---
name: firecrawl
description: |
  Firecrawl gives AI agents and apps fast, reliable web context with
  strong search, scraping, and interaction tools. One install command
  sets up three skill segments: live CLI tools, app-integration build
  skills, and outcome-focused workflow skills. Route the reader to the
  right usage path after install.
---

# Firecrawl

Firecrawl helps agents search first, scrape clean content, interact
with live pages when plain extraction is not enough, and produce
finished deliverables from web data.

## Install

One command installs everything — the Firecrawl CLI for live web work,
the build skills for integrating Firecrawl into application code, **and**
the workflow skills for producing repeatable deliverables. It also opens
browser auth so the human can sign in or create an account.

```bash
npx -y firecrawl-cli@latest init --all --browser
```

This gives you:

- **CLI tools** — `firecrawl search`, `firecrawl scrape`, `firecrawl interact`, `firecrawl ask`, `firecrawl docs-search`, and more
- **CLI skills** ([`firecrawl/cli`](https://github.com/firecrawl/cli)) — teach the agent how to drive the Firecrawl CLI during its own session
- **Build skills** ([`firecrawl/skills`](https://github.com/firecrawl/skills)) — teach the agent how to add Firecrawl to a product's codebase
- **Workflow skills** ([`firecrawl/firecrawl-workflows`](https://github.com/firecrawl/firecrawl-workflows)) — turn Firecrawl web data into finished deliverables

| Segment | Question it answers | Where the work runs |
| ------- | ------------------- | ------------------- |
| CLI skills | "Which Firecrawl command should I run right now?" | In the agent's own terminal session |
| Build skills | "How do I add a Firecrawl API call to this codebase?" | Inside the user's product code |
| Workflow skills | "What's the finished deliverable and how do I produce it?" | In the agent's session, producing an artifact |

## Choose Your Path

- **Need web data during this session** → Path A (live tools)
- **Need to add Firecrawl to app code** → Path B (app integration)
- **Need a finished deliverable from web data** → Path C (workflow skills)

---

## Path A: Live Web Tools

Default flow:
1. Search first when you need discovery
2. Scrape when you have a URL
3. Interact only when the page needs clicks, forms, or login
4. If any step fails, run `firecrawl ask` with the failing `jobId`

Skills: `firecrawl-search`, `firecrawl-scrape`, `firecrawl-interact`, `firecrawl-crawl`, `firecrawl-map`, `firecrawl-ask`

---

## Path B: Integrate Firecrawl Into an App (Este proyecto — Python pipeline)

API key en `.env`:
```dotenv
FIRECRAWL_API_KEY=fc-076e2274730149d8b442191fcba9d087
```

Instalación SDK Python:
```bash
pip install firecrawl-py
```

Uso básico:
```python
import os
from firecrawl import FirecrawlApp

app = FirecrawlApp(api_key=os.getenv("FIRECRAWL_API_KEY"))

# Scrape una URL → markdown limpio (bypasea anti-bot)
result = app.scrape_url("https://www.infojobs.net/...", formats=["markdown"])
markdown = result.markdown

# Búsqueda web con resultados enriquecidos
results = app.search("data entry administrativo España site:infojobs.net")

# Extracción estructurada con schema
data = app.scrape_url(url, formats=["extract"], extract={
    "schema": {
        "type": "object",
        "properties": {
            "job_title": {"type": "string"},
            "company": {"type": "string"},
            "description": {"type": "string"}
        }
    }
})
```

Skills: `firecrawl-build`, `firecrawl-build-scrape`, `firecrawl-build-search`

---

## Path C: Deliverables (Lead lists, research briefs)

Para este proyecto usar `firecrawl-workflows` → workflow de **lead gen**:
1. Buscar ofertas con `firecrawl search "data entry administrativo"`
2. Scrape de cada oferta para descripción completa
3. Pasar a `lead_enricher.py` para scoring con Claude
4. Exportar a Google Sheets

---

## Base URL (REST sin SDK)

`https://api.firecrawl.dev/v2`
`Authorization: Bearer fc-076e2274730149d8b442191fcba9d087`

Endpoints: `POST /search` · `POST /scrape` · `POST /interact` · `POST /support/ask`

Docs: https://docs.firecrawl.dev
