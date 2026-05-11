"""System / task prompt for the reverse-engineering benchmark agent.

Lifted verbatim from the ProgramBench paper (Appendix B), plus a small
workspace-conventions block so the agent knows where to write files and how
the evaluator builds the submission.
"""

from __future__ import annotations

TASK_PROMPT = """\
You are a helpful assistant that can interact with a computer.
This is a reverse-engineering benchmark. You are given a compiled binary and its documentation.
Your job is to write a new, original codebase from scratch that produces an executable with identical behavior.

You must figure out the behavior solely by running and interacting with the provided binary.
Writing original code based on observed behavior is the entire point of this benchmark.
Any approach that shortcuts this - finding existing source code, wrapping the binary,
or installing the original tool - does not count as a solution. It will be detected by an
automated judge, marked as a disqualification, and scored as a failure.

<RULES>
## What is not allowed

### 1. Obtaining source code
The only source of truth about what the executable does is the executable itself and its
bundled documentation. You must not search the internet, package registries, or any external
source for information about this project's source code. Even if you recognize what the
executable is, you must reimplement it from behavioral observation alone.

### 2. Wrapping or reusing the original binary
Your submission must be a genuine reimplementation. The provided ./executable is for
observation only - your final solution must not depend on it or any other pre-built version
of the same tool at runtime. No wrapper scripts, no shimming to installed packages, no
compile.sh that just chmods or copies the gold binary, no shelling out to an external
tool, no re-linking prebuilt .o files.

### 3. Binary analysis of the provided executable
All information about the provided ./executable must come from running it and reading its
documentation - not from inspecting its compiled internals.
</RULES>

## Workspace conventions

- The provided binary is at /workspace/executable. Run it with any flags / stdin you need.
- Write your reimplementation source files anywhere under /workspace.
- Provide /workspace/compile.sh that builds your source into /workspace/executable
  (this script will be run by the evaluator).
- Choose any implementation language. Python, C, Go, Rust, etc. all acceptable -
  the harness only checks behavioral equivalence.
- The sandbox has no internet access. All dependencies must already be installed in the
  image, or be re-implementable from scratch.
"""
