# Job Finder

Asks you what job you want, then searches up to 9 job sites at once. It
removes duplicates, throws out jobs you said you don't want, ranks the rest,
and saves them as a web page you can click through.

## The sites

| Type this | Site | Notes |
|---|---|---|
| `indeed` | Indeed | |
| `linkedin` | LinkedIn | Blocks you for a while if you search too often |
| `google` | Google Jobs | Collects postings from many smaller sites |
| `jobbank` | Job Bank / Guichet-Emplois | Government of Canada. Lots of restaurant, retail and student jobs |
| `adzuna` | Adzuna | Official API, needs a free key |
| `jooble` | Jooble | Official API, needs a free key |
| `remotive` | Remotive | Remote jobs only, used only if you answer "y" to remote |
| `glassdoor` | Glassdoor | Often blocks these searches |
| `ziprecruiter` | ZipRecruiter | Mostly USA |

Type `all` to search every site. The default is Indeed, LinkedIn, Google and
Job Bank.

**Free keys (Adzuna, Jooble):** the first time you pick one of these, the
program shows the sign-up link and asks you to paste the key. It's saved in
`api_keys.json`, which is listed in `.gitignore` so it never gets uploaded to
GitHub. Press Enter instead to skip that site.

- Adzuna: sign up at https://developer.adzuna.com/signup, then copy the
  *Application ID* and *Application Key*.
- Jooble: fill the form at https://jooble.org/api/about, the key comes by email.

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
| `search.py` | Sends each job title to every picked site and collects the results |
| `more_sites.py` | Job Bank, Adzuna, Jooble and Remotive, one function each |
| `ranking.py` | Dedupes, filters and scores (no internet code, easy to test) |
| `report.py` | Terminal output, CSV and HTML files, NEW markers |
| `tests/` | `python -m pytest` checks everything with fake jobs and fake web pages |

Indeed, LinkedIn, Google, Glassdoor and ZipRecruiter go through the
[JobSpy](https://github.com/speedyapply/JobSpy) library.

**Adding your own site:** write a function in `more_sites.py` that takes
`(title, prefs)` and returns a list of jobs built with `make_job(...)`, add it
to `EXTRA_SITES` at the bottom, and add a line to `SITES` in `questions.py`.

## Limits to know

- JobSpy reads the sites the way a browser would; it is not an official API.
  If you search a lot in a short time, a site (LinkedIn first) may block you
  for a while and you'll see `! linkedin failed`. The other sites keep working.
- Glassdoor and ZipRecruiter often block these requests. Indeed and Google
  are the most reliable.
- Job Bank has no API, so the program reads its search page. If the
  government redesigns that page, you'll see "layout may have changed" and
  Job Bank returns 0 jobs until `parse_jobbank_html()` is updated.
- Job Bank often lists Quebec jobs under their French title only. Add the
  French name as a second job title (for example `cook, cuisinier`) or you'll
  miss those, or they'll rank low.
- After each search you'll see a line like
  `found 41 jobs (indeed 15, linkedin 0, google 10, jobbank 16)`. A site stuck
  at 0 every time is broken or blocking you; the others are unaffected.
- Google Jobs returns at most around 10 to 20 results per search and ignores
  the distance and job-type filters.
- Pay is converted to $/hour assuming 40 h/week, so a yearly salary for a
  part-time job will look lower than it is.
- Keep it for your own job hunt. Running it on a schedule hundreds of times a
  day is what gets you blocked and is against the sites' terms.
