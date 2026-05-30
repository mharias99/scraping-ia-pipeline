"""Smoke tests — digital_enricher.py (scoring puro, sin llamadas a IA ni Firecrawl)"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from cleaner.digital_enricher import (
    maps_score_v2,
    is_healthy,
    total_score,
    band_from_score,
    dedup_businesses,
    enrich_businesses,
)


# ── maps_score_v2 ─────────────────────────────────────────────────────────────

def test_maps_score_low_rating_high_score():
    biz = {"rating": 2.5, "review_count": 5, "claimed": False}
    score = maps_score_v2(biz)
    assert score == 40  # 25 (rating<3) + 10 (reviews<10) + 5 (unclaimed)

def test_maps_score_no_rating():
    biz = {"rating": None, "review_count": 0, "claimed": True}
    score = maps_score_v2(biz)
    assert score == 25  # 15 (no rating) + 10 (no reviews)

def test_maps_score_good_business():
    biz = {"rating": 4.8, "review_count": 200, "claimed": True}
    score = maps_score_v2(biz)
    assert score == 0

def test_maps_score_capped_at_50():
    biz = {"rating": 1.0, "review_count": 0, "claimed": False}
    score = maps_score_v2(biz)
    assert score <= 50


# ── is_healthy (gate de auto-descarte) ───────────────────────────────────────

def test_healthy_gate_triggers():
    assert is_healthy({"rating": 4.8, "review_count": 150}) is True

def test_healthy_gate_not_enough_reviews():
    assert is_healthy({"rating": 4.8, "review_count": 50}) is False

def test_healthy_gate_not_enough_rating():
    assert is_healthy({"rating": 4.2, "review_count": 200}) is False

def test_healthy_gate_edge():
    assert is_healthy({"rating": 4.5, "review_count": 100}) is True


# ── band_from_score ───────────────────────────────────────────────────────────

def test_band_high():
    assert band_from_score(65) == "HIGH"
    assert band_from_score(45) == "HIGH"

def test_band_medium():
    assert band_from_score(40) == "MEDIUM"
    assert band_from_score(25) == "MEDIUM"

def test_band_low():
    assert band_from_score(24) == "LOW"
    assert band_from_score(0)  == "LOW"


# ── dedup_businesses ─────────────────────────────────────────────────────────

def test_dedup_by_phone():
    bizs = [
        {"name": "A", "phone": "612345678", "website": ""},
        {"name": "B", "phone": "612345678", "website": ""},  # dup
        {"name": "C", "phone": "699999999", "website": ""},
    ]
    result = dedup_businesses(bizs)
    assert len(result) == 2

def test_dedup_by_domain():
    bizs = [
        {"name": "A", "phone": "", "website": "https://example.com/sede1"},
        {"name": "B", "phone": "", "website": "https://example.com/sede2"},  # same domain
        {"name": "C", "phone": "", "website": "https://other.com"},
    ]
    result = dedup_businesses(bizs)
    assert len(result) == 2

def test_dedup_no_duplicates():
    bizs = [{"name": str(i), "phone": str(i), "website": ""} for i in range(5)]
    assert len(dedup_businesses(bizs)) == 5


# ── permanently_closed filter ────────────────────────────────────────────────

def test_permanently_closed_filtered(monkeypatch):
    """permanently_closed=True businesses must be removed before scoring."""
    import cleaner.digital_enricher as de

    # Patch the heavy dependencies so test runs without API calls
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")

    def _fake_inspect(businesses, top_n=25):
        for b in businesses:
            b.update({"web_status": "no_web", "web_score": 25,
                       "web_live": False, "web_https": False,
                       "web_booking": False, "web_pixel_meta": False,
                       "web_pixel_ga": False})
        return businesses

    def _fake_enrich_batch(client, batch, model, attempt=1):
        return [{"index": i, "weaknesses": ["test"], "call_script": "test"}
                for i in range(len(batch))]

    monkeypatch.setattr("cleaner.digital_enricher._enrich_batch_v2", _fake_enrich_batch)

    import scraper.web_inspector as wi
    monkeypatch.setattr(wi, "inspect_websites", _fake_inspect)

    businesses = [
        {"name": "Open",   "phone": "111", "website": "", "rating": 2.0,
         "review_count": 5, "claimed": False, "permanently_closed": False},
        {"name": "Closed", "phone": "222", "website": "", "rating": 2.0,
         "review_count": 5, "claimed": False, "permanently_closed": True},
    ]

    import anthropic
    monkeypatch.setattr(anthropic, "Anthropic", lambda **kw: object())

    results = de.enrich_businesses(businesses, model="claude-haiku-4-5-20251001")
    names = [r["name"] for r in results]
    assert "Closed" not in names
    assert "Open" in names
