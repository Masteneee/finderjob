# Job Finder

Asks you what job you want, then searches **Indeed, LinkedIn and Google Jobs**
(plus Glassdoor and ZipRecruiter if you want) all at once. It removes
duplicates, throws out jobs you said you don't want, ranks the rest, and saves
them as a web page you can click through.

## Setup (once)

You need Python 3.10 or newer. In a terminal, inside this folder:

```bash
python -m venv .venv
```

On Mac/Linux:

```bash
source .venv/bin/activate
```

On Windows:

```bash
.venv\Scripts\activate
```

Then:

```bash
pip install -r requirements.txt
```

## Use it

```bash
python job_finder.py
```

It asks about 12 questions (job titles, city, distance, part-time or
full-time, minimum pay, words you want, words you don't want, which sites...).
Press Enter to keep the default shown in `[brackets]`. Your answers are saved,
so next time you just answer "y" to reuse them.

Results:

- The top 10 are printed in the terminal.
- Everything goes in `results/jobs_<date>.html` (open it in your browser,
  titles are links) and `results/jobs_<date>.csv` (Excel / Google Sheets).
- Jobs you haven't seen in an earlier run are marked **NEW**, so running it
  every couple of days shows you only what changed.

## How the ranking works

A job is **removed** if its title contains one of your "don't want" words, it
is older than your day limit, or it shows a pay below your minimum. Jobs that
hide their pay are kept, since you can't know.

The rest get points: +3 if the title really matches what you searched,
+3 for each "want" word in the title (+1 if only in the description),
+2 if posted today or yesterday, +1 if it shows the pay. The "Why this score"
column tells you where the points came from. Want different rules? It's all
in `score_job()` in `ranking.py`.

## Files

| File | What it does |
|---|---|
| `job_finder.py` | Runs the 4 steps in order |
| `questions.py` | Asks the questions, saves answers to `preferences.json` |
| `search.py` | Calls the job sites through the [JobSpy](https://github.com/speedyapply/JobSpy) library |
| `ranking.py` | Dedupes, filters and scores (no internet code, easy to test) |
| `report.py` | Terminal output, CSV and HTML files, NEW markers |
| `tests/` | `python -m pytest` checks the ranking with fake jobs |

## Limits to know

- JobSpy reads the sites the way a browser would; it is not an official API.
  If you search a lot in a short time, a site (LinkedIn first) may block you
  for a while and you'll see `! linkedin failed`. The other sites keep working.
- Glassdoor and ZipRecruiter often block these requests. Indeed and Google
  are the most reliable.
- Google Jobs returns at most around 10 to 20 results per search and ignores
  the distance and job-type filters.
- Pay is converted to $/hour assuming 40 h/week, so a yearly salary for a
  part-time job will look lower than it is.
- Keep it for your own job hunt. Running it on a schedule hundreds of times a
  day is what gets you blocked and is against the sites' terms.
