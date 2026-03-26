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
