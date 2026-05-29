import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest


# ── HTML fixtures ────────────────────────────────────────────────────────────

QUOTE_HTML_WITH_NEXT = """
<html><body>
  <div class="quote">
    <span class="text">“The only way to do great work is to love what you do.”</span>
    <small class="author">Steve Jobs</small>
    <div class="tags">
      <a class="tag">work</a>
      <a class="tag">passion</a>
    </div>
  </div>
  <div class="quote">
    <span class="text">“In the middle of every difficulty lies opportunity.”</span>
    <small class="author">Albert Einstein</small>
    <div class="tags">
      <a class="tag">opportunity</a>
    </div>
  </div>
  <ul class="pager"><li class="next"><a href="/page/2/">Next</a></li></ul>
</body></html>
"""

QUOTE_HTML_NO_NEXT = """
<html><body>
  <div class="quote">
    <span class="text">“Last page quote.”</span>
    <small class="author">Unknown</small>
  </div>
</body></html>
"""

QUOTE_HTML_INCOMPLETE = """
<html><body>
  <div class="quote">
    <span class="text">“No author here.”</span>
  </div>
  <div class="quote">
    <small class="author">No text here</small>
  </div>
  <div class="quote">
    <span class="text">“Valid quote.”</span>
    <small class="author">Valid Author</small>
  </div>
</body></html>
"""


# ── Data fixtures ────────────────────────────────────────────────────────────

@pytest.fixture
def sample_raw_batch() -> list[dict]:
    return [
        {"text": "To be or not to be.", "author": "Shakespeare", "tags": ["life", "death"]},
        {"text": "I think therefore I am.", "author": "Descartes", "tags": ["philosophy"]},
        {"text": "Knowledge is power.", "author": "Bacon", "tags": ["knowledge"]},
    ]


@pytest.fixture
def sample_enriched() -> list[dict]:
    return [
        {"index": 0, "category": "philosophy", "sentiment": "neutral",
         "key_themes": ["existence", "choice"], "complexity": "moderate"},
        {"index": 1, "category": "philosophy", "sentiment": "neutral",
         "key_themes": ["consciousness", "identity"], "complexity": "complex"},
        {"index": 2, "category": "knowledge", "sentiment": "positive",
         "key_themes": ["power", "learning"], "complexity": "simple"},
    ]


@pytest.fixture
def sample_merged_records() -> list[dict]:
    return [
        {"text": "To be or not to be.", "author": "shakespeare", "tags": "life, death",
         "category": "philosophy", "sentiment": "neutral",
         "key_themes": "existence, choice", "complexity": "moderate"},
        {"text": "I think therefore I am.", "author": "descartes", "tags": "philosophy",
         "category": "philosophy", "sentiment": "neutral",
         "key_themes": "consciousness, identity", "complexity": "complex"},
    ]


@pytest.fixture
def raw_json_file(tmp_path: Path, sample_raw_batch: list[dict]) -> Path:
    path = tmp_path / "quotes_raw.json"
    path.write_text(json.dumps(sample_raw_batch), encoding="utf-8")
    return path


# ── Anthropic mock ───────────────────────────────────────────────────────────

def make_anthropic_response(quotes: list[dict]) -> MagicMock:
    tool_block = MagicMock()
    tool_block.type = "tool_use"
    tool_block.input = {"quotes": quotes}

    response = MagicMock()
    response.content = [tool_block]
    return response
