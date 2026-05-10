Prompts I used to build the scraper, Claude Code v1.6608.2 Opus 4.7

---

This page offers task breakdowns of program bench
https://programbench.com/

If you scrape the html, you'll see that it redirects to pages like this
https://programbench.com/task/wintermute-cell__ngrrram.8ea13c3/

And it shows score, calls, and cost per model
Can you build a scraper under modifications/metrics_scraper/
and put this all into a table

A row should be:
repo owner, repo name, # generated behavioral tests, best score, model X, model X score, model X cost, model X cost, model Y...

---

can you round off those floats to 2

---

round to 4
