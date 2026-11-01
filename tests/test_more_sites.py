"""
Tests for more_sites.py, using fake web pages and fake API answers,
so they work without internet. Run with:   python -m pytest
"""

import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
import more_sites

PREFS = {"location": "Montreal, QC", "country": "Canada", "distance_km": 25,
         "max_days_old": 7, "results_per_site": 20, "job_type": "part-time",
         "remote_only": True}


# ---------- reading pay written by humans ----------

def test_salary_english():
    assert more_sites.parse_salary("$17.00 to $19.50 hourly") == (17.0, 19.5, "hourly")
    assert more_sites.parse_salary("$45,000.00 annually") == (45000.0, None, "yearly")
    assert more_sites.parse_salary("$17 - $20 per hour") == (17.0, 20.0, "hourly")
    assert more_sites.parse_salary("$45k - $50k") == (45000.0, 50000.0, "yearly")


def test_salary_french():
    assert more_sites.parse_salary("17,50 $ de l'heure") == (17.5, None, "hourly")
    assert more_sites.parse_salary("45 000 $ par année") == (45000.0, None, "yearly")


def test_salary_unreadable():
    assert more_sites.parse_salary("Competitive") == (None, None, None)
    assert more_sites.parse_salary(None) == (None, None, None)


def test_dates():
    assert more_sites.parse_date("2026-10-30T12:00:00Z") == date(2026, 10, 30)
    assert more_sites.parse_date("October 30, 2026") == date(2026, 10, 30)
    assert more_sites.parse_date("yesterday-ish") is None


# ---------- Job Bank page ----------

JOBBANK_HTML = """
<div id="ajaxupdateform:result_block">
<article id="article-43000001">
  <a href="/jobsearch/jobposting/43000001;jsessionid=ABC?source=searchresults" class="resultJobItem">
    <h3 class="title"><span class="flag"></span><span class="noctitle"> line cook </span></h3>
    <ul class="list-unstyled">
      <li class="date">October 30, 2026</li>
      <li class="business">Restaurant Chez Nous</li>
      <li class="location"><span class="wb-inv">Location</span> Montréal (QC)</li>
      <li class="salary"><span class="wb-inv">Salary:</span> $17.50 to $19.00 hourly</li>
    </ul>
  </a>
</article>
<article id="article-43000002">
  <a href="/jobsearch/jobposting/43000002?source=searchresults" class="resultJobItem">
    <h3 class="title"><span class="noctitle">Cuisinier/cuisinière</span></h3>
    <ul class="list-unstyled"><li class="business">Café Y</li></ul>
  </a>
</article>
</div>"""


def test_jobbank_page():
    jobs = more_sites.parse_jobbank_html(JOBBANK_HTML)
    assert len(jobs) == 2
    first = jobs[0]
    assert first["title"] == "line cook"
    assert first["company"] == "Restaurant Chez Nous"
    assert first["location"] == "Montréal (QC)"        # the hidden "Location" label is gone
    assert first["date_posted"] == date(2026, 10, 30)
    assert (first["min_amount"], first["max_amount"], first["interval"]) == (17.5, 19.0, "hourly")
    assert first["job_url"] == "https://www.jobbank.gc.ca/jobsearch/jobposting/43000001"
    assert jobs[1]["min_amount"] is None and jobs[1]["date_posted"] is None


def test_jobbank_redesign_gives_empty_list(capsys):
    assert more_sites.parse_jobbank_html("<html><body>New design!</body></html>") == []
    assert "layout may have changed" in capsys.readouterr().out


# ---------- Job Bank city lookup ----------

def test_jobbank_picks_city_in_right_province(monkeypatch):
    more_sites._city_ids.clear()
    monkeypatch.setattr(more_sites, "get_json", lambda *a, **k: {"response": {"docs": [
        {"name": "Montreal Lake", "province_name": "Saskatchewan", "city_id": "30828"},
        {"name": "Montréal", "province_name": "Québec", "city_id": "22446"}]}})
    assert more_sites.jobbank_city_id("Montreal, QC") == ("22446", "QC")


def test_jobbank_unknown_city(monkeypatch):
    more_sites._city_ids.clear()
    monkeypatch.setattr(more_sites, "get_json", lambda *a, **k: {"response": {"docs": []}})
    assert more_sites.jobbank_city_id("Nowhereville, QC") == (None, "QC")


# ---------- the APIs, with a fake get_json ----------

def fake_answer(monkeypatch, answer):
    calls = []
    def fake_get_json(method, url, **kwargs):
        calls.append((method, url, kwargs))
        return answer
    monkeypatch.setattr(more_sites, "get_json", fake_get_json)
    return calls


def test_adzuna(monkeypatch):
    monkeypatch.setattr(more_sites, "load_keys", lambda: {"adzuna": {"app_id": "i", "app_key": "k"}})
    calls = fake_answer(monkeypatch, {"results": [
        {"title": "Prep Cook", "redirect_url": "https://adzuna/1", "created": "2026-10-31T08:00:00Z",
         "company": {"display_name": "Bistro"}, "location": {"display_name": "Montréal, Québec"},
         "salary_min": 36000, "salary_max": 40000, "salary_is_predicted": "0", "description": "..."},
        {"title": "Cook", "redirect_url": "https://adzuna/2", "salary_min": 50000,
         "salary_is_predicted": "1"},       # Adzuna guessed this pay: we ignore it
    ]})
    jobs = more_sites.search_adzuna("cook", PREFS)
    method, url, kwargs = calls[0]
    assert url.endswith("/jobs/ca/search/1")
    assert kwargs["params"]["part_time"] == 1 and kwargs["params"]["distance"] == 25
    assert jobs[0]["company"] == "Bistro" and jobs[0]["interval"] == "yearly"
    assert jobs[1]["min_amount"] is None


def test_jooble(monkeypatch):
    monkeypatch.setattr(more_sites, "load_keys", lambda: {"jooble": {"key": "abc"}})
    calls = fake_answer(monkeypatch, {"totalCount": 1, "jobs": [
        {"title": "Line Cook", "location": "Montréal, QC", "snippet": "Weekend shifts",
         "salary": "$18 - $21 per hour", "link": "https://jooble/1", "company": "Diner",
         "updated": "2026-10-29T00:00:00.0000000"}]})
    jobs = more_sites.search_jooble("line cook", PREFS)
    assert calls[0][0] == "POST" and calls[0][1] == "https://jooble.org/api/abc"
    assert jobs[0]["min_amount"] == 18 and jobs[0]["interval"] == "hourly"
    assert jobs[0]["date_posted"] == date(2026, 10, 29)


def test_remotive(monkeypatch):
    fake_answer(monkeypatch, {"jobs": [
        {"title": "Support Agent", "url": "https://remotive/1", "company_name": "Acme",
         "candidate_required_location": "Canada", "publication_date": "2026-10-31T10:00:00",
         "salary": "", "description": "<p>Hi</p>"}]})
    jobs = more_sites.search_remotive("support", PREFS)
    assert jobs[0]["location"] == "Remote: Canada"


def test_remotive_skipped_when_not_remote(monkeypatch):
    calls = fake_answer(monkeypatch, {"jobs": []})
    assert more_sites.search_remotive("cook", {**PREFS, "remote_only": False}) == []
    assert calls == []   # didn't even ask the site
