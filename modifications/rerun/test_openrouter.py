"""Smoke-test OpenRouter access. Hits deepseek/deepseek-v4-flash with a tiny prompt
and prints the response, so we can verify the API key and model id work before
spending agent turns on a real task.

Usage:
    export OPENROUTER_API_KEY=sk-or-...
    python modifications/rerun/test_openrouter.py
"""

from __future__ import annotations

import json
import os
import sys
import urllib.request

MODEL = "deepseek/deepseek-v4-flash"
URL = "https://openrouter.ai/api/v1/chat/completions"


def main() -> None:
    key = os.environ.get("OPENROUTER_API_KEY")
    if not key:
        sys.exit("OPENROUTER_API_KEY not set. Get one at https://openrouter.ai/keys.")

    body = json.dumps(
        {
            "model": MODEL,
            "messages": [
                {"role": "user", "content": "Reply with exactly: pong"},
            ],
            "max_tokens": 20,
        }
    ).encode()

    req = urllib.request.Request(
        URL,
        data=body,
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/local/programbench-rerun",
            "X-Title": "programbench-rerun smoke test",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read())

    print(f"Model: {data.get('model')}")
    print(f"Reply: {data['choices'][0]['message']['content']!r}")
    usage = data.get("usage", {})
    if usage:
        print(
            f"Tokens: prompt={usage.get('prompt_tokens')} "
            f"completion={usage.get('completion_tokens')} "
            f"total={usage.get('total_tokens')}"
        )


if __name__ == "__main__":
    main()
