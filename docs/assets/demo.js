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
