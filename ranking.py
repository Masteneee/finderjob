"""
ranking.py: removes the junk and sorts the rest, best match first.

Every job is a dict like {"title": ..., "company": ..., "description": ...}.
This file has no internet code at all, which makes it easy to test
(see tests/test_ranking.py).
"""

import re
from datetime import date

import pandas as pd

# Rough number of work hours in each pay period, to turn any salary into $/hour
HOURS_IN = {"hourly": 1, "daily": 8, "weekly": 40, "monthly": 173, "yearly": 2080}


def clean(value):
    """Pandas marks empty cells with NaN ("not a number") or NaT ("not a time").
    Turn both into None so the rest of the code only has to check for None."""
    if isinstance(value, (list, dict)):
        return value
    return None if pd.isna(value) else value


def has_word(text, word):
    """True if `word` appears in `text` as a whole word, ignoring upper/lower case.
    So 'cook' matches 'Line Cook' but not 'Cookie Factory'."""
    if not text:
        return False
    return re.search(rf"\b{re.escape(word)}\b", text, re.IGNORECASE) is not None


def hourly_pay(job):
    """Return the lowest advertised pay as $/hour, or None if the posting hides it."""
    amount = clean(job.get("min_amount")) or clean(job.get("max_amount"))
    interval = clean(job.get("interval"))
    if not amount or interval not in HOURS_IN:
        return None
    return round(amount / HOURS_IN[interval], 2)


def days_old(job, today):
    posted = clean(job.get("date_posted"))
    if posted is None:
        return None
    if isinstance(posted, str):
        try:
            posted = date.fromisoformat(posted[:10])
        except ValueError:
            return None
    if hasattr(posted, "date"):      # a datetime, keep only the day part
        posted = posted.date()
    return (today - posted).days


def remove_duplicates(jobs):
    """The same job is often on Indeed AND Job Bank AND Google. Keep the first one,
    but if it hides the pay and a copy shows it, take the pay from the copy."""
    first_copy = {}   # (title, company) -> the job we kept
    unique = []
    for job in jobs:
        key = (str(job.get("title", "")).lower().strip(),
               str(clean(job.get("company")) or "").lower().strip())
        if key not in first_copy:
            first_copy[key] = job
            unique.append(job)
        elif hourly_pay(first_copy[key]) is None and hourly_pay(job) is not None:
            for field in ("min_amount", "max_amount", "interval"):
                first_copy[key][field] = job.get(field)
    return unique


def reject_reason(job, prefs, today):
    """Return why a job should be thrown away, or None if it's a keeper."""
    for word in prefs["bad_words"]:
        if has_word(job.get("title"), word):
            return f"title has '{word}'"

    age = days_old(job, today)
    if age is not None and age > prefs["max_days_old"]:
        return f"posted {age} days ago"

    pay = hourly_pay(job)
    if pay is not None and prefs["min_hourly_pay"] and pay < prefs["min_hourly_pay"]:
        return f"pays ${pay}/h"

    return None


def score_job(job, prefs, today):
    """Give the job points. Returns (points, list of reasons) so you can see WHY."""
    points = 0
    why = []
    title = job.get("title") or ""
    description = clean(job.get("description")) or ""

    # Does the title actually match what you searched for? Google Jobs especially
    # returns loosely related stuff, so a real match gets a big bonus.
    for wanted in prefs["job_titles"]:
        if all(has_word(title, word) for word in wanted.split()):
            points += 3
            why.append(f"title matches '{wanted}'")
            break

    for word in prefs["good_words"]:
        if has_word(title, word):
            points += 3
            why.append(f"'{word}' in title")
        elif has_word(description, word):
            points += 1
            why.append(f"'{word}' in description")

    age = days_old(job, today)
    if age is not None and age <= 1:
        points += 2
        why.append("posted today/yesterday")
    elif age is not None and age <= 3:
        points += 1
        why.append("posted this week")

    if hourly_pay(job) is not None:
        points += 1
        why.append("shows the pay")

    return points, why


def rank(jobs, prefs, today=None):
    """Main function: dedupe, filter, score, sort. Returns (kept, rejected_count)."""
    today = today or date.today()
    kept = []
    rejected = 0
    for job in remove_duplicates(jobs):
        if reject_reason(job, prefs, today):
            rejected += 1
            continue
        job["score"], reasons = score_job(job, prefs, today)
        job["why"] = ", ".join(reasons)
        job["hourly"] = hourly_pay(job)
        job["days_old"] = days_old(job, today)
        kept.append(job)

    # Highest score first. If two jobs tie, the newer one goes first
    # (unknown age counts as very old: 999 days).
    kept.sort(key=lambda j: (-j["score"], j["days_old"] if j["days_old"] is not None else 999))
    return kept, rejected
