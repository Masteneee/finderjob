"""
more_sites.py: job sites that JobSpy doesn't cover.

  jobbank   Job Bank / Guichet-Emplois (Government of Canada). We read the
            search results page like a browser does (no API exists).
  adzuna    Adzuna, an official API. Needs a free key.
  jooble    Jooble, an official API. Needs a free key.
  remotive  Remotive, an official API for remote jobs. No key needed.

Every site has one function that takes (title, prefs) and returns a list of
jobs. Each job is a dict with the SAME keys JobSpy uses (title, company,
location, date_posted, min_amount, max_amount, interval, job_url,
description, site), so ranking.py doesn't care where a job came from.
"""

import json
import re
from datetime import date, datetime
from pathlib import Path

import requests
from bs4 import BeautifulSoup

KEYS_FILE = Path(__file__).parent / "api_keys.json"
TIMEOUT = 20  # seconds to wait for a site before giving up
BROWSER = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                         "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36"}


# ---------- small shared helpers ----------

def make_job(site, title, job_url, company=None, location=None, date_posted=None,
             min_amount=None, max_amount=None, interval=None, description=None):
    """Build a job dict in the shape the rest of the program expects."""
    return {"site": site, "title": (title or "").strip(), "job_url": job_url,
            "company": company, "location": location, "date_posted": date_posted,
            "min_amount": min_amount, "max_amount": max_amount, "interval": interval,
            "description": description}


def parse_date(text):
    """Turn '2026-10-30T12:00:00Z' or 'October 30, 2026' into a date. None if we can't."""
    if not text:
        return None
    text = text.strip()
    try:
        return date.fromisoformat(text[:10])          # 2026-10-30...
    except ValueError:
        pass
    for pattern in ("%B %d, %Y", "%b %d, %Y", "%d %B %Y"):  # October 30, 2026 / Oct 30, 2026
        try:
            return datetime.strptime(text, pattern).date()
        except ValueError:
            pass
    return None


# Words a site uses for each pay period, in English and French
PERIOD_WORDS = {
    "hourly": ["hour", "hourly", "/h", "/hr", "heure", "horaire"],
    "daily": ["day", "daily", "jour"],
    "weekly": ["week", "weekly", "semaine"],
    "monthly": ["month", "monthly", "mois"],
    "yearly": ["year", "yearly", "annually", "annual", "/yr", "an", "année", "annuel"],
}


def to_number(piece):
    piece = piece.strip().replace(" ", "").replace(" ", "")
    if re.fullmatch(r"\d+,\d{2}", piece):   # 17,50 is French for 17.50
        return float(piece.replace(",", "."))
    return float(piece.replace(",", ""))     # 45,000 is English for 45000


def parse_salary(text):
    """Read pay written by a human, like '$17.00 to $19.50 hourly' or '45 000 $ par année'.
    Returns (min, max, interval). Anything we can't read gives (None, None, None)."""
    if not text:
        return None, None, None
    lower = text.lower()
    # Numbers can look like 17, 17.50, 45,000.00, 45 000 (French spacing) or 17,50 (French decimal)
    numbers = [to_number(n) for n in re.findall(r"\d[\d,  ]*(?:\.\d+)?", lower)]
    numbers = [n for n in numbers if n > 0]
    if not numbers:
        return None, None, None
    if re.search(r"\d\s*k\b", lower) and numbers[0] < 1000:   # "$45k" means 45 000
        numbers = [n * 1000 for n in numbers]

    interval = None
    for period, words in PERIOD_WORDS.items():
        if any(re.search(rf"(?<![a-zé]){re.escape(w)}(?![a-zé])", lower) for w in words):
            interval = period
            break
    if interval is None:   # no word? guess from the size of the number
        interval = "hourly" if numbers[0] < 200 else "yearly"

    return numbers[0], (numbers[1] if len(numbers) > 1 else None), interval


def get_json(method, url, **kwargs):
    response = requests.request(method, url, timeout=TIMEOUT, **kwargs)
    response.raise_for_status()      # turns "403 Forbidden" etc. into a clear error
    return response.json()


# ---------- API keys (saved in api_keys.json, never uploaded to GitHub) ----------

def load_keys():
    return json.loads(KEYS_FILE.read_text()) if KEYS_FILE.exists() else {}


def save_keys(keys):
    KEYS_FILE.write_text(json.dumps(keys, indent=2))


NEEDS_KEY = {
    "adzuna": (["app_id", "app_key"], "https://developer.adzuna.com/signup"),
    "jooble": (["key"], "https://jooble.org/api/about"),
}


def ask_missing_keys(sites):
    """For each picked site that needs a key we don't have yet, ask for it.
    Returns the list of sites we can actually use."""
    keys = load_keys()
    usable = []
    for site in sites:
        if site not in NEEDS_KEY or keys.get(site):
            usable.append(site)
            continue
        fields, signup = NEEDS_KEY[site]
        print(f"\n  {site} needs a free key. Get one at {signup}")
        print("  (Press Enter to skip this site for now.)")
        answers = {f: input(f"  {site} {f}: ").strip() for f in fields}
        if all(answers.values()):
            keys[site] = answers
            save_keys(keys)
            usable.append(site)
        else:
            print(f"  Skipping {site}.")
    return usable


# ---------- Job Bank (Government of Canada) ----------

PROVINCES = {"québec": "QC", "quebec": "QC", "ontario": "ON", "british columbia": "BC",
             "alberta": "AB", "manitoba": "MB", "saskatchewan": "SK", "nova scotia": "NS",
             "new brunswick": "NB", "newfoundland and labrador": "NL",
             "prince edward island": "PE", "northwest territories": "NT",
             "nunavut": "NU", "yukon": "YT"}

_city_ids = {}   # remember lookups so we ask Job Bank only once per run


def jobbank_city_id(location):
    """Job Bank ignores a typed location in the address. Its website first turns the
    city name into a number (Montréal = 22446) with this lookup service, then
    searches with mid=<that number>. We do the same.
    Returns (city_id or None, province code or None)."""
    city, _, province = location.partition(",")
    province = province.strip().upper()[:2] or None
    if location not in _city_ids:
        data = get_json("GET", "https://www.jobbank.gc.ca/core/ta-cityprovsuggest_en/select",
                        params={"q": city.strip(), "fq": "NOT postalcode_cnt:0",
                                "wt": "json", "rows": 10}, headers=BROWSER)
        cities = data.get("response", {}).get("docs", [])
        # "Montreal" also matches Montreal Lake (SK), so prefer the right province
        same_province = [c for c in cities
                         if PROVINCES.get(str(c.get("province_name")).lower()) == province]
        best = (same_province or cities or [{}])[0]
        _city_ids[location] = best.get("city_id")
    return _city_ids[location], province


def search_jobbank(title, prefs):
    """Job Bank has no public API, so we download the search page and pick
    the jobs out of the HTML with BeautifulSoup."""
    params = {"term": title, "sort": "D"}
    city_id, province = jobbank_city_id(prefs["location"])
    if city_id:
        params["mid"] = city_id
        params["d"] = int(prefs["distance_km"])   # Job Bank uses km
    elif province:
        print(f"    (Job Bank doesn't know '{prefs['location']}', searching all of {province})")
        params["fprov"] = province
    else:
        print(f"    (Job Bank doesn't know '{prefs['location']}', searching all of Canada)")

    page = requests.get("https://www.jobbank.gc.ca/jobsearch/jobsearch",
                        params=params, headers=BROWSER, timeout=TIMEOUT)
    page.raise_for_status()
    return parse_jobbank_html(page.text)[: int(prefs["results_per_site"])]


def parse_jobbank_html(html_text):
    soup = BeautifulSoup(html_text, "html.parser")
    jobs = []
    for link in soup.select("a.resultJobItem"):
        def text_of(css):
            tag = link.select_one(css)
            if not tag:
                return None
            for hidden in tag.select(".wb-inv"):   # screen-reader labels like "Location"
                hidden.decompose()
            return " ".join(tag.get_text(" ").split()) or None

        href = link.get("href", "").split(";")[0]   # drop the ;jsessionid=... part
        low, high, interval = parse_salary(text_of(".salary"))
        jobs.append(make_job(
            site="jobbank",
            title=text_of(".noctitle"),
            job_url="https://www.jobbank.gc.ca" + href if href.startswith("/") else href,
            company=text_of(".business"),
            location=text_of(".location"),
            date_posted=parse_date(text_of(".date")),
            min_amount=low, max_amount=high, interval=interval))
    if not jobs and "resultJobItem" not in html_text and "noctitle" not in html_text:
        # The page loaded but has none of the parts we look for: probably a redesign
        print("    (Job Bank's page looks different than expected; its layout may have changed)")
    return [j for j in jobs if j["title"]]


# ---------- Adzuna ----------

ADZUNA_COUNTRIES = {"canada": "ca", "usa": "us", "us": "us", "united states": "us",
                    "uk": "gb", "united kingdom": "gb", "france": "fr", "australia": "au"}

ADZUNA_JOB_TYPE = {"full-time": "full_time", "part-time": "part_time", "contract": "contract"}


def search_adzuna(title, prefs):
    keys = load_keys()["adzuna"]
    country = ADZUNA_COUNTRIES.get(prefs["country"].lower(), "ca")
    params = {
        "app_id": keys["app_id"], "app_key": keys["app_key"],
        "what": title, "where": prefs["location"],
        "distance": int(prefs["distance_km"]),          # Adzuna uses km
        "max_days_old": int(prefs["max_days_old"]),
        "results_per_page": min(50, int(prefs["results_per_site"])),
        "sort_by": "date", "content-type": "application/json",
    }
    if prefs["job_type"] in ADZUNA_JOB_TYPE:
        params[ADZUNA_JOB_TYPE[prefs["job_type"]]] = 1

    data = get_json("GET", f"https://api.adzuna.com/v1/api/jobs/{country}/search/1", params=params)
    jobs = []
    for item in data.get("results", []):
        guessed = str(item.get("salary_is_predicted")) == "1"   # Adzuna's own estimate, not real
        jobs.append(make_job(
            site="adzuna",
            title=item.get("title"),
            job_url=item.get("redirect_url"),
            company=(item.get("company") or {}).get("display_name"),
            location=(item.get("location") or {}).get("display_name"),
            date_posted=parse_date(item.get("created")),
            min_amount=None if guessed else item.get("salary_min"),
            max_amount=None if guessed else item.get("salary_max"),
            interval=None if guessed or not item.get("salary_min") else "yearly",
            description=item.get("description")))
    return jobs


# ---------- Jooble ----------

def search_jooble(title, prefs):
    key = load_keys()["jooble"]["key"]
    body = {"keywords": title, "location": prefs["location"],
            "radius": str(int(prefs["distance_km"])), "page": "1",
            "ResultOnPage": str(int(prefs["results_per_site"]))}
    data = get_json("POST", f"https://jooble.org/api/{key}", json=body)
    jobs = []
    for item in data.get("jobs", []):
        low, high, interval = parse_salary(item.get("salary"))
        jobs.append(make_job(
            site="jooble",
            title=item.get("title"),
            job_url=item.get("link"),
            company=item.get("company"),
            location=item.get("location"),
            date_posted=parse_date(item.get("updated")),
            min_amount=low, max_amount=high, interval=interval,
            description=item.get("snippet")))
    return jobs


# ---------- Remotive (remote jobs only) ----------

def search_remotive(title, prefs):
    if not prefs["remote_only"]:
        print("    (remotive skipped: it only has remote jobs. Answer 'y' to 'Remote jobs only?')")
        return []
    data = get_json("GET", "https://remotive.com/api/remote-jobs",
                    params={"search": title, "limit": int(prefs["results_per_site"])})
    jobs = []
    for item in data.get("jobs", []):
        low, high, interval = parse_salary(item.get("salary"))
        jobs.append(make_job(
            site="remotive",
            title=item.get("title"),
            job_url=item.get("url"),
            company=item.get("company_name"),
            location="Remote: " + (item.get("candidate_required_location") or "anywhere"),
            date_posted=parse_date(item.get("publication_date")),
            min_amount=low, max_amount=high, interval=interval,
            description=item.get("description")))
    return jobs


# The name you type -> the function that searches that site
EXTRA_SITES = {
    "jobbank": search_jobbank,
    "adzuna": search_adzuna,
    "jooble": search_jooble,
    "remotive": search_remotive,
}
