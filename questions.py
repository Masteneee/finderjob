"""
questions.py: asks you what kind of job you want.

Your answers are saved in preferences.json so next time you can just
press Enter to reuse them.
"""

import json
from pathlib import Path

PREFS_FILE = Path(__file__).parent / "preferences.json"

import more_sites

# Every site you can pick. The key is what you type, the value is shown as a hint.
SITES = {
    "indeed": "Indeed",
    "linkedin": "LinkedIn (blocks you if you search too often)",
    "google": "Google Jobs (collects jobs from many smaller sites)",
    "jobbank": "Job Bank / Guichet-Emplois, Government of Canada",
    "adzuna": "Adzuna (needs a free key)",
    "jooble": "Jooble (needs a free key)",
    "remotive": "Remotive (remote jobs only)",
    "glassdoor": "Glassdoor (often blocks searches)",
    "ziprecruiter": "ZipRecruiter (mostly USA)",
}

JOB_TYPES = {
    "any": None,
    "full-time": "fulltime",
    "part-time": "parttime",
    "contract": "contract",
    "temporary": "temporary",
    "internship": "internship",
}

DEFAULTS = {
    "job_titles": ["cook"],
    "location": "Montreal, QC",
    "country": "Canada",
    "distance_km": 25,
    "job_type": "any",
    "remote_only": False,
    "max_days_old": 7,
    "min_hourly_pay": 0,
    "good_words": [],
    "bad_words": ["senior", "manager", "director"],
    "sites": ["indeed", "linkedin", "google", "jobbank"],
    "results_per_site": 20,
}


# ---------- small helpers that ask one question each ----------

def ask_text(question, default):
    answer = input(f"{question} [{default}]: ").strip()
    return answer or default


def ask_list(question, default):
    """Ask for a comma separated list, like: cook, line cook, prep cook"""
    shown = ", ".join(default) if default else "none"
    answer = input(f"{question} (separate with commas) [{shown}]: ").strip()
    if not answer:
        return default
    if answer.lower() == "none":
        return []
    return [part.strip() for part in answer.split(",") if part.strip()]


def ask_number(question, default):
    while True:
        answer = input(f"{question} [{default}]: ").strip()
        if not answer:
            return default
        try:
            return float(answer) if "." in answer else int(answer)
        except ValueError:
            print("  Please type a number.")


def ask_yes_no(question, default):
    shown = "y" if default else "n"
    while True:
        answer = input(f"{question} (y/n) [{shown}]: ").strip().lower()
        if not answer:
            return default
        if answer in ("y", "yes", "o", "oui"):
            return True
        if answer in ("n", "no", "non"):
            return False
        print("  Please type y or n.")


def ask_choice(question, choices, default):
    options = "/".join(choices)
    while True:
        answer = input(f"{question} ({options}) [{default}]: ").strip().lower()
        if not answer:
            return default
        if answer in choices:
            return answer
        print(f"  Please pick one of: {options}")


def ask_sites(default):
    print("  Sites you can search (type 'all' for every one):")
    for name, hint in SITES.items():
        print(f"    {name:13} {hint}")
    while True:
        picked = ask_list("Which sites should I search?", default)
        if [s.lower() for s in picked] == ["all"]:
            picked = list(SITES)
        unknown = [s for s in picked if s.lower() not in SITES]
        if picked and not unknown:
            # Sites that need a key: ask for it now, drop the site if you skip
            usable = more_sites.ask_missing_keys([s.lower() for s in picked])
            if usable:
                return usable
            print("  No usable sites left, pick again.")
            continue
        print(f"  I don't know these sites: {', '.join(unknown) or '(none picked)'}")


# ---------- the interview ----------

def load_saved():
    if PREFS_FILE.exists():
        try:
            saved = json.loads(PREFS_FILE.read_text(encoding="utf-8"))
            return {**DEFAULTS, **saved}   # saved answers win over defaults
        except json.JSONDecodeError:
            print("(preferences.json is broken, starting fresh)")
    return None


def save(prefs):
    PREFS_FILE.write_text(json.dumps(prefs, indent=2), encoding="utf-8")


def show(prefs):
    for key, value in prefs.items():
        if isinstance(value, list):
            value = ", ".join(value) or "none"
        print(f"  {key:17} {value}")


def interview():
    """Ask every question and return a dict of answers."""
    saved = load_saved()
    if saved:
        print("Last time you searched with:")
        show(saved)
        if ask_yes_no("Use the same answers?", True):
            saved["sites"] = more_sites.ask_missing_keys(saved["sites"]) or ["indeed"]
            return saved
    d = saved or DEFAULTS   # previous answers become the defaults

    print("\nA few questions first. Press Enter to keep the value in [brackets].\n")
    prefs = {
        "job_titles": ask_list("What job(s) are you looking for?", d["job_titles"]),
        "location": ask_text("Where? (city, province)", d["location"]),
        "country": ask_text("Country (Indeed needs this)", d["country"]),
        "distance_km": ask_number("How far are you willing to travel, in km?", d["distance_km"]),
        "job_type": ask_choice("Job type?", list(JOB_TYPES), d["job_type"]),
        "remote_only": ask_yes_no("Remote jobs only?", d["remote_only"]),
        "max_days_old": ask_number("Only jobs posted in the last how many days?", d["max_days_old"]),
        "min_hourly_pay": ask_number(
            "Minimum pay in $/hour (0 = don't care)", d["min_hourly_pay"]),
        "good_words": ask_list(
            "Words you WANT to see (they push a job up the list), e.g. student, weekend, bilingual",
            d["good_words"]),
        "bad_words": ask_list(
            "Words you DON'T want in the job title (those jobs get removed)", d["bad_words"]),
        "sites": ask_sites(d["sites"]),
        "results_per_site": ask_number("How many results per site, per job title?", d["results_per_site"]),
    }

    if not prefs["job_titles"]:
        print("You need at least one job title, using 'cook'.")
        prefs["job_titles"] = ["cook"]

    save(prefs)
    return prefs
