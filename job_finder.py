"""
Job Finder: asks what job you want, searches Indeed, LinkedIn, Google Jobs,
Job Bank, Adzuna, Jooble, Remotive, Glassdoor and ZipRecruiter (you pick),
then ranks everything it found.

Run it with:   python job_finder.py

The program is split in 4 steps, one file each:
  1. questions.py  ask you what you want
  2. search.py     search the job sites
  3. ranking.py    remove junk and sort best first
  4. report.py     print the top jobs and save them to CSV + HTML
"""

import questions
import ranking
import report
import search


def main():
    print("=" * 50)
    print("  JOB FINDER")
    print("=" * 50)

    prefs = questions.interview()                       # step 1

    print("\nSearching (this can take a minute)...")
    found = search.search_all(prefs)                    # step 2
    if not found:
        print("\nNothing came back. Check your internet connection, or try again"
              " in a few minutes (sites sometimes block too many searches in a row).")
        return

    jobs, rejected = ranking.rank(found, prefs)         # step 3
    print(f"\n{len(found)} results, {len(found) - len(jobs) - rejected} duplicates,"
          f" {rejected} filtered out by your answers.")

    report.mark_new(jobs)                               # step 4
    report.print_top(jobs)
    if jobs:
        csv_path, html_path = report.save_all(jobs, prefs)
        print(f"\nAll {len(jobs)} jobs saved to:\n  {html_path}\n  {csv_path}")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:      # Ctrl+C quits quietly instead of a big error
        print("\nBye!")
