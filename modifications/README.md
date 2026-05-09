# modifications

I'm interested in how open source models perform on ProgramBench + how much performance we can gain through auto prompt tuning w/ DSPy`.

Thinking of using OpenRouter to handle the inference ( connect to mini-swe-agent ).

## Setup

My fork expects mini-swe-agent to be installed.

```bash
# from the parent directory of this repo
git clone https://github.com/swe-agent/mini-swe-agent
uv pip install -e ../mini-swe-agent
```

Tests are created and stored on huggingface, repo offers helper command to bring them in `uv run programbench blob sync`
- from docs/README.md
- update `PROGRAMBENCH_BLOB_DIR` to set hf test blob path (defaults to HF cache loc, set to ./blobs here)

## Other Info

Leaderboard of best runs: https://programbench.com/
- anthropic's heavily in the lead, their agents take more turns too (tuned for swe bench heavily? :) )