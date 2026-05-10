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

Run `/modifications/rerun/extract_test.py` to conver the hf compressed tarballs to testing directories
  - you'll have to pull them first from `https://huggingface.co/datasets/programbench/ProgramBench-Tests`

## Other Info

Leaderboard of best runs: https://programbench.com/
- anthropic's heavily in the lead, their agents take more turns too (tuned for swe bench heavily? :) )

metrics_scraper/ is set up to compare model performance on the tasks + look for differences/model biases
- created w/ Opus 4.7, very similar to fig 25 in paper

GPT 5.4 and Opus 4.7 have a very high pearson correlation on task-score compared to every other combination of models

Results come from a single run across everything, not pass@k so we should expect strong per task variance if we recreate results
  - pg 10, mentions 1800 runs, which is 1 run per task per model. Could have been costly to do pass@k but this is also Meta TBD...

Some tests are OS specific, like one of cmatrix's tests goes over the windows max path limit and uses illegal chars in the filename
  - using WSL for now