"""Smoke tests — cars_enricher.py"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import pytest
from cleaner.cars_enricher import (
    enrich_cars,
    _parse_year,
    _parse_km,
    _year_bucket,
    _km_bucket,
)

# ── Fixtures ──────────────────────────────────────────────────────────────────

def _listing(title: str, price: float, model: str = "seat ibiza", url: str = "") -> dict:
    return {"title": title, "price": price, "model_query": model, "url": url or title}


def _make_group(price_list: list[float], model: str = "seat ibiza") -> list[dict]:
    return [
        _listing(f"Seat Ibiza 2019 30000km {i}", p, model, f"http://car{i}")
        for i, p in enumerate(price_list)
    ]


# ── Parser tests ─────────────────────────────────────────────────────────────

def test_parse_year_finds_valid():
    assert _parse_year("Seat Ibiza 2019 30.000km") == 2019

def test_parse_year_none_on_missing():
    assert _parse_year("Seat Ibiza sin año") is None

def test_parse_km_standard():
    assert _parse_km("30.000 km") == 30000

def test_parse_km_with_space():
    assert _parse_km("30 000 km") == 30000

def test_parse_km_none_on_missing():
    assert _parse_km("Sin kilometraje") is None

def test_year_bucket():
    assert _year_bucket(2021) == "2020+"
    assert _year_bucket(2017) == "2015-2019"
    assert _year_bucket(2012) == "2010-2014"
    assert _year_bucket(2005) == "<2010"
    assert _year_bucket(None) == "desconocido"

def test_km_bucket():
    assert _km_bucket(20000)  == "0-50k"
    assert _km_bucket(75000)  == "50k-100k"
    assert _km_bucket(120000) == "100k-150k"
    assert _km_bucket(200000) == "150k+"
    assert _km_bucket(None)   == "desconocido"


# ── Arbitrage logic ───────────────────────────────────────────────────────────

def test_high_opportunity_detected():
    """Listing 30% below median → HIGH."""
    listings = _make_group([10000, 10000, 10000, 10000, 10000, 7000])
    results = enrich_cars(listings, arbitrage_threshold=0.15)
    highs = [r for r in results if r["opportunity"] == "HIGH"]
    assert len(highs) >= 1
    assert highs[0]["price"] == 7000

def test_overpriced_detected():
    """Listing above median → SOBREVALORADO."""
    listings = _make_group([10000, 10000, 10000, 10000, 10000, 15000])
    results = enrich_cars(listings, arbitrage_threshold=0.15)
    sobre = [r for r in results if r["opportunity"] == "SOBREVALORADO"]
    assert len(sobre) >= 1

def test_normal_price():
    """Listing at median → NORMAL."""
    listings = _make_group([10000] * 6)
    results = enrich_cars(listings, arbitrage_threshold=0.15)
    normals = [r for r in results if r["opportunity"] == "NORMAL"]
    assert len(normals) == 6

def test_small_group_returns_unknown():
    """Group with <5 samples → market_median=None → UNKNOWN (no falsos positivos)."""
    listings = _make_group([10000, 5000, 9000], model="cupra leon")  # n=3 < MIN_SAMPLE_SIZE
    results = enrich_cars(listings, arbitrage_threshold=0.15)
    unknowns = [r for r in results if r["opportunity"] == "UNKNOWN"]
    assert len(unknowns) == 3, f"Expected 3 UNKNOWN, got {[(r['price'], r['opportunity']) for r in results]}"

def test_no_price_filtered_out():
    """Listings without price are filtered before analysis."""
    listings = [
        _listing("Seat Ibiza 2019", 0, url="http://a"),
        _listing("Seat Ibiza 2019", None, url="http://b"),  # type: ignore
    ]
    results = enrich_cars(listings)
    assert results == []

def test_empty_input():
    assert enrich_cars([]) == []

def test_output_has_required_fields():
    listings = _make_group([10000] * 6)
    results = enrich_cars(listings)
    for r in results:
        assert "opportunity" in r
        assert "market_median" in r
        assert "price_delta_pct" in r
