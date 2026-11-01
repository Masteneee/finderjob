"""
search.py: sends your answers to the job sites and collects the results.

Two kinds of sites:
  - Indeed, LinkedIn, Google, Glassdoor, ZipRecruiter go through the
    JobSpy library (python-jobspy), all in one call.
  - Job Bank, Adzuna, Jooble, Remotive are in more_sites.py, one function each.

Everything comes back as one list of job dicts.
"""

import logging

from jobspy import scrape_jobs

import more_sites
from questions import JOB_TYPES

KM_PER_MILE = 1.609

# JobSpy prints its own error lines. We already print a shorter one per site,
# so tell JobSpy's logger to stay silent (verbose=None below keeps this setting).
logging.getLogger("jobspy").setLevel(logging.CRITICAL)


def short(error):
    """Long technical errors -> one readable line."""
    text = " ".join(str(error).split())
    return text if len(text) <= 160 else text[:157] + "..."


# The name you type -> the name JobSpy expects
JOBSPY_SITES = {
    "indeed": "indeed",
    "linkedin": "linkedin",
    "google": "google",
    "glassdoor": "glassdoor",
    "ziprecruiter": "zip_recruiter",
}


def search_jobspy(title, sites, prefs):
    """Search the JobSpy sites for one job title. Returns a list of job dicts."""
    when = "since yesterday" if prefs["max_days_old"] <= 1 else "in the last week"

    jobs = scrape_jobs(
        site_name=[JOBSPY_SITES[s] for s in sites],
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
        verbose=None,  # don't touch the logging level we set above
    )

    # JobSpy stores per-site problems here instead of crashing
    for site, error in jobs.attrs.get("errors", {}).items():
        print(f"    ! {site} failed: {short(error)}")

    return jobs.to_dict("records")   # DataFrame -> plain list of dicts


def count_by_site(jobs):
    counts = {}
    for job in jobs:
        counts[job["site"]] = counts.get(job["site"], 0) + 1
    return counts


def search_all(prefs):
    """Search every chosen site for every job title. Returns one list of jobs."""
    jobspy_sites = [s for s in prefs["sites"] if s in JOBSPY_SITES]
    other_sites = [s for s in prefs["sites"] if s in more_sites.EXTRA_SITES]
    all_jobs = []

    for title in prefs["job_titles"]:
        print(f"  Searching '{title}'...")
        found = []

        if jobspy_sites:
            try:
                found += search_jobspy(title, jobspy_sites, prefs)
            except Exception as error:   # a bad answer or no internet shouldn't kill the program
                print(f"    ! {', '.join(jobspy_sites)} failed: {short(error)}")

        for site in other_sites:
            try:
                found += more_sites.EXTRA_SITES[site](title, prefs)
            except Exception as error:
                print(f"    ! {site} failed: {short(error)}")

        for job in found:
            job["searched_for"] = title
        counts = count_by_site(found)
        # Show every picked site, even the ones that found 0, so you can spot a broken one
        summary = ", ".join(f"{s} {counts.get(JOBSPY_SITES.get(s, s), 0)}" for s in prefs["sites"])
        print(f"    found {len(found)} jobs ({summary})")
        all_jobs += found

    return all_jobs
