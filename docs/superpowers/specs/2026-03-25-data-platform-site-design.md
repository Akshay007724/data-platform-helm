# Data Platform Helm — Site & Demo Design

**Date:** 2026-03-25
**Status:** Approved

---

## Overview

Build two deliverables:

1. **`docs/`** — A stunning project showcase site (GitHub Pages). Zero build tools. Pure HTML/CSS/JS served directly from the `docs/` folder on the `main` branch.
2. **Upgraded Document Processor UI** — Replace `data-platform/apps/document-processor/ui/index.html` with a production build of the demo page (mock mode off, real FastAPI backend).

---

## Visual Design System

**Aesthetic:** Data visualization / dashboard — dark navy, live-looking charts, monospace metrics.

| Token | Value | Usage |
|---|---|---|
| `--bg` | `#03070f` | Page background |
| `--surface` | `#060d1a` | Cards, sidebar |
| `--surface2` | `#0f1f34` | Nested elements |
| `--border` | `#1e3a5f` | Card borders |
| `--accent-cyan` | `#38bdf8` | Primary accent, links |
| `--accent-purple` | `#818cf8` | Secondary accent |
| `--accent-pink` | `#f472b6` | Highlight / streaming |
| `--accent-green` | `#4ade80` | Success / uptime |
| `--text` | `#e2e8f0` | Body text |
| `--muted` | `#475569` | Secondary text |
| `--radius` | `12px` | Default border radius |
| `--font-mono` | `'JetBrains Mono', monospace` | Metrics, code |

Typography: Inter (system-ui fallback). Monospace for metrics and code.

---

## File Structure

```
docs/
├── index.html              ← Landing page
├── demo.html               ← Document Processor demo
└── assets/
    ├── style.css           ← Shared CSS variables + components
    ├── particles.js        ← Canvas particle system (hero background)
    ├── landing.js          ← Landing page: scroll animations, metrics, architecture
    ├── demo.js             ← Demo UI: sidebar, search, ask, mock interception
    └── mock-data.js        ← Canned responses + SSE streaming simulation

data-platform/apps/document-processor/ui/
└── index.html              ← Upgraded production UI (DEMO_MODE=false)

.github/workflows/
└── pages.yml               ← GitHub Pages config (no build, source: docs/)
```

---

## Landing Page (`docs/index.html`)

Seven sections, single long scroll. Sticky nav bar.

### Nav
- Logo left: `DATA PLATFORM` in cyan monospace
- Links right: Features · Architecture · Demo · Quick Start · GitHub ↗
- Transparent on hero, solid `--surface` on scroll (Intersection Observer)

### Section 1 — Hero
- **Background:** Canvas particle system. 120 particles in `--accent-cyan/purple/pink/green`, connected by lines when within 100px. Slow drift animation.
- **Content (centered):**
  - Pill badge: `● Production-ready · Kubernetes-native` (pulsing dot)
  - H1: "The **Data Platform** you actually want to deploy" — gradient text on "Data Platform"
  - Subtitle: "Kafka streaming · Flink processing · Airflow orchestration · AI document intelligence — all in one Helm chart."
  - CTAs: `⚡ Deploy in 60s` (primary gradient button) + `Try Live Demo →` (ghost) + `★ GitHub` (ghost)
- **Live metrics strip** (below CTAs, glassmorphism card):
  - Events/sec — animates ±200 every 1.2s
  - Stream latency — random 0.1–0.5ms
  - Uptime SLA — static 99.9%
  - Docs indexed — increments slowly

### Section 2 — Features
- H2: "Everything in one chart"
- 4-column grid (responsive → 2col → 1col):
  - ⚡ Kafka — bitnami/kafka 32.4.3, 3-broker, 10Gi
  - 🌊 Flink — operator + session cluster, RocksDB + S3
  - 🔁 Airflow — KubernetesExecutor, PostgreSQL, DAG sync ready
  - 🧠 Document Processor — hybrid search, RAG Q&A, fully local
- Cards: `--surface` background, `--border` border, hover lifts + cyan border

### Section 3 — Architecture
- H2: "How it fits together"
- Interactive SVG diagram showing:
  - Browser UI → FastAPI → SQLite / ChromaDB / Ollama
  - Kafka → Flink → Data Processor → Data Ingestion
  - Airflow orchestrating the pipeline
- Click any component → highlight it + show a tooltip with role description
- Animated dashed lines showing data flow direction

### Section 4 — Document Processor Preview
- H2: "AI document intelligence, fully local"
- Embedded mini-version of the demo via iframe pointing to `demo.html?preview=1` (preview mode hides the nav bar and sidebar, shows only the search/ask panel)
- Bullet list of capabilities: multi-format ingestion, hybrid search, RAG Q&A, image understanding, no external APIs
- CTA: `Open full demo →`

### Section 5 — Quick Start
- H2: "Up and running in 60 seconds"
- Two tabs: `Docker Compose` | `Helm`
- Code blocks with syntax highlighting (Prism.js or hand-rolled) and copy button
- Docker tab shows the 3-command quickstart from the README
- Helm tab shows `helm install` command with namespace flag

### Section 6 — Pipeline Flow
- H2: "The data pipeline"
- Horizontal animated flow diagram: `Ingest → Kafka → Flink → Process → Query`
- Each node pulses; animated arrows between them
- Below each node: brief description + tech badge

### Section 7 — Footer
- Left: Logo + tagline
- Center: Links (GitHub, Docs, License)
- Right: Badges — Helm version, License: MIT, Kubernetes 1.30+
- Bottom line: "Built with Helm · Runs on Kubernetes"

---

## Document Processor Demo (`docs/demo.html` + production `ui/index.html`)

Full-screen two-panel layout. Same HTML file, `DEMO_MODE` flag controls mock vs real API.

### Mock Mode Detection
```js
const DEMO_MODE = window.DEMO_MODE ||
  window.location.hostname.includes('github.io') ||
  new URLSearchParams(window.location.search).has('mock');
```
In `docs/demo.html`: `<script>window.DEMO_MODE = true</script>` before main script.
In `ui/index.html`: no flag set → real API.

### Layout
```
┌─────────────────────────────────────────────────────┐
│  NAV: ← Back to site (demo only)   Document Processor│
├───────────────┬─────────────────────────────────────┤
│               │                                     │
│   SIDEBAR     │         MAIN PANEL                  │
│   280px       │         [Search] [Ask]  tabs        │
│               │                                     │
│  Upload zone  │  (search results / answer stream)   │
│               │                                     │
│  Documents    │                                     │
│  list         │                                     │
│               │                                     │
└───────────────┴─────────────────────────────────────┘
```

### Sidebar
- **Upload zone:** Drag-drop area. In demo mode: shows "Demo mode — uploads disabled" toast. In production: full upload with progress.
- **Document list:** Cards showing filename, file type icon (🗎 PDF / 📊 Excel / 📝 Word), status badge (ready/processing/error), chunk count, date.
- **Refresh button** (production only)

### Search Tab
- Input + Search button (Enter key triggers)
- Results: score bar (0–100%), filename + page, highlighted snippet (matched terms bolded), result type badge (text/image)
- Empty state: "No results — try a different query"

### Ask Tab
- Question input + Ask button
- Streaming answer box: tokens appear one by one with cursor blink effect
- `<think>` blocks rendered in muted italic (DeepSeek-R1 compat)
- Source cards below answer: filename, page, score, snippet
- Error state: red border + message

### Mock Data (`assets/mock-data.js`)

**Pre-loaded documents:**
```js
[
  { id: 'd1', filename: 'financial-report-2024.pdf', file_type: 'pdf', status: 'ready', chunk_count: 142, created_at: '2024-11-15' },
  { id: 'd2', filename: 'product-specification.docx', file_type: 'docx', status: 'ready', chunk_count: 87, created_at: '2024-12-03' },
  { id: 'd3', filename: 'sales-data-q4.xlsx', file_type: 'xlsx', status: 'ready', chunk_count: 34, created_at: '2025-01-08' },
  { id: 'd4', filename: 'architecture-overview.pdf', file_type: 'pdf', status: 'ready', chunk_count: 56, created_at: '2025-02-20' },
]
```

**Mock search:** Returns 4–6 results with realistic scores, snippets, page numbers. Slight random delay (200–500ms) to feel real.

**Mock ask:** SSE simulation — dispatches `sources` event immediately, then streams answer tokens word-by-word at ~40ms intervals using `setInterval`. Answer text is a realistic multi-sentence response referencing the mock documents.

---

## GitHub Pages Workflow (`.github/workflows/pages.yml`)

```yaml
name: Deploy to GitHub Pages
on:
  push:
    branches: [main]
  workflow_dispatch:

permissions:
  contents: read
  pages: write
  id-token: write

jobs:
  deploy:
    runs-on: ubuntu-latest
    environment:
      name: github-pages
      url: ${{ steps.deployment.outputs.page_url }}
    steps:
      - uses: actions/checkout@v4
      - uses: actions/configure-pages@v4
      - uses: actions/upload-pages-artifact@v3
        with:
          path: docs/
      - id: deployment
        uses: actions/deploy-pages@v4
```

No build step. GitHub Pages serves `docs/` directly.

---

## Error Handling

- **Upload errors** (production): toast with error message, card shows error badge
- **Search empty:** friendly empty state with suggestion
- **Ask SSE error:** `{"type":"error"}` event → red answer box
- **Network failure:** catch block → toast "Connection error"
- **Mock mode:** upload attempts show a non-destructive info toast

---

## Testing Approach

No automated test suite (pure static files). Manual verification checklist:
- [ ] Landing page loads and particle animation runs
- [ ] All 7 sections visible on scroll
- [ ] Architecture SVG click interactions work
- [ ] Quick Start copy buttons work
- [ ] Demo page loads in mock mode (open `demo.html` directly)
- [ ] Search returns mock results
- [ ] Ask streams mock answer token by token
- [ ] Production `ui/index.html` connects to real FastAPI (manual Docker test)
- [ ] GitHub Pages deploys and loads at correct URL
