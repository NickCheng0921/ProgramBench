"""Run mini-swe-agent against a single ProgramBench task via OpenRouter.

Sandbox: mini-swe-agent's `DockerEnvironment` starts a container per session;
we configure it with `--network=none` so the workload it drives has no internet
access (matching the paper). Mini's own loop runs on the host and can reach
OpenRouter freely.

Flow:
  1. Pull the per-task Docker image (programbench/<owner>_1776_<repo>.<hash>:task).
  2. Write a temp config YAML overriding mini's system_template + environment.
  3. Run `mini -c <default> -c <ours> -m <model> -t <task> -y --environment-class docker`.
     Mini starts a container labeled `pb-run=<run-id>` (we pass that via run_args)
     so we can find it after.
  4. Find the labeled container, stream /workspace out as submission.tar.gz, remove it.
  5. Run `programbench eval` to score it (unless --no-eval).

Setup (one-time):
    pip install mini-swe-agent       # provides the `mini` CLI
    export OPENROUTER_API_KEY=...    # https://openrouter.ai/keys

Example (single line; bash line-continuation is one backslash, not two):
    python modifications/rerun/run_agent.py abishekvashok__cmatrix.5c082c6 \
        --model openrouter/deepseek/deepseek-v4-flash \
        --run-name deepseek_v4_flash --max-tokens 8192

    python modifications/rerun/run_agent.py arq5x__bedtools2.dd57059 \
        --model openrouter/deepseek/deepseek-v4-flash \
        --run-name deepseek_v4_flash --max-tokens 8192
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import subprocess
import sys
import tempfile
import uuid
from pathlib import Path

from prompt import TASK_PROMPT

REPO_ROOT = Path(__file__).resolve().parents[2]


def image_for(instance_id: str) -> str:
    return f"programbench/{instance_id.replace('__', '_1776_').lower()}:task"


def mini_default_config() -> Path:
    """Path to mini-swe-agent's bundled mini.yaml (so our overrides merge with it)."""
    import minisweagent  # type: ignore[import-not-found]
    return Path(minisweagent.__file__).parent / "config" / "mini.yaml"


def write_overrides(
    image: str, label: str, cost_limit: float, step_limit: int,
    host_workspace: Path, max_tokens: int,
) -> Path:
    """Write a YAML that overrides mini.yaml fields we care about."""
    cfg = {
        "agent": {
            "system_template": TASK_PROMPT,
            "cost_limit": cost_limit,
            "step_limit": step_limit,
            "mode": "yolo",  # don't prompt for confirmation per command
        },
        "model": {
            "model_kwargs": {
                "drop_params": True,
                "max_tokens": max_tokens,
                # Abort a single API call if the provider stalls.
                "request_timeout": 120,
                "timeout": 120,
                # OpenRouter-specific: auto-trim middle of prompt if it would
                # exceed the model's context window.
                "extra_body": {"transforms": ["middle-out"]},
            },
        },
        "environment": {
            "image": image,
            "cwd": "/workspace",
            "run_args": [
                "--network=none",
                "--label", f"pb-run={label}",
                "-v", f"{host_workspace}:/workspace",
            ],
            # Don't pass --rm; we need the container to survive past mini's exit
            # so we can extract /workspace. We rm it manually below.
            "container_timeout": "2h",
        },
    }
    f = tempfile.NamedTemporaryFile(
        mode="w", suffix=".yaml", delete=False, encoding="utf-8"
    )
    # Write minimal YAML by hand (avoids yaml dep; values are simple).
    f.write(_dump_yaml(cfg))
    f.close()
    return Path(f.name)


def _dump_yaml(obj, indent: int = 0) -> str:
    """Tiny YAML serializer for our limited use (dict/list/str/num/bool)."""
    pad = "  " * indent
    if isinstance(obj, dict):
        out = []
        for k, v in obj.items():
            if isinstance(v, (dict, list)):
                out.append(f"{pad}{k}:\n{_dump_yaml(v, indent + 1)}")
            elif isinstance(v, str) and ("\n" in v or len(v) > 80):
                out.append(f"{pad}{k}: |\n" + "\n".join(f"{pad}  {ln}" for ln in v.split("\n")))
            else:
                out.append(f"{pad}{k}: {json.dumps(v)}")
        return "\n".join(out)
    if isinstance(obj, list):
        return "\n".join(f"{pad}- {json.dumps(item)}" for item in obj)
    return f"{pad}{json.dumps(obj)}"


def find_container(label: str) -> str | None:
    r = subprocess.run(
        ["docker", "ps", "-a", "-q", "-f", f"label=pb-run={label}"],
        capture_output=True, text=True, check=True,
    )
    cids = [c for c in r.stdout.strip().split("\n") if c]
    return cids[0] if cids else None


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("instance_id", help="e.g. abishekvashok__cmatrix.5c082c6")
    p.add_argument(
        "--model",
        default="openrouter/deepseek/deepseek-v4-flash",
        help="LiteLLM model string. OpenRouter format: openrouter/<provider>/<model>.",
    )
    p.add_argument("--run-name", default="agent_run")
    p.add_argument("--cost-limit", type=float, default=3.0,
                   help="Mini cost cap in USD (0 disables).")
    p.add_argument("--step-limit", type=int, default=200,
                   help="Mini step cap (0 disables).")
    p.add_argument("--max-tokens", type=int, default=8192,
                   help="Per-request max output tokens passed to LiteLLM/OpenRouter.")
    p.add_argument("--wall-timeout", type=int, default=1800,
                   help="Wall-clock cap (seconds) on the whole mini invocation. 0 disables.")
    p.add_argument("--no-eval", action="store_true")
    p.add_argument("--keep-sandbox", action="store_true",
                   help="Don't remove the sandbox container at the end.")
    args = p.parse_args()

    if not os.environ.get("OPENROUTER_API_KEY"):
        sys.exit("OPENROUTER_API_KEY not set. Get one at https://openrouter.ai/keys.")

    # Skip mini's first-run wizard by pre-creating an (empty) global config.
    mini_global_cfg = Path.home() / ".config" / "mini-swe-agent" / ".env"
    if not mini_global_cfg.exists():
        mini_global_cfg.parent.mkdir(parents=True, exist_ok=True)
        mini_global_cfg.write_text("# created by run_agent.py to skip wizard\n")

    image = image_for(args.instance_id)
    run_root = REPO_ROOT / "tmp" / args.run_name
    run_id = f"{dt.datetime.now().strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:6]}"
    run_dir = run_root / "runs" / args.instance_id / run_id
    submission_dir = run_dir / "submission"
    host_workspace = run_dir / "workspace"
    submission_dir.mkdir(parents=True, exist_ok=True)
    host_workspace.mkdir(parents=True, exist_ok=True)
    label = f"{args.instance_id.replace('.', '-')}-{run_id[-6:]}"
    print(f"Run dir: {run_dir}")

    # 1. Pull (no-op if cached).
    print(f"Pulling {image} ...")
    subprocess.run(["docker", "pull", image], check=True)

    # 1b. Seed host_workspace from the image's /workspace so the agent has
    #     the gold ./executable + docs to inspect (bind mount otherwise hides them).
    print(f"Seeding workspace from image -> {host_workspace} ...")
    cid_seed = subprocess.check_output(
        ["docker", "create", image], text=True
    ).strip()
    try:
        subprocess.run(
            ["docker", "cp", f"{cid_seed}:/workspace/.", str(host_workspace)],
            check=True,
        )
    finally:
        subprocess.run(["docker", "rm", cid_seed], check=True, stdout=subprocess.DEVNULL)

    # 2. Write overrides config (binds host_workspace -> /workspace).
    overrides_yaml = write_overrides(
        image, label, args.cost_limit, args.step_limit, host_workspace,
        args.max_tokens,
    )

    # 3. Run mini-swe-agent.
    task_msg = (
        "The binary you must reimplement is at /workspace/executable. "
        "Begin by exploring its CLI/help, then build up your reimplementation under "
        "/workspace. Provide /workspace/compile.sh that builds your source into "
        "/workspace/executable. Submit when done by issuing the COMPLETE_TASK command."
    )
    task_msg = "Write some tests for the existing executable, then write your own code and check if it passes. Complete once done by issung COMPLETE_TASK. If a binary errors with Error opening terminal or similar, it's a curses app — focus on --help, version, and error-path testing rather than trying to run it interactively. Use script -qc only if a specific test requires the binary to start successfully under a pty."
    cmd = [
        "mini",
        "-c", str(mini_default_config()),
        "-c", str(overrides_yaml),
        "-m", args.model,
        "-t", task_msg,
        "-y",  # yolo mode
        "--environment-class", "docker",
        "--exit-immediately",
        "-o", str(run_dir / "trajectory.json"),
    ]
    print(f"Running mini-swe-agent ({args.model}) ...")
    env = os.environ.copy()
    # OpenRouter routes models that aren't in litellm's price map, so mini's
    # cost tracker raises. Suppress that — we'll cap by step_limit instead.
    env.setdefault("MSWEA_COST_TRACKING", "ignore_errors")
    timeout = args.wall_timeout or None
    try:
        rc = subprocess.run(cmd, env=env, timeout=timeout).returncode
    except subprocess.TimeoutExpired:
        print(f"mini exceeded wall timeout ({timeout}s); killing and packaging /workspace anyway.")
        rc = -1
    if rc != 0:
        print(f"mini exited non-zero ({rc}); packaging /workspace anyway.")

    # 4. Pack host_workspace into submission.tar.gz (the bind mount means it's
    #    already up-to-date with whatever the agent left behind).
    sub_path = submission_dir / "submission.tar.gz"
    print(f"Packaging submission -> {sub_path}")
    subprocess.run(
        ["tar", "--exclude=./eval", "-C", str(host_workspace),
         "-czf", str(sub_path), "."],
        check=True,
    )

    # Find the labeled container so we can clean up (or keep it).
    cid = find_container(label)
    if cid:
        if args.keep_sandbox:
            print(f"Sandbox kept: {cid}  (remove with: docker rm -f {cid})")
        else:
            subprocess.run(["docker", "rm", "-f", cid],
                           check=False, capture_output=True)
    else:
        print(f"(No labeled container found for pb-run={label}; nothing to clean up.)")

    overrides_yaml.unlink(missing_ok=True)

    # 5. Optionally eval.
    if args.no_eval:
        print(f"\nSkipping eval. Submission at: {sub_path}")
        return

    # programbench eval expects <run_dir>/<instance_id>/submission.tar.gz layout.
    # Symlink (or copy) submission into that shape so we can point eval at it.
    eval_in = run_dir / "eval-in"
    (eval_in / args.instance_id).mkdir(parents=True, exist_ok=True)
    (eval_in / args.instance_id / "submission.tar.gz").write_bytes(sub_path.read_bytes())

    print("\nRunning programbench eval ...")
    eval_out = run_dir / "eval-out"
    subprocess.run(
        ["programbench", "eval", str(eval_in),
         "--filter", f"^{args.instance_id}$",
         "-w", "1", "-b", "1",
         "-o", str(eval_out),
         "--force"],
        check=False,
    )
    print(f"\nDone. Results at: {eval_out / args.instance_id / 'eval.json'}")


if __name__ == "__main__":
    main()
