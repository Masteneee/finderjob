"""
search.py: sends your answers to the job sites and collects the results.

The real work is done by the JobSpy library (python-jobspy), which knows
how to talk to Indeed, LinkedIn, Google Jobs, Glassdoor and ZipRecruiter.
We call it once per job title and glue all the results together.
"""

import pandas as pd
from jobspy import scrape_jobs

from questions import SITES, JOB_TYPES

KM_PER_MILE = 1.609


def search_one_title(title, prefs):
    """Search every chosen site for one job title. Returns a DataFrame."""
    sites = [SITES[s] for s in prefs["sites"]]
    when = "since yesterday" if prefs["max_days_old"] <= 1 else "in the last week"

    jobs = scrape_jobs(
        site_name=sites,
        search_term=title,
        # Google Jobs ignores most filters, it just reads a sentence like a human would
        google_search_term=f"{title} jobs near {prefs['location']} {when}",
        location=prefs["location"],
        distance=max(1, round(prefs["distance_km"] / KM_PER_MILE)),  # JobSpy wants miles
        job_type=JOB_TYPES[prefs["job_type"]],
        is_remote=prefs["remote_only"],
        results_wanted=int(prefs["results_per_site"]),
        hours_old=int(prefs["max_days_old"] * 24),
        country_indeed=prefs["country"],
        verbose=0,  # keep the terminal quiet, we print our own messages
    )

    # JobSpy stores per-site problems here instead of crashing
    for site, error in jobs.attrs.get("errors", {}).items():
        print(f"    ! {site} failed: {error}")

    jobs["searched_for"] = title
    return jobs


def search_all(prefs):
    """Search for every job title and return one big DataFrame."""
    all_results = []
    for title in prefs["job_titles"]:
        print(f"  Searching '{title}' on {', '.join(prefs['sites'])}...")
        try:
            found = search_one_title(title, prefs)
        except Exception as error:  # a bad answer or no internet shouldn't kill the program
            print(f"    ! search for '{title}' failed: {error}")
            continue
        print(f"    found {len(found)} jobs")
        all_results.append(found)

    if not all_results:
        return pd.DataFrame()
    return pd.concat(all_results, ignore_index=True)
