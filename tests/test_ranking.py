"""
Tests for ranking.py. Run with:   python -m pytest
They use fake jobs, so they work without internet.
"""

import sys
from datetime import date, timedelta
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent))   # so we can import ranking.py
import ranking

TODAY = date(2026, 11, 1)

PREFS = {
    "job_titles": ["line cook"],
    "max_days_old": 7,
    "min_hourly_pay": 17,
    "good_words": ["weekend", "student"],
    "bad_words": ["senior", "manager"],
}


def job(title, company="Resto", days=1, pay=None, interval="hourly", description=""):
    return {"title": title, "company": company, "description": description,
            "date_posted": TODAY - timedelta(days=days) if days is not None else None,
            "min_amount": pay, "max_amount": None, "interval": interval if pay else None,
            "job_url": f"https://example.com/{title}/{company}"}


def test_whole_word_only():
    assert ranking.has_word("Line Cook - Evenings", "cook")
    assert not ranking.has_word("Cookie Factory Worker", "cook")


def test_yearly_salary_becomes_hourly():
    assert ranking.hourly_pay(job("x", pay=41600, interval="yearly")) == 20.0
    assert ranking.hourly_pay(job("x")) is None


def test_empty_pandas_cells_are_none():
    assert ranking.clean(float("nan")) is None
    assert ranking.clean(pd.NaT) is None
    assert ranking.days_old({"date_posted": pd.NaT}, TODAY) is None


def test_duplicates_across_sites_removed():
    jobs = [job("Line Cook", "Joe Beef"), job("line cook ", "JOE BEEF"), job("Line Cook", "Other")]
    assert len(ranking.remove_duplicates(jobs)) == 2


def test_filters():
    kept, rejected = ranking.rank([
        job("Senior Line Cook"),          # bad word
        job("Line Cook", "Old", days=30), # too old
        job("Line Cook", "Cheap", pay=15),# pays under 17
        job("Line Cook", "Ok", pay=19),   # keeper
        job("Line Cook", "NoPay"),        # pay hidden: kept, we can't know
    ], PREFS, TODAY)
    assert rejected == 3
    assert {j["company"] for j in kept} == {"Ok", "NoPay"}


def test_best_match_first():
    kept, _ = ranking.rank([
        job("Dishwasher", "A", days=5),
        job("Line Cook", "B", days=5),
        job("Weekend Line Cook", "C", days=0, pay=20),
    ], PREFS, TODAY)
    assert [j["company"] for j in kept] == ["C", "B", "A"]
    assert "'weekend' in title" in kept[0]["why"]
