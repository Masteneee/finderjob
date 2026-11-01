"""
report.py: shows the results in the terminal and saves them to files.

  results/jobs_<date>.csv   opens in Excel / Google Sheets
  results/jobs_<date>.html  open in your browser, every title is a clickable link

It also remembers which jobs you've already been shown (seen_jobs.json),
so on the next run new postings are marked NEW.
"""

import csv
import html
import json
from datetime import datetime
from pathlib import Path

from ranking import clean

HERE = Path(__file__).parent
RESULTS_DIR = HERE / "results"
SEEN_FILE = HERE / "seen_jobs.json"

COLUMNS = ["score", "new", "title", "company", "location", "hourly",
           "days_old", "site", "job_url", "why"]


def mark_new(jobs):
    seen = set(json.loads(SEEN_FILE.read_text())) if SEEN_FILE.exists() else set()
    for job in jobs:
        job["new"] = "NEW" if job.get("job_url") not in seen else ""
        seen.add(job.get("job_url"))
    SEEN_FILE.write_text(json.dumps(sorted(u for u in seen if u)))


def print_top(jobs, how_many=10):
    if not jobs:
        print("\nNo jobs matched. Try fewer bad words, a bigger distance or more days.")
        return
    print(f"\nTop {min(how_many, len(jobs))} of {len(jobs)} jobs:\n")
    for number, job in enumerate(jobs[:how_many], start=1):
        pay = f"${job['hourly']:.2f}/h" if job["hourly"] else "pay not shown"
        age = f"{job['days_old']}d ago" if job["days_old"] is not None else "date unknown"
        company = clean(job.get("company")) or "?"
        print(f"{number:2}. {job['new']:3} {job['title']}  @ {company}")
        print(f"      {clean(job.get('location')) or ''} | {pay} | {age} | {job.get('site')}"
              f" | score {job['score']}")
        print(f"      {job.get('job_url')}")


def save_csv(jobs, path):
    with open(path, "w", newline="", encoding="utf-8-sig") as f:   # -sig = Excel reads accents right
        writer = csv.DictWriter(f, fieldnames=COLUMNS, extrasaction="ignore")
        writer.writeheader()
        for job in jobs:
            writer.writerow({col: clean(job.get(col)) for col in COLUMNS})


def save_html(jobs, path, prefs):
    rows = []
    for job in jobs:
        e = lambda col: html.escape(str(clean(job.get(col)) or ""))
        pay = f"${job['hourly']:.2f}/h" if job["hourly"] else "?"
        age = f"{job['days_old']}d" if job["days_old"] is not None else "?"
        rows.append(
            f"<tr><td>{job['score']}</td><td class=new>{e('new')}</td>"
            f"<td><a href='{e('job_url')}' target=_blank>{e('title')}</a></td>"
            f"<td>{e('company')}</td><td>{e('location')}</td><td>{pay}</td>"
            f"<td>{age}</td><td>{e('site')}</td><td class=why>{e('why')}</td></tr>")

    searched = html.escape(", ".join(prefs["job_titles"]) + " near " + prefs["location"])
    page = f"""<!doctype html><meta charset=utf-8>
<meta name=viewport content="width=device-width, initial-scale=1">
<title>Job Finder results</title>
<style>
  body {{ font-family: system-ui, sans-serif; margin: 16px; background: #fafafa; color: #222; }}
  table {{ border-collapse: collapse; width: 100%; background: white; }}
  th, td {{ padding: 6px 8px; border-bottom: 1px solid #ddd; text-align: left; vertical-align: top; }}
  th {{ background: #333; color: white; position: sticky; top: 0; }}
  .new {{ color: #0a7d2c; font-weight: bold; }}
  .why {{ color: #666; font-size: 0.85em; }}
  .wrap {{ overflow-x: auto; }}
</style>
<h1>{len(jobs)} jobs: {searched}</h1>
<p>Made {datetime.now():%Y-%m-%d %H:%M}. Best matches at the top.</p>
<div class=wrap><table>
<tr><th>Score</th><th></th><th>Job</th><th>Company</th><th>Where</th>
<th>Pay</th><th>Age</th><th>Site</th><th>Why this score</th></tr>
{''.join(rows)}
</table></div>"""
    path.write_text(page, encoding="utf-8")


def save_all(jobs, prefs):
    RESULTS_DIR.mkdir(exist_ok=True)
    stamp = datetime.now().strftime("%Y-%m-%d_%H%M")
    csv_path = RESULTS_DIR / f"jobs_{stamp}.csv"
    html_path = RESULTS_DIR / f"jobs_{stamp}.html"
    save_csv(jobs, csv_path)
    save_html(jobs, html_path, prefs)
    return csv_path, html_path
