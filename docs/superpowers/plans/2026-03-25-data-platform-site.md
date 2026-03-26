# Data Platform Site & Demo Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a GitHub Pages showcase site (`docs/`) and overhaul the Document Processor UI — pure HTML/CSS/JS, no build tools.

**Architecture:** Two static HTML pages share a CSS design system and JS modules. `demo.html` uses a `DEMO_MODE` flag to switch between mock data (GitHub Pages) and real FastAPI calls (production). The existing `ui/index.html` is replaced by a copy of `demo.html` with mock mode off.

**Tech Stack:** Vanilla JS (ES modules), CSS custom properties, Canvas API, Intersection Observer, EventSource/SSE simulation.

---

## File Map

| File | Responsibility |
|---|---|
| `docs/assets/style.css` | Design tokens, shared component styles |
| `docs/assets/particles.js` | Canvas particle system (hero background) |
| `docs/assets/mock-data.js` | Canned API responses + SSE stream simulator |
| `docs/assets/landing.js` | Scroll animations, live metrics, architecture SVG |
| `docs/assets/demo.js` | Demo UI logic: sidebar, search tab, ask tab, API calls |
| `docs/index.html` | Landing page (7 sections) |
| `docs/demo.html` | Document Processor demo (DEMO_MODE=true) |
| `data-platform/apps/document-processor/ui/index.html` | Production UI (DEMO_MODE unset — real API) |
| `.github/workflows/pages.yml` | GitHub Pages deploy workflow |

---

### Task 1: Design system — `docs/assets/style.css`

**Files:**
- Create: `docs/assets/style.css`

- [ ] Create `docs/assets/style.css`:

```css
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

:root {
  --bg:           #03070f;
  --surface:      #060d1a;
  --surface2:     #0f1f34;
  --border:       #1e3a5f;
  --cyan:         #38bdf8;
  --purple:       #818cf8;
  --pink:         #f472b6;
  --green:        #4ade80;
  --text:         #e2e8f0;
  --muted:        #475569;
  --radius:       12px;
  --font-mono:    'JetBrains Mono', 'Fira Code', monospace;
}

body { background: var(--bg); color: var(--text); font-family: Inter, system-ui, sans-serif; line-height: 1.6; }

.grad { background: linear-gradient(90deg, var(--cyan), var(--purple), var(--pink)); -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text; }

.btn { display: inline-flex; align-items: center; gap: 8px; padding: 11px 24px; border-radius: 8px; font-size: 0.9rem; font-weight: 600; cursor: pointer; border: none; transition: transform 0.15s, opacity 0.15s; text-decoration: none; }
.btn-primary { background: linear-gradient(135deg, var(--cyan), var(--purple)); color: #fff; }
.btn-primary:hover { transform: translateY(-1px); opacity: 0.9; }
.btn-ghost { background: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.12); color: var(--muted); }
.btn-ghost:hover { border-color: rgba(56,189,248,0.4); color: var(--text); }

.card { background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius); padding: 24px; transition: border-color 0.2s, transform 0.2s; }
.card:hover { border-color: var(--cyan); transform: translateY(-2px); }

.badge { display: inline-flex; align-items: center; gap: 6px; background: rgba(56,189,248,0.08); border: 1px solid rgba(56,189,248,0.2); border-radius: 999px; padding: 5px 14px; font-size: 0.78rem; color: var(--cyan); letter-spacing: 0.04em; }
.badge .pulse { width: 6px; height: 6px; background: var(--cyan); border-radius: 50%; animation: pulse 2s infinite; }
@keyframes pulse { 0%,100%{opacity:1;transform:scale(1)} 50%{opacity:0.4;transform:scale(0.7)} }

.status { display: inline-flex; align-items: center; gap: 5px; padding: 2px 10px; border-radius: 999px; font-size: 0.7rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.06em; }
.status-ready      { background: rgba(74,222,128,0.1);  color: var(--green); }
.status-processing { background: rgba(251,191,36,0.1);  color: #fbbf24; }
.status-error      { background: rgba(248,113,113,0.1); color: #f87171; }

.section { max-width: 1100px; margin: 0 auto; padding: 80px 24px; }
.section-title { font-size: clamp(1.6rem,3vw,2.2rem); font-weight: 800; letter-spacing: -0.02em; text-align: center; margin-bottom: 12px; }
.section-sub { text-align: center; color: var(--muted); font-size: 1rem; margin-bottom: 48px; }

.nav { position: fixed; top: 0; left: 0; right: 0; z-index: 100; padding: 0 24px; height: 60px; display: flex; align-items: center; justify-content: space-between; transition: background 0.3s, border-bottom 0.3s; }
.nav.scrolled { background: var(--surface); border-bottom: 1px solid var(--border); }
.nav-logo { font-family: var(--font-mono); font-size: 0.9rem; font-weight: 700; color: var(--cyan); letter-spacing: 0.06em; text-decoration: none; }
.nav-links { display: flex; gap: 24px; align-items: center; }
.nav-links a { color: var(--muted); text-decoration: none; font-size: 0.88rem; transition: color 0.15s; }
.nav-links a:hover { color: var(--text); }

.code-block { background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius); padding: 20px; font-family: var(--font-mono); font-size: 0.82rem; color: var(--cyan); overflow-x: auto; position: relative; white-space: pre; }
.copy-btn { position: absolute; top: 12px; right: 12px; background: rgba(56,189,248,0.1); border: 1px solid rgba(56,189,248,0.2); color: var(--cyan); border-radius: 6px; padding: 4px 12px; font-size: 0.72rem; cursor: pointer; }
.copy-btn:hover { background: rgba(56,189,248,0.2); }

.reveal { opacity: 0; transform: translateY(24px); transition: opacity 0.6s ease, transform 0.6s ease; }
.reveal.visible { opacity: 1; transform: none; }

.toast-wrap { position: fixed; bottom: 24px; right: 24px; display: flex; flex-direction: column; gap: 8px; z-index: 999; pointer-events: none; }
.toast { background: var(--surface2); border: 1px solid var(--border); border-radius: 8px; padding: 10px 18px; font-size: 0.84rem; animation: slideup 0.2s ease; }
@keyframes slideup { from { transform: translateY(10px); opacity: 0; } }
```

- [ ] Commit:
```bash
cd /Users/ad6/Desktop/Projects/data-platform-helm
git add docs/assets/style.css
git commit -m "feat: add shared design system CSS"
```

---

### Task 2: Particle system — `docs/assets/particles.js`

**Files:**
- Create: `docs/assets/particles.js`

- [ ] Create `docs/assets/particles.js`:

```js
export function initParticles(canvasId) {
  const canvas = document.getElementById(canvasId);
  const ctx = canvas.getContext('2d');
  const COLORS = ['#38bdf8','#818cf8','#f472b6','#4ade80'];
  let W, H, particles = [];

  function resize() {
    W = canvas.width = canvas.offsetWidth;
    H = canvas.height = canvas.offsetHeight;
  }

  class Particle {
    reset() {
      this.x = Math.random() * W;
      this.y = Math.random() * H;
      this.size = Math.random() * 1.5 + 0.4;
      this.vx = (Math.random() - 0.5) * 0.35;
      this.vy = (Math.random() - 0.5) * 0.35;
      this.opacity = Math.random() * 0.5 + 0.1;
      this.color = COLORS[Math.floor(Math.random() * COLORS.length)];
    }
    constructor() { this.reset(); }
    update() {
      this.x += this.vx; this.y += this.vy;
      if (this.x < 0 || this.x > W || this.y < 0 || this.y > H) this.reset();
    }
    draw() {
      ctx.save(); ctx.globalAlpha = this.opacity; ctx.fillStyle = this.color;
      ctx.beginPath(); ctx.arc(this.x, this.y, this.size, 0, Math.PI * 2); ctx.fill();
      ctx.restore();
    }
  }

  function drawConnections() {
    for (let i = 0; i < particles.length; i++) {
      for (let j = i + 1; j < particles.length; j++) {
        const dx = particles[i].x - particles[j].x;
        const dy = particles[i].y - particles[j].y;
        const d = Math.sqrt(dx * dx + dy * dy);
        if (d < 100) {
          ctx.save(); ctx.globalAlpha = (1 - d / 100) * 0.07;
          ctx.strokeStyle = '#38bdf8'; ctx.lineWidth = 0.5;
          ctx.beginPath();
          ctx.moveTo(particles[i].x, particles[i].y);
          ctx.lineTo(particles[j].x, particles[j].y);
          ctx.stroke(); ctx.restore();
        }
      }
    }
  }

  resize();
  window.addEventListener('resize', resize);
  for (let i = 0; i < 120; i++) particles.push(new Particle());

  (function loop() {
    ctx.clearRect(0, 0, W, H);
    particles.forEach(p => { p.update(); p.draw(); });
    drawConnections();
    requestAnimationFrame(loop);
  })();
}
```

- [ ] Commit:
```bash
git add docs/assets/particles.js
git commit -m "feat: add canvas particle system"
```

---

### Task 3: Mock data — `docs/assets/mock-data.js`

**Files:**
- Create: `docs/assets/mock-data.js`

- [ ] Create `docs/assets/mock-data.js`:

```js
export const MOCK_DOCS = [
  { id:'d1', filename:'financial-report-2024.pdf',  file_type:'pdf',  status:'ready', chunk_count:142, created_at:'2024-11-15T10:00:00Z' },
  { id:'d2', filename:'product-specification.docx', file_type:'docx', status:'ready', chunk_count:87,  created_at:'2024-12-03T14:30:00Z' },
  { id:'d3', filename:'sales-data-q4.xlsx',         file_type:'xlsx', status:'ready', chunk_count:34,  created_at:'2025-01-08T09:15:00Z' },
  { id:'d4', filename:'architecture-overview.pdf',  file_type:'pdf',  status:'ready', chunk_count:56,  created_at:'2025-02-20T16:45:00Z' },
];

export const MOCK_SEARCH_RESULTS = [
  { doc_id:'d1', filename:'financial-report-2024.pdf',  page:12,   score:0.94, content:'Revenue grew 23% YoY to $4.2B, driven by strong performance in the cloud segment and new enterprise contracts signed in Q3.', result_type:'text' },
  { doc_id:'d4', filename:'architecture-overview.pdf',  page:3,    score:0.87, content:'The data pipeline processes approximately 12,000 events per second at peak load, with end-to-end latency below 400ms using Flink stateful stream processing.', result_type:'text' },
  { doc_id:'d2', filename:'product-specification.docx', page:7,    score:0.81, content:'Authentication is handled via OAuth 2.0 with JWT tokens. All endpoints require a valid Bearer token. Token expiry is set to 24 hours by default.', result_type:'text' },
  { doc_id:'d3', filename:'sales-data-q4.xlsx',         page:null, score:0.74, content:'Q4 total sales: $1.84B. Top regions: North America (42%), Europe (31%), APAC (19%). Highest growth segment: SMB (+38% QoQ).', result_type:'text' },
];

const MOCK_SOURCES = [
  { doc_id:'d1', filename:'financial-report-2024.pdf', page:12, score:0.94, snippet:'Revenue grew 23% YoY to $4.2B, driven by strong performance in the cloud segment...' },
  { doc_id:'d4', filename:'architecture-overview.pdf', page:3,  score:0.87, snippet:'The data pipeline processes approximately 12,000 events per second at peak load...' },
];

const MOCK_ANSWER = `Based on the documents, revenue grew 23% year-over-year to $4.2 billion, primarily driven by the cloud segment and new enterprise contracts. The data platform architecture supporting this growth handles approximately 12,000 events per second with sub-400ms end-to-end latency using Apache Flink. Q4 sales reached $1.84B with North America as the largest region at 42% of total revenue.`;

export function installMockFetch() {
  const delay = ms => new Promise(r => setTimeout(r, ms));

  window.fetch = async (url, opts = {}) => {
    const path = typeof url === 'string' ? url : url.url;
    await delay(200 + Math.random() * 300);

    if (path.includes('/documents/upload')) {
      return jsonResp({ message: 'Demo mode — uploads are disabled.', uploaded: [] });
    }
    if (path.match(/\/documents\/[^/]+$/) && (!opts.method || opts.method === 'GET')) {
      const id = path.split('/').pop();
      return jsonResp(MOCK_DOCS.find(d => d.id === id) ?? MOCK_DOCS[0]);
    }
    if (path.includes('/documents') && (!opts.method || opts.method === 'GET')) {
      return jsonResp({ documents: MOCK_DOCS });
    }
    if (path.includes('/search')) {
      const body = JSON.parse(opts.body || '{}');
      return jsonResp({ results: body.query ? MOCK_SEARCH_RESULTS : [] });
    }
    if (path.includes('/ask')) {
      return sseResp(MOCK_SOURCES, MOCK_ANSWER);
    }
    return jsonResp({ status: 'ok' });
  };
}

function jsonResp(data) {
  return { ok: true, status: 200, json: async () => data, body: null };
}

function sseResp(sources, answer) {
  const enc = new TextEncoder();
  const words = answer.split(' ');
  let i = 0;
  const stream = new ReadableStream({
    start(ctrl) {
      ctrl.enqueue(enc.encode(`data: ${JSON.stringify({ type:'sources', data: sources })}\n\n`));
      const iv = setInterval(() => {
        if (i >= words.length) {
          ctrl.enqueue(enc.encode(`data: ${JSON.stringify({ type:'done' })}\n\n`));
          ctrl.close(); clearInterval(iv); return;
        }
        const token = (i === 0 ? '' : ' ') + words[i++];
        ctrl.enqueue(enc.encode(`data: ${JSON.stringify({ type:'token', data: token })}\n\n`));
      }, 45);
    }
  });
  return { ok: true, status: 200, body: stream, json: async () => ({}) };
}
```

- [ ] Commit:
```bash
git add docs/assets/mock-data.js
git commit -m "feat: add mock data layer and SSE simulator"
```

---

### Task 4: Landing page — `docs/index.html`

**Files:**
- Create: `docs/index.html`

- [ ] Create `docs/index.html` with all 7 sections. Note: all dynamic content is set via `textContent` or DOM methods in `landing.js` — no user input is ever passed to `innerHTML`. Static HTML strings in the template below are safe hardcoded content:

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8"/>
  <meta name="viewport" content="width=device-width,initial-scale=1"/>
  <title>Data Platform Helm — Kafka · Flink · Airflow on Kubernetes</title>
  <meta name="description" content="Production-ready Helm chart for Kafka, Flink, Airflow and AI document intelligence on Kubernetes."/>
  <link rel="stylesheet" href="assets/style.css"/>
  <style>
    /* Hero */
    .hero { position:relative; min-height:100vh; display:flex; align-items:center; justify-content:center; overflow:hidden; }
    #hero-canvas { position:absolute; inset:0; width:100%; height:100%; }
    .hero-content { position:relative; z-index:2; text-align:center; max-width:820px; padding:40px 24px; }
    .hero h1 { font-size:clamp(2.4rem,6vw,4rem); font-weight:800; line-height:1.1; letter-spacing:-0.03em; margin:20px 0; }
    .hero-sub { font-size:1.1rem; color:var(--muted); max-width:560px; margin:0 auto 36px; }
    .ctas { display:flex; gap:12px; justify-content:center; flex-wrap:wrap; margin-bottom:56px; }
    /* Metrics */
    .metrics { display:flex; border:1px solid rgba(56,189,248,0.12); border-radius:var(--radius); overflow:hidden; background:rgba(6,13,26,0.85); backdrop-filter:blur(12px); }
    .metric { flex:1; padding:16px; text-align:center; border-right:1px solid rgba(56,189,248,0.1); }
    .metric:last-child { border-right:none; }
    .metric-val { font-size:1.5rem; font-weight:700; font-family:var(--font-mono); color:var(--cyan); }
    .metric-val.pink { color:var(--pink); }
    .metric-val.green { color:var(--green); }
    .metric-label { font-size:0.65rem; color:var(--muted); text-transform:uppercase; letter-spacing:0.08em; margin-top:4px; }
    /* Features */
    .features-grid { display:grid; grid-template-columns:repeat(auto-fit,minmax(220px,1fr)); gap:16px; }
    .feature-icon { font-size:1.8rem; margin-bottom:12px; }
    .feature-tag { display:inline-block; background:rgba(56,189,248,0.08); border:1px solid rgba(56,189,248,0.2); color:var(--cyan); font-size:0.65rem; padding:2px 8px; border-radius:4px; margin-top:10px; font-family:var(--font-mono); }
    .feature-tag.pink   { background:rgba(244,114,182,0.08); border-color:rgba(244,114,182,0.2); color:var(--pink); }
    .feature-tag.green  { background:rgba(74,222,128,0.08);  border-color:rgba(74,222,128,0.2);  color:var(--green); }
    .feature-tag.purple { background:rgba(129,140,248,0.08); border-color:rgba(129,140,248,0.2); color:var(--purple); }
    /* Architecture */
    #arch-svg { width:100%; max-width:800px; display:block; margin:0 auto; cursor:default; }
    .arch-tooltip { background:var(--surface2); border:1px solid var(--border); border-radius:8px; padding:10px 14px; font-size:0.82rem; max-width:240px; position:absolute; pointer-events:none; display:none; z-index:10; line-height:1.5; }
    /* Tabs */
    .tabs { display:flex; gap:2px; margin-bottom:0; }
    .tab { padding:8px 18px; border-radius:6px 6px 0 0; font-size:0.85rem; cursor:pointer; background:var(--surface); color:var(--muted); border:1px solid var(--border); border-bottom:none; }
    .tab.active { background:var(--surface2); color:var(--cyan); border-color:var(--cyan); }
    .tab-panel { display:none; }
    .tab-panel.active { display:block; }
    /* Pipeline */
    .pipeline { display:flex; align-items:center; justify-content:center; gap:0; flex-wrap:wrap; margin-top:40px; }
    .pipe-node { background:var(--surface); border:1px solid var(--border); border-radius:var(--radius); padding:20px 16px; text-align:center; min-width:120px; }
    .pipe-node h4 { font-size:0.88rem; margin-bottom:6px; }
    .pipe-node p { font-size:0.72rem; color:var(--muted); }
    .pipe-arrow { color:var(--cyan); font-size:1.4rem; padding:0 8px; }
    /* Demo embed */
    .demo-embed { border:1px solid var(--border); border-radius:var(--radius); overflow:hidden; height:500px; }
    .demo-embed iframe { width:100%; height:100%; border:none; }
    /* Footer */
    footer { border-top:1px solid var(--border); padding:40px 24px; max-width:1100px; margin:0 auto; display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:20px; }
    footer .logo { font-family:var(--font-mono); color:var(--cyan); font-weight:700; }
    footer p { color:var(--muted); font-size:0.82rem; }
    footer .links { display:flex; gap:20px; }
    footer .links a { color:var(--muted); text-decoration:none; font-size:0.85rem; }
    footer .links a:hover { color:var(--cyan); }
  </style>
</head>
<body>

<nav class="nav" id="nav">
  <a class="nav-logo" href="#">DATA PLATFORM</a>
  <div class="nav-links">
    <a href="#features">Features</a>
    <a href="#architecture">Architecture</a>
    <a href="#demo">Demo</a>
    <a href="#quickstart">Quick Start</a>
    <a class="btn btn-ghost" style="padding:6px 14px;font-size:0.82rem" href="https://github.com/REPLACE_ME" target="_blank" rel="noopener">★ GitHub</a>
  </div>
</nav>

<!-- HERO -->
<section class="hero" id="hero">
  <canvas id="hero-canvas"></canvas>
  <div class="hero-content">
    <div class="badge"><span class="pulse"></span>Production-ready · Kubernetes-native</div>
    <h1>The <span class="grad">Data Platform</span><br>you actually want to deploy</h1>
    <p class="hero-sub">Kafka streaming · Flink processing · Airflow orchestration · AI document intelligence — all in one Helm chart.</p>
    <div class="ctas">
      <a class="btn btn-primary" href="#quickstart">&#9889; Deploy in 60s</a>
      <a class="btn btn-ghost" href="demo.html">Try Live Demo &#8594;</a>
      <a class="btn btn-ghost" href="https://github.com/REPLACE_ME" target="_blank" rel="noopener">&#9733; GitHub</a>
    </div>
    <div class="metrics">
      <div class="metric"><div class="metric-val" id="m-events">12,483</div><div class="metric-label">Events / sec</div></div>
      <div class="metric"><div class="metric-val pink" id="m-lat">0.3ms</div><div class="metric-label">Stream latency</div></div>
      <div class="metric"><div class="metric-val green">99.9%</div><div class="metric-label">Uptime SLA</div></div>
      <div class="metric"><div class="metric-val" id="m-docs">2,847</div><div class="metric-label">Docs indexed</div></div>
    </div>
  </div>
</section>

<!-- FEATURES -->
<section class="section reveal" id="features">
  <h2 class="section-title">Everything in one chart</h2>
  <p class="section-sub">Install once. Scale independently. Each component is optional and production-hardened.</p>
  <div class="features-grid">
    <div class="card">
      <div class="feature-icon">&#9889;</div>
      <h3>Apache Kafka</h3>
      <p style="color:var(--muted);font-size:0.85rem;margin-top:8px">3-broker cluster, 10Gi persistence, PLAINTEXT listeners, Bitnami-managed.</p>
      <span class="feature-tag">bitnami/kafka 32.4.3</span>
    </div>
    <div class="card">
      <div class="feature-icon">&#127754;</div>
      <h3>Apache Flink</h3>
      <p style="color:var(--muted);font-size:0.85rem;margin-top:8px">Kubernetes Operator + session cluster, 2 TaskManagers, RocksDB + S3 checkpointing.</p>
      <span class="feature-tag pink">flink-operator 1.9.0</span>
    </div>
    <div class="card">
      <div class="feature-icon">&#128260;</div>
      <h3>Apache Airflow</h3>
      <p style="color:var(--muted);font-size:0.85rem;margin-top:8px">KubernetesExecutor, PostgreSQL backend, DAG sync ready, no scheduler contention.</p>
      <span class="feature-tag green">airflow 1.19.0</span>
    </div>
    <div class="card">
      <div class="feature-icon">&#129504;</div>
      <h3>Document Processor</h3>
      <p style="color:var(--muted);font-size:0.85rem;margin-top:8px">PDF/DOCX/XLSX ingestion, hybrid BM25 + vector search, local LLM Q&amp;A via Ollama.</p>
      <span class="feature-tag purple">RAG · Fully local</span>
    </div>
  </div>
</section>

<!-- ARCHITECTURE -->
<section class="section reveal" id="architecture" style="position:relative">
  <h2 class="section-title">How it fits together</h2>
  <p class="section-sub">Hover any component to learn its role in the stack.</p>
  <svg id="arch-svg" viewBox="0 0 800 340" xmlns="http://www.w3.org/2000/svg"></svg>
  <div class="arch-tooltip" id="arch-tooltip"></div>
</section>

<!-- DEMO PREVIEW -->
<section class="section reveal" id="demo">
  <h2 class="section-title">AI document intelligence, fully local</h2>
  <p class="section-sub">Upload PDFs, Word docs, and spreadsheets. Search semantically. Ask questions answered by an on-device LLM.</p>
  <div class="demo-embed">
    <iframe src="demo.html?preview=1" title="Document Processor Demo" loading="lazy"></iframe>
  </div>
  <div style="text-align:center;margin-top:20px">
    <a class="btn btn-primary" href="demo.html">Open full demo &#8594;</a>
  </div>
</section>

<!-- QUICK START -->
<section class="section reveal" id="quickstart">
  <h2 class="section-title">Up and running in 60 seconds</h2>
  <p class="section-sub">Choose your deployment method.</p>
  <div class="tabs">
    <div class="tab active" data-tab="docker">Docker Compose</div>
    <div class="tab" data-tab="helm">Helm</div>
  </div>
  <div class="tab-panel active" id="tab-docker">
    <div class="code-block"><button class="copy-btn" data-copy="docker">Copy</button><span style="color:var(--muted)"># 1. Enter the app directory</span>
cd data-platform/apps/document-processor

<span style="color:var(--muted)"># 2. Copy environment config</span>
cp .env.example .env

<span style="color:var(--muted)"># 3. Build and start</span>
docker compose up --build

<span style="color:var(--green)"># Open http://localhost:8000 once you see "All services ready"</span></div>
  </div>
  <div class="tab-panel" id="tab-helm">
    <div class="code-block"><button class="copy-btn" data-copy="helm">Copy</button><span style="color:var(--muted)"># Add chart dependencies</span>
helm dependency update data-platform/

<span style="color:var(--muted)"># Install to Kubernetes</span>
helm install data-platform data-platform/ \
  --namespace data-engineering \
  --create-namespace

<span style="color:var(--green)"># Verify rollout</span>
kubectl get pods -n data-engineering</div>
  </div>
</section>

<!-- PIPELINE FLOW -->
<section class="section reveal" id="pipeline">
  <h2 class="section-title">The data pipeline</h2>
  <p class="section-sub">From raw events to queryable intelligence.</p>
  <div class="pipeline">
    <div class="pipe-node"><div style="font-size:1.4rem">&#128229;</div><h4>Ingest</h4><p>HTTP / file upload</p></div>
    <div class="pipe-arrow">&#8594;</div>
    <div class="pipe-node"><div style="font-size:1.4rem">&#9889;</div><h4>Kafka</h4><p>Event streaming</p></div>
    <div class="pipe-arrow">&#8594;</div>
    <div class="pipe-node"><div style="font-size:1.4rem">&#127754;</div><h4>Flink</h4><p>Stream processing</p></div>
    <div class="pipe-arrow">&#8594;</div>
    <div class="pipe-node"><div style="font-size:1.4rem">&#129504;</div><h4>Embed</h4><p>Vector index</p></div>
    <div class="pipe-arrow">&#8594;</div>
    <div class="pipe-node"><div style="font-size:1.4rem">&#128269;</div><h4>Query</h4><p>Hybrid search + RAG</p></div>
  </div>
</section>

<!-- FOOTER -->
<footer>
  <div>
    <div class="logo">DATA PLATFORM HELM</div>
    <p style="margin-top:6px">Built with Helm · Runs on Kubernetes</p>
  </div>
  <div class="links">
    <a href="https://github.com/REPLACE_ME" target="_blank" rel="noopener">GitHub &#8599;</a>
    <a href="#quickstart">Deploy</a>
    <a href="demo.html">Demo</a>
  </div>
  <p>MIT License · Helm 3.14+ · Kubernetes 1.30+</p>
</footer>

<div class="toast-wrap" id="toasts"></div>

<script type="module" src="assets/particles.js"></script>
<script type="module" src="assets/landing.js"></script>
</body>
</html>
```

- [ ] Open in browser — HTML structure renders, no JS errors (logic wired in Task 5).
- [ ] Commit:
```bash
git add docs/index.html
git commit -m "feat: add landing page HTML"
```

---

### Task 5: Landing JS — `docs/assets/landing.js`

**Files:**
- Create: `docs/assets/landing.js`

All DOM content is set via `textContent` or SVG attribute methods — no user input reaches `innerHTML`.

- [ ] Create `docs/assets/landing.js`:

```js
import { initParticles } from './particles.js';

initParticles('hero-canvas');

// Sticky nav
const nav = document.getElementById('nav');
window.addEventListener('scroll', () => {
  nav.classList.toggle('scrolled', window.scrollY > 60);
}, { passive: true });

// Live metrics
let ev = 12483, docs = 2847;
setInterval(() => {
  ev = Math.max(10000, Math.min(15000, ev + Math.floor((Math.random() - 0.48) * 300)));
  docs += Math.floor(Math.random() * 2);
  document.getElementById('m-events').textContent = ev.toLocaleString();
  document.getElementById('m-docs').textContent = docs.toLocaleString();
  document.getElementById('m-lat').textContent = (Math.random() * 0.4 + 0.1).toFixed(1) + 'ms';
}, 1300);

// Scroll reveal
const obs = new IntersectionObserver(entries => {
  entries.forEach(e => { if (e.isIntersecting) e.target.classList.add('visible'); });
}, { threshold: 0.12 });
document.querySelectorAll('.reveal').forEach(el => obs.observe(el));

// Architecture SVG — built entirely via DOM API, no innerHTML
const ARCH_NODES = [
  { id:'browser', x:350, y:20,  w:100, h:36, label:'Browser UI',    color:'#38bdf8', desc:'Single-page UI: upload, search, ask. Served by FastAPI or GitHub Pages in demo mode.' },
  { id:'fastapi', x:310, y:100, w:180, h:36, label:'FastAPI :8000', color:'#818cf8', desc:'Async HTTP server. Routes: /upload, /documents, /search, /ask (SSE). Background task queue.' },
  { id:'sqlite',  x:80,  y:200, w:130, h:36, label:'SQLite',        color:'#4ade80', desc:'Two tables: documents (metadata) and chunks (raw text for BM25 corpus).' },
  { id:'chroma',  x:310, y:200, w:130, h:36, label:'ChromaDB :8001',color:'#f472b6', desc:'HNSW vector index for nomic-embed-text and CLIP embeddings. Cosine similarity search.' },
  { id:'ollama',  x:540, y:200, w:130, h:36, label:'Ollama :11434', color:'#fbbf24', desc:'Serves Qwen2.5:0.5b locally. Streams tokens over SSE. Zero external API calls.' },
  { id:'kafka',   x:80,  y:290, w:120, h:36, label:'Kafka',         color:'#38bdf8', desc:'3-broker cluster. 10Gi persistence. PLAINTEXT. Managed by the Bitnami chart.' },
  { id:'flink',   x:270, y:290, w:120, h:36, label:'Flink',         color:'#818cf8', desc:'Session cluster, 2 TaskManagers. RocksDB state backend with S3 checkpointing.' },
  { id:'airflow', x:460, y:290, w:120, h:36, label:'Airflow',       color:'#4ade80', desc:'KubernetesExecutor, PostgreSQL backend. Orchestrates pipeline DAGs.' },
];

const ARCH_EDGES = [
  ['browser','fastapi'],['fastapi','sqlite'],['fastapi','chroma'],['fastapi','ollama'],
  ['kafka','flink'],['flink','airflow'],
];

const NS = 'http://www.w3.org/2000/svg';
const svg = document.getElementById('arch-svg');
const tooltip = document.getElementById('arch-tooltip');

function svgEl(tag, attrs) {
  const el = document.createElementNS(NS, tag);
  Object.entries(attrs).forEach(([k, v]) => el.setAttribute(k, v));
  return el;
}

// Draw edges first (behind nodes)
ARCH_EDGES.forEach(([a, b]) => {
  const na = ARCH_NODES.find(n => n.id === a);
  const nb = ARCH_NODES.find(n => n.id === b);
  svg.appendChild(svgEl('line', {
    x1: na.x + na.w/2, y1: na.y + na.h/2,
    x2: nb.x + nb.w/2, y2: nb.y + nb.h/2,
    stroke: '#1e3a5f', 'stroke-width': '1.5', 'stroke-dasharray': '5,4',
  }));
});

// Draw nodes
ARCH_NODES.forEach(node => {
  const g = svgEl('g', {});
  g.style.cursor = 'pointer';

  const rect = svgEl('rect', { x:node.x, y:node.y, width:node.w, height:node.h, rx:'8', fill:'#060d1a', stroke:node.color, 'stroke-width':'1.5' });
  const text = svgEl('text', { x: node.x + node.w/2, y: node.y + node.h/2 + 5, 'text-anchor':'middle', fill:node.color, 'font-size':'11', 'font-family':'Inter,system-ui,sans-serif', 'font-weight':'500' });
  text.textContent = node.label;  // safe — hardcoded string, not user input

  g.appendChild(rect);
  g.appendChild(text);

  g.addEventListener('mouseenter', () => {
    rect.setAttribute('fill', node.color + '18');
    // Tooltip content set via textContent for the label, and a separate text node for desc
    tooltip.textContent = '';
    const strong = document.createElement('strong');
    strong.style.color = node.color;
    strong.textContent = node.label;
    tooltip.appendChild(strong);
    tooltip.appendChild(document.createElement('br'));
    tooltip.appendChild(document.createTextNode(node.desc));
    tooltip.style.display = 'block';
  });
  g.addEventListener('mousemove', e => {
    const svgRect = svg.getBoundingClientRect();
    tooltip.style.left = (e.clientX - svgRect.left + 14) + 'px';
    tooltip.style.top  = (e.clientY - svgRect.top - 10) + 'px';
  });
  g.addEventListener('mouseleave', () => {
    rect.setAttribute('fill', '#060d1a');
    tooltip.style.display = 'none';
  });

  svg.appendChild(g);
});

// Quick start tabs
document.querySelectorAll('.tab').forEach(tab => {
  tab.addEventListener('click', () => {
    document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
    document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
    tab.classList.add('active');
    document.getElementById('tab-' + tab.dataset.tab).classList.add('active');
  });
});

// Copy buttons — values are hardcoded strings, never user input
const CODE = {
  docker: `cd data-platform/apps/document-processor\ncp .env.example .env\ndocker compose up --build`,
  helm:   `helm dependency update data-platform/\nhelm install data-platform data-platform/ \\\n  --namespace data-engineering \\\n  --create-namespace\nkubectl get pods -n data-engineering`,
};
document.querySelectorAll('.copy-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    navigator.clipboard.writeText(CODE[btn.dataset.copy] || '');
    btn.textContent = 'Copied!';
    setTimeout(() => { btn.textContent = 'Copy'; }, 1800);
  });
});
```

- [ ] Open `docs/index.html` in browser. Verify:
  - Particles animate in hero canvas
  - Nav turns opaque on scroll
  - Metrics numbers animate every ~1.3s
  - Architecture SVG renders with nodes; hover shows tooltip (no innerHTML used)
  - Tab switching works; copy button copies the correct text
  - `.reveal` sections fade in on scroll
- [ ] Commit:
```bash
git add docs/assets/landing.js
git commit -m "feat: add landing page interactions, architecture SVG, and metrics"
```

---

### Task 6: Demo page — `docs/demo.html`

**Files:**
- Create: `docs/demo.html`

- [ ] Create `docs/demo.html`:

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8"/>
  <meta name="viewport" content="width=device-width,initial-scale=1"/>
  <title>Document Processor — Demo</title>
  <link rel="stylesheet" href="assets/style.css"/>
  <style>
    body { display:flex; flex-direction:column; height:100vh; overflow:hidden; }
    .demo-nav { height:52px; border-bottom:1px solid var(--border); display:flex; align-items:center; padding:0 20px; gap:14px; flex-shrink:0; background:var(--surface); }
    .demo-nav a { color:var(--muted); text-decoration:none; font-size:0.82rem; transition:color 0.15s; }
    .demo-nav a:hover { color:var(--cyan); }
    .demo-nav .title { font-weight:600; font-size:0.9rem; margin-left:auto; color:var(--text); }
    .demo-nav.hidden { display:none; }
    .demo-body { display:flex; flex:1; overflow:hidden; }
    /* Sidebar */
    .sidebar { width:280px; border-right:1px solid var(--border); display:flex; flex-direction:column; background:var(--surface); flex-shrink:0; }
    .sidebar.hidden { display:none; }
    .upload-zone { border:2px dashed var(--border); border-radius:var(--radius); margin:16px; padding:20px 12px; text-align:center; cursor:pointer; transition:border-color 0.2s,background 0.2s; }
    .upload-zone:hover,.upload-zone.drag-over { border-color:var(--cyan); background:rgba(56,189,248,0.04); }
    .upload-zone .uz-icon { font-size:1.8rem; }
    .upload-zone p { font-size:0.78rem; color:var(--muted); margin-top:6px; }
    .doc-list { flex:1; overflow-y:auto; padding:0 12px 12px; }
    .doc-item { background:var(--surface2); border:1px solid var(--border); border-radius:8px; padding:12px; margin-bottom:8px; }
    .doc-name { font-size:0.82rem; font-weight:500; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; color:var(--text); }
    .doc-meta { font-size:0.7rem; color:var(--muted); margin-top:5px; display:flex; justify-content:space-between; align-items:center; }
    .sidebar-footer { padding:12px; border-top:1px solid var(--border); }
    /* Main */
    .main { flex:1; display:flex; flex-direction:column; overflow:hidden; }
    .tab-bar { display:flex; gap:2px; padding:12px 20px 0; border-bottom:1px solid var(--border); flex-shrink:0; background:var(--bg); }
    .ptab { padding:8px 20px; border-radius:6px 6px 0 0; font-size:0.88rem; cursor:pointer; color:var(--muted); border:1px solid transparent; border-bottom:none; margin-bottom:-1px; transition:color 0.15s; }
    .ptab.active { color:var(--cyan); border-color:var(--border); border-bottom-color:var(--bg); background:var(--bg); }
    .panel { display:none; flex:1; flex-direction:column; overflow-y:auto; padding:20px; gap:0; }
    .panel.active { display:flex; }
    /* Search */
    .search-bar { display:flex; gap:10px; margin-bottom:16px; flex-shrink:0; }
    .search-bar input { flex:1; background:var(--surface); border:1px solid var(--border); border-radius:8px; padding:10px 16px; color:var(--text); font-size:0.9rem; outline:none; transition:border-color 0.15s; }
    .search-bar input:focus { border-color:var(--cyan); }
    .search-bar input::placeholder { color:var(--muted); }
    .result-card { background:var(--surface); border:1px solid var(--border); border-radius:10px; padding:14px 18px; margin-bottom:10px; }
    .result-header { display:flex; justify-content:space-between; align-items:center; margin-bottom:6px; }
    .result-meta { font-size:0.75rem; color:var(--muted); }
    .score-bar-wrap { height:3px; background:var(--border); border-radius:2px; margin:6px 0; }
    .score-bar { height:100%; background:linear-gradient(90deg,var(--cyan),var(--purple)); border-radius:2px; transition:width 0.4s ease; }
    .result-snippet { font-size:0.84rem; color:var(--text); line-height:1.55; }
    /* Ask */
    .ask-bar { display:flex; gap:10px; margin-bottom:16px; flex-shrink:0; }
    .ask-bar input { flex:1; background:var(--surface); border:1px solid var(--border); border-radius:8px; padding:10px 16px; color:var(--text); font-size:0.9rem; outline:none; transition:border-color 0.15s; }
    .ask-bar input:focus { border-color:var(--cyan); }
    .ask-bar input::placeholder { color:var(--muted); }
    .answer-box { background:var(--surface); border:1px solid var(--border); border-radius:10px; padding:18px; font-size:0.9rem; line-height:1.7; min-height:80px; }
    .cursor { display:inline-block; width:2px; height:1em; background:var(--pink); animation:blink 0.8s step-end infinite; vertical-align:text-bottom; margin-left:1px; }
    @keyframes blink { 50%{opacity:0} }
    .source-card { background:var(--surface2); border:1px solid var(--border); border-radius:8px; padding:10px 14px; margin-top:8px; font-size:0.8rem; }
    .source-meta { color:var(--cyan); font-weight:600; margin-bottom:4px; }
    .source-snippet { color:var(--muted); }
    .empty { text-align:center; padding:60px 20px; color:var(--muted); font-size:0.875rem; }
  </style>
</head>
<body>

<nav class="demo-nav" id="demo-nav">
  <a href="index.html">&#8592; Back to site</a>
  <span style="color:var(--border)">|</span>
  <span class="badge" style="font-size:0.7rem;padding:3px 10px">DEMO</span>
  <span class="title">Document Processor</span>
</nav>

<div class="demo-body">
  <aside class="sidebar" id="sidebar">
    <div class="upload-zone" id="upload-zone" role="button" tabindex="0" aria-label="Upload files">
      <div class="uz-icon">&#128196;</div>
      <p>Drop files here or click</p>
      <p style="font-size:0.7rem;margin-top:4px">PDF · DOCX · XLSX</p>
    </div>
    <div class="doc-list" id="doc-list"></div>
    <div class="sidebar-footer">
      <button class="btn btn-ghost" style="width:100%;justify-content:center;font-size:0.8rem" id="refresh-btn">&#8635; Refresh</button>
    </div>
  </aside>

  <div class="main">
    <div class="tab-bar">
      <div class="ptab active" data-panel="search">&#128269; Search</div>
      <div class="ptab" data-panel="ask">&#128172; Ask</div>
    </div>
    <div class="panel active" id="panel-search">
      <div class="search-bar">
        <input type="text" id="search-input" placeholder="Search across documents&#8230;" autocomplete="off"/>
        <button class="btn btn-primary" id="search-btn">Search</button>
      </div>
      <div id="search-results"><div class="empty">Enter a query to search your documents</div></div>
    </div>
    <div class="panel" id="panel-ask">
      <div class="ask-bar">
        <input type="text" id="ask-input" placeholder="Ask anything about your documents&#8230;" autocomplete="off"/>
        <button class="btn btn-primary" id="ask-btn">Ask</button>
      </div>
      <div id="ask-output" style="display:none">
        <div class="answer-box" id="answer-box"></div>
        <div id="sources-list"></div>
      </div>
    </div>
  </div>
</div>

<div class="toast-wrap" id="toasts"></div>

<script>window.DEMO_MODE = true;</script>
<script type="module" src="assets/demo.js"></script>
</body>
</html>
```

- [ ] Open `docs/demo.html` in browser — layout renders (doc list empty, no JS yet).
- [ ] Commit:
```bash
git add docs/demo.html
git commit -m "feat: add demo page HTML layout"
```

---

### Task 7: Demo JS — `docs/assets/demo.js`

**Files:**
- Create: `docs/assets/demo.js`

All server-provided strings (filenames, snippets, scores) are set via `textContent` or typed DOM construction — never passed to `innerHTML`.

- [ ] Create `docs/assets/demo.js`:

```js
import { installMockFetch, MOCK_DOCS } from './mock-data.js';

const DEMO_MODE = window.DEMO_MODE ||
  window.location.hostname.includes('github.io') ||
  new URLSearchParams(window.location.search).has('mock');

const PREVIEW = new URLSearchParams(window.location.search).has('preview');

if (DEMO_MODE) installMockFetch();
if (PREVIEW) {
  document.getElementById('demo-nav').classList.add('hidden');
  document.getElementById('sidebar').classList.add('hidden');
}

// ── Utilities ──────────────────────────────────────────────────────────────

function toast(msg) {
  const el = document.createElement('div');
  el.className = 'toast';
  el.textContent = msg;  // textContent — safe
  document.getElementById('toasts').appendChild(el);
  setTimeout(() => el.remove(), 3000);
}

const FILE_ICONS = { pdf:'📕', docx:'📘', doc:'📘', xlsx:'📗', xls:'📗' };
function fileIcon(type) { return FILE_ICONS[type] || '📄'; }

// ── Document list (all content via textContent / DOM) ──────────────────────

function renderDocItem(doc) {
  const item = document.createElement('div');
  item.className = 'doc-item';

  const name = document.createElement('div');
  name.className = 'doc-name';
  name.textContent = fileIcon(doc.file_type) + ' ' + doc.filename;
  item.appendChild(name);

  const meta = document.createElement('div');
  meta.className = 'doc-meta';

  const badge = document.createElement('span');
  badge.className = 'status status-' + doc.status;
  badge.textContent = doc.status;

  const chunks = document.createElement('span');
  chunks.textContent = doc.chunk_count + ' chunks';

  meta.appendChild(badge);
  meta.appendChild(chunks);
  item.appendChild(meta);
  return item;
}

async function loadDocs() {
  const res = await fetch('/api/v1/documents');
  const data = await res.json();
  const list = document.getElementById('doc-list');
  list.textContent = '';  // clear
  if (!data.documents?.length) {
    const empty = document.createElement('div');
    empty.className = 'empty';
    empty.textContent = 'No documents yet';
    list.appendChild(empty);
    return;
  }
  data.documents.forEach(doc => list.appendChild(renderDocItem(doc)));
}

// ── Upload ─────────────────────────────────────────────────────────────────

const zone = document.getElementById('upload-zone');

async function handleFiles(files) {
  if (DEMO_MODE) { toast('Demo mode — uploads are disabled'); return; }
  const form = new FormData();
  [...files].forEach(f => form.append('files', f));
  const res = await fetch('/api/v1/documents/upload', { method:'POST', body:form });
  const data = await res.json();
  toast(data.message);
  loadDocs();
}

zone.addEventListener('click', () => {
  if (DEMO_MODE) { toast('Demo mode — uploads are disabled'); return; }
  const inp = document.createElement('input');
  inp.type = 'file'; inp.multiple = true; inp.accept = '.pdf,.docx,.doc,.xlsx,.xls';
  inp.onchange = () => handleFiles(inp.files);
  inp.click();
});
zone.addEventListener('keydown', e => { if (e.key === 'Enter' || e.key === ' ') zone.click(); });
zone.addEventListener('dragover', e => { e.preventDefault(); zone.classList.add('drag-over'); });
zone.addEventListener('dragleave', () => zone.classList.remove('drag-over'));
zone.addEventListener('drop', e => {
  e.preventDefault(); zone.classList.remove('drag-over');
  handleFiles(e.dataTransfer.files);
});

document.getElementById('refresh-btn').addEventListener('click', loadDocs);

// ── Tab switching ──────────────────────────────────────────────────────────

document.querySelectorAll('.ptab').forEach(tab => {
  tab.addEventListener('click', () => {
    document.querySelectorAll('.ptab').forEach(t => t.classList.remove('active'));
    document.querySelectorAll('.panel').forEach(p => p.classList.remove('active'));
    tab.classList.add('active');
    document.getElementById('panel-' + tab.dataset.panel).classList.add('active');
  });
});

// ── Search ─────────────────────────────────────────────────────────────────

function renderResult(r) {
  const card = document.createElement('div');
  card.className = 'result-card';

  const header = document.createElement('div');
  header.className = 'result-header';

  const meta = document.createElement('span');
  meta.className = 'result-meta';
  meta.textContent = '📄 ' + r.filename + (r.page ? ' · p' + r.page : '') + ' · ' + r.result_type;

  const score = document.createElement('span');
  score.style.cssText = 'font-size:0.75rem;font-weight:700;color:var(--cyan)';
  score.textContent = (r.score * 100).toFixed(1) + '%';

  header.appendChild(meta);
  header.appendChild(score);
  card.appendChild(header);

  const barWrap = document.createElement('div');
  barWrap.className = 'score-bar-wrap';
  const bar = document.createElement('div');
  bar.className = 'score-bar';
  bar.style.width = (r.score * 100).toFixed(1) + '%';
  barWrap.appendChild(bar);
  card.appendChild(barWrap);

  const snippet = document.createElement('p');
  snippet.className = 'result-snippet';
  snippet.textContent = r.content;  // server string via textContent
  card.appendChild(snippet);

  return card;
}

async function doSearch() {
  const query = document.getElementById('search-input').value.trim();
  if (!query) return;
  const btn = document.getElementById('search-btn');
  btn.textContent = '…'; btn.disabled = true;

  const res = await fetch('/api/v1/search', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ query, limit: 10 }),
  });
  const data = await res.json();
  btn.textContent = 'Search'; btn.disabled = false;

  const container = document.getElementById('search-results');
  container.textContent = '';
  if (!data.results?.length) {
    const empty = document.createElement('div');
    empty.className = 'empty';
    empty.textContent = 'No results found — try different keywords';
    container.appendChild(empty);
    return;
  }
  data.results.forEach(r => container.appendChild(renderResult(r)));
}

document.getElementById('search-btn').addEventListener('click', doSearch);
document.getElementById('search-input').addEventListener('keydown', e => { if (e.key === 'Enter') doSearch(); });

// ── Ask ────────────────────────────────────────────────────────────────────

function buildSourceCard(s) {
  const card = document.createElement('div');
  card.className = 'source-card';

  const meta = document.createElement('div');
  meta.className = 'source-meta';
  meta.textContent = '📄 ' + s.filename + (s.page ? ' · p' + s.page : '') + ' · ' + (s.score * 100).toFixed(1) + '%';

  const snip = document.createElement('div');
  snip.className = 'source-snippet';
  snip.textContent = s.snippet;  // server string via textContent

  card.appendChild(meta);
  card.appendChild(snip);
  return card;
}

async function doAsk() {
  const question = document.getElementById('ask-input').value.trim();
  if (!question) return;
  const btn = document.getElementById('ask-btn');
  btn.disabled = true; btn.textContent = 'Thinking…';

  const answerBox = document.getElementById('answer-box');
  const sourcesList = document.getElementById('sources-list');
  const output = document.getElementById('ask-output');

  answerBox.textContent = '';
  sourcesList.textContent = '';
  output.style.display = 'block';

  const cursor = document.createElement('span');
  cursor.className = 'cursor';
  answerBox.appendChild(cursor);

  try {
    const res = await fetch('/api/v1/ask', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question, limit: 5 }),
    });

    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buf = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buf += decoder.decode(value, { stream: true });
      const lines = buf.split('\n'); buf = lines.pop();

      for (const line of lines) {
        if (!line.startsWith('data: ')) continue;
        let payload;
        try { payload = JSON.parse(line.slice(6)); } catch { continue; }

        if (payload.type === 'sources') {
          payload.data.forEach(s => sourcesList.appendChild(buildSourceCard(s)));
        } else if (payload.type === 'token') {
          cursor.remove();
          answerBox.appendChild(document.createTextNode(payload.data));
          answerBox.appendChild(cursor);
        } else if (payload.type === 'done') {
          cursor.remove();
        } else if (payload.type === 'error') {
          cursor.remove();
          answerBox.style.color = '#f87171';
          answerBox.textContent = 'Error: ' + payload.data;
        }
      }
    }
  } catch (err) {
    cursor.remove();
    answerBox.style.color = '#f87171';
    answerBox.textContent = 'Error: ' + err.message;
  } finally {
    btn.disabled = false; btn.textContent = 'Ask';
  }
}

document.getElementById('ask-btn').addEventListener('click', doAsk);
document.getElementById('ask-input').addEventListener('keydown', e => { if (e.key === 'Enter') doAsk(); });

// ── Init ───────────────────────────────────────────────────────────────────

loadDocs();
```

- [ ] Open `docs/demo.html` in browser. Verify:
  - 4 mock documents appear in sidebar with icons and status badges
  - Search "revenue" → 4 result cards with score bars appear
  - Ask "What is the revenue?" → answer streams word-by-word with pink cursor; source cards appear below
  - Upload zone shows "Demo mode — uploads are disabled" toast
  - `demo.html?preview=1` hides nav and sidebar (for iframe embed)
- [ ] Commit:
```bash
git add docs/assets/demo.js
git commit -m "feat: add demo UI logic with mock interception and SSE streaming"
```

---

### Task 8: Production UI

**Files:**
- Modify: `data-platform/apps/document-processor/ui/index.html`

- [ ] Copy demo.html as the base:
```bash
cp docs/demo.html data-platform/apps/document-processor/ui/index.html
```

- [ ] Copy shared assets:
```bash
mkdir -p data-platform/apps/document-processor/ui/assets
cp docs/assets/style.css docs/assets/mock-data.js docs/assets/demo.js \
   data-platform/apps/document-processor/ui/assets/
```

- [ ] Edit `data-platform/apps/document-processor/ui/index.html` — make exactly two changes:

**Remove** the DEMO_MODE script tag (the line `<script>window.DEMO_MODE = true;</script>`).

**Update the nav** — change the back link from `href="index.html"` to `href="/"` and remove the DEMO badge span, since this is the real app:
```html
<nav class="demo-nav" id="demo-nav">
  <span class="title">Document Processor</span>
</nav>
```

- [ ] Check `api/main.py` to confirm how the UI is served. Look for `StaticFiles` or `FileResponse`. If the app serves `ui/index.html` at `/` and `ui/assets/` at `/assets/`, no changes are needed. If the assets path differs, adjust the `<link>` and `<script>` `src` attributes accordingly.

- [ ] Verify in Docker:
```bash
cd data-platform/apps/document-processor
docker compose up --build
# Open http://localhost:8000
# Upload a PDF, wait for "ready", run a search, ask a question
```

- [ ] Commit:
```bash
git add data-platform/apps/document-processor/ui/
git commit -m "feat: replace document processor UI with redesigned version"
```

---

### Task 9: GitHub Pages workflow

**Files:**
- Create: `.github/workflows/pages.yml`

- [ ] Create `.github/workflows/pages.yml`:

```yaml
name: Deploy to GitHub Pages

on:
  push:
    branches: [main, master]
  workflow_dispatch:

permissions:
  contents: read
  pages: write
  id-token: write

concurrency:
  group: pages
  cancel-in-progress: false

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

- [ ] In GitHub → repo Settings → Pages → Source → set to **GitHub Actions**.
- [ ] Commit and push:
```bash
git add .github/workflows/pages.yml
git commit -m "feat: add GitHub Pages deploy workflow"
git push
```
- [ ] Watch Actions tab. After the workflow completes, open the Pages URL and verify the landing page loads with particle animation.

---

### Task 10: Final wiring

**Files:**
- Modify: `.gitignore`
- Modify: `docs/index.html` (real GitHub URL)
- Modify: `docs/demo.html` (real GitHub URL if referenced)

- [ ] Add `.superpowers/` to gitignore:
```bash
echo '.superpowers/' >> .gitignore
```

- [ ] Get the real repo remote URL:
```bash
git remote get-url origin
# e.g. https://github.com/username/data-platform-helm.git
```

- [ ] In `docs/index.html`, replace all three occurrences of `https://github.com/REPLACE_ME` with the actual repo URL (e.g. `https://github.com/username/data-platform-helm`).

- [ ] Final manual verification:
  - [ ] `docs/index.html` — particles, animated metrics, scrolled nav, all 7 sections, SVG tooltips, tab copy buttons
  - [ ] `docs/demo.html` — mock docs, search results with score bars, streaming ask, upload toast
  - [ ] `docs/demo.html?preview=1` — sidebar and nav hidden (iframe mode works)
  - [ ] GitHub Pages URL loads landing page after push
  - [ ] Links to `demo.html` on GitHub Pages work correctly

- [ ] Commit:
```bash
git add .gitignore docs/index.html
git commit -m "chore: wire real GitHub URL and gitignore .superpowers"
git push
```

---

## Spec Coverage

| Requirement | Task |
|---|---|
| Design tokens (dark navy, cyan/pink/purple) | 1 |
| Canvas particle hero | 2 |
| Mock data (4 docs, search, SSE) | 3 |
| Landing page — 7 sections | 4 |
| Animated live metrics | 5 |
| Interactive architecture SVG (hover tooltips, DOM-safe) | 5 |
| Quick start tabs + copy buttons | 4, 5 |
| Pipeline flow diagram | 4 |
| Demo sidebar + upload zone | 6 |
| Search with score bars | 7 |
| Streaming ask with cursor + source cards | 7 |
| DEMO_MODE detection | 3, 7 |
| `?preview=1` iframe mode | 6, 7 |
| Production UI (no mock) | 8 |
| GitHub Pages workflow | 9 |
| `.superpowers/` gitignored | 10 |
| XSS safety (no user input to innerHTML) | 5, 7 |
