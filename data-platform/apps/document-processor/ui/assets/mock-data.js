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
