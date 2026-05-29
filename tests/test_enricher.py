import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import anthropic
import pandas as pd
import pytest

from cleaner.enricher import (
    build_dataframe,
    build_prompt,
    enrich_batch,
    load_raw_data,
    merge_results,
    run_enricher,
    save_csv,
)
from conftest import make_anthropic_response


# ── load_raw_data ─────────────────────────────────────────────────────────────

class TestLoadRawData:
    def test_loads_valid_json(self, raw_json_file: Path, sample_raw_batch: list) -> None:
        result = load_raw_data(raw_json_file)
        assert result == sample_raw_batch

    def test_raises_if_file_missing(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError):
            load_raw_data(tmp_path / "nonexistent.json")

    def test_raises_if_file_empty(self, tmp_path: Path) -> None:
        empty = tmp_path / "empty.json"
        empty.write_text("[]")
        with pytest.raises(ValueError, match="empty"):
            load_raw_data(empty)


# ── build_prompt ──────────────────────────────────────────────────────────────

class TestBuildPrompt:
    def test_includes_all_quotes(self, sample_raw_batch: list) -> None:
        prompt = build_prompt(sample_raw_batch)
        assert "Shakespeare" in prompt
        assert "Descartes" in prompt
        assert "Bacon" in prompt

    def test_includes_batch_indices(self, sample_raw_batch: list) -> None:
        prompt = build_prompt(sample_raw_batch)
        assert "[0]" in prompt
        assert "[1]" in prompt
        assert "[2]" in prompt

    def test_includes_tags(self, sample_raw_batch: list) -> None:
        prompt = build_prompt(sample_raw_batch)
        assert "life" in prompt
        assert "philosophy" in prompt

    def test_single_item_batch(self) -> None:
        batch = [{"text": "Hello", "author": "World", "tags": ["tag1"]}]
        prompt = build_prompt(batch)
        assert "[0]" in prompt
        assert "Hello" in prompt


# ── merge_results ─────────────────────────────────────────────────────────────

class TestMergeResults:
    def test_merges_all_fields(
        self, sample_raw_batch: list, sample_enriched: list
    ) -> None:
        merged = merge_results(sample_raw_batch, sample_enriched, batch_offset=0)
        assert len(merged) == 3
        assert merged[0]["text"] == "To be or not to be."
        assert merged[0]["category"] == "philosophy"
        assert merged[0]["tags"] == "life, death"
        assert merged[0]["key_themes"] == "existence, choice"

    def test_joins_tags_as_string(
        self, sample_raw_batch: list, sample_enriched: list
    ) -> None:
        merged = merge_results(sample_raw_batch, sample_enriched, batch_offset=0)
        assert isinstance(merged[0]["tags"], str)

    def test_skips_record_with_missing_enrichment(
        self, sample_raw_batch: list
    ) -> None:
        partial_enriched = [
            {"index": 0, "category": "philosophy", "sentiment": "neutral",
             "key_themes": ["x"], "complexity": "simple"},
        ]
        merged = merge_results(sample_raw_batch, partial_enriched, batch_offset=0)
        assert len(merged) == 1
        assert merged[0]["text"] == "To be or not to be."

    def test_empty_enriched_returns_empty(self, sample_raw_batch: list) -> None:
        merged = merge_results(sample_raw_batch, [], batch_offset=0)
        assert merged == []


# ── build_dataframe ───────────────────────────────────────────────────────────

class TestBuildDataframe:
    def test_drops_duplicate_texts(self) -> None:
        records = [
            {"text": "Same.", "author": "A", "tags": "t", "category": "life",
             "sentiment": "positive", "key_themes": "x", "complexity": "simple"},
            {"text": "Same.", "author": "B", "tags": "t", "category": "life",
             "sentiment": "positive", "key_themes": "x", "complexity": "simple"},
        ]
        df = build_dataframe(records)
        assert len(df) == 1

    def test_normalizes_string_columns(self) -> None:
        records = [{
            "text": "Quote", "author": "  AUTHOR  ", "tags": "tag",
            "category": "  LIFE  ", "sentiment": "POSITIVE",
            "key_themes": "theme", "complexity": "SIMPLE",
        }]
        df = build_dataframe(records)
        assert df["author"].iloc[0] == "author"
        assert df["category"].iloc[0] == "life"
        assert df["sentiment"].iloc[0] == "positive"
        assert df["complexity"].iloc[0] == "simple"

    def test_resets_index(self, sample_merged_records: list) -> None:
        df = build_dataframe(sample_merged_records)
        assert list(df.index) == list(range(len(df)))

    def test_returns_dataframe(self, sample_merged_records: list) -> None:
        df = build_dataframe(sample_merged_records)
        assert isinstance(df, pd.DataFrame)


# ── save_csv ──────────────────────────────────────────────────────────────────

class TestSaveCsv:
    def test_creates_csv_file(
        self, tmp_path: Path, sample_merged_records: list
    ) -> None:
        df = build_dataframe(sample_merged_records)
        with patch("cleaner.enricher.OUTPUT_DIR", tmp_path):
            path = save_csv(df)
        assert path.exists()
        assert path.suffix == ".csv"

    def test_csv_has_no_index_column(
        self, tmp_path: Path, sample_merged_records: list
    ) -> None:
        df = build_dataframe(sample_merged_records)
        with patch("cleaner.enricher.OUTPUT_DIR", tmp_path):
            path = save_csv(df)
        loaded = pd.read_csv(path)
        assert "Unnamed: 0" not in loaded.columns

    def test_csv_filename_contains_date(
        self, tmp_path: Path, sample_merged_records: list
    ) -> None:
        df = build_dataframe(sample_merged_records)
        with patch("cleaner.enricher.OUTPUT_DIR", tmp_path):
            path = save_csv(df)
        assert "dataset_" in path.name

    def test_csv_preserves_all_rows(
        self, tmp_path: Path, sample_merged_records: list
    ) -> None:
        df = build_dataframe(sample_merged_records)
        with patch("cleaner.enricher.OUTPUT_DIR", tmp_path):
            path = save_csv(df)
        assert len(pd.read_csv(path)) == len(df)


# ── enrich_batch ──────────────────────────────────────────────────────────────

class TestEnrichBatch:
    def test_returns_enriched_list_on_success(
        self, sample_raw_batch: list, sample_enriched: list
    ) -> None:
        client = MagicMock()
        client.messages.create.return_value = make_anthropic_response(sample_enriched)

        result = enrich_batch(client, sample_raw_batch)
        assert result == sample_enriched

    def test_raises_value_error_if_no_tool_block(
        self, sample_raw_batch: list
    ) -> None:
        response = MagicMock()
        response.content = []  # no tool_use block
        client = MagicMock()
        client.messages.create.return_value = response

        with pytest.raises(ValueError, match="No tool_use block"):
            enrich_batch(client, sample_raw_batch)

    def test_retries_on_rate_limit(
        self, sample_raw_batch: list, sample_enriched: list
    ) -> None:
        client = MagicMock()
        client.messages.create.side_effect = [
            anthropic.RateLimitError.__new__(anthropic.RateLimitError),
            make_anthropic_response(sample_enriched),
        ]

        with patch("cleaner.enricher.time.sleep"):
            result = enrich_batch(client, sample_raw_batch)

        assert result == sample_enriched
        assert client.messages.create.call_count == 2

    def test_returns_empty_after_max_retries(
        self, sample_raw_batch: list
    ) -> None:
        client = MagicMock()
        client.messages.create.side_effect = anthropic.RateLimitError.__new__(
            anthropic.RateLimitError
        )

        with patch("cleaner.enricher.time.sleep"):
            result = enrich_batch(client, sample_raw_batch, attempt=4)

        assert result == []

    def test_raises_runtime_error_on_insufficient_credits(
        self, sample_raw_batch: list
    ) -> None:
        class CreditError(anthropic.BadRequestError):
            def __init__(self) -> None:
                pass
            def __str__(self) -> str:
                return "credit balance is too low"

        client = MagicMock()
        client.messages.create.side_effect = CreditError()

        with pytest.raises(RuntimeError, match="insufficient credits"):
            enrich_batch(client, sample_raw_batch)


# ── run_enricher ──────────────────────────────────────────────────────────────

class TestRunEnricher:
    def test_raises_if_no_api_key(self) -> None:
        with patch.dict("os.environ", {}, clear=True):
            with patch("cleaner.enricher.os.getenv", return_value=None):
                with pytest.raises(EnvironmentError, match="ANTHROPIC_API_KEY"):
                    run_enricher()
