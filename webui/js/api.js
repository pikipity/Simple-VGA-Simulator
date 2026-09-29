// api.js — HTTP + WebSocket client for the v2 backend.
// Token comes from ?token= (stored in localStorage so links across tabs keep it).
// ?mock=1 swaps the whole backend for js/mock.js (no network at all).

const qs = new URLSearchParams(location.search);
if (qs.get('token')) localStorage.setItem('svs_token', qs.get('token'));
if (qs.get('mock') === '1') localStorage.setItem('svs_mock', '1');

export function getToken() { return localStorage.getItem('svs_token') || ''; }
export function isMock() { return localStorage.getItem('svs_mock') === '1'; }

// Link helper that keeps token/mock across page A <-> page B navigation.
export function pageUrl(page) {
  const p = new URLSearchParams();
  if (getToken()) p.set('token', getToken());
  if (isMock()) p.set('mock', '1');
  const s = p.toString();
  return s ? `${page}?${s}` : page;
}

export class ApiError extends Error {
  constructor(code, message) { super(message); this.name = 'ApiError'; this.code = code || 'ERR'; }
}

function unwrap(j) {
  if (j && j.ok) return j.data;
  throw new ApiError(j && j.error && j.error.code, j && j.error && j.error.message || 'Request failed');
}

// ---- real backend over HTTP ----
const real = {
  async apiGet(path) {
    let r;
    try { r = await fetch(path, { headers: { 'X-Board-Token': getToken() } }); }
    catch (e) { throw new ApiError('NETWORK', 'Cannot reach backend: ' + e.message); }
    const j = await r.json().catch(() => null);
    return unwrap(j || { ok: false, error: { code: 'HTTP_' + r.status, message: r.statusText } });
  },
  async apiPost(path, body) {
    let r;
    try {
      r = await fetch(path, {
        method: 'POST',
        headers: { 'X-Board-Token': getToken(), 'Content-Type': 'application/json' },
        body: JSON.stringify(body || {}),
        keepalive: path === '/api/heartbeat',
      });
    } catch (e) { throw new ApiError('NETWORK', 'Cannot reach backend: ' + e.message); }
    const j = await r.json().catch(() => null);
    return unwrap(j || { ok: false, error: { code: 'HTTP_' + r.status, message: r.statusText } });
  },
  connectWS(handlers) {
    let ws = null, closed = false, delay = 1000, timer = null;
    const proto = location.protocol === 'https:' ? 'wss' : 'ws';
    const url = `${proto}://${location.host}/ws?token=${encodeURIComponent(getToken())}`;
    const open = () => {
      ws = new WebSocket(url);
      ws.binaryType = 'arraybuffer';
      ws.onopen = () => { delay = 1000; handlers.onOpen && handlers.onOpen(); };
      ws.onmessage = (ev) => {
        if (typeof ev.data === 'string') {
          try { handlers.onMsg && handlers.onMsg(JSON.parse(ev.data)); } catch (e) { /* bad json */ }
        } else {
          handlers.onFrame && handlers.onFrame(ev.data);
        }
      };
      ws.onclose = () => {
        handlers.onClose && handlers.onClose();
        if (!closed) { timer = setTimeout(open, delay); delay = Math.min(delay * 1.5, 10000); }
      };
      ws.onerror = () => { try { ws.close(); } catch (e) { /* noop */ } };
    };
    open();
    return { close() { closed = true; clearTimeout(timer); try { ws && ws.close(); } catch (e) { /* noop */ } } };
  },
  mockControls: null,
};

let implPromise = null;
function impl() {
  if (!implPromise) {
    implPromise = isMock() ? import('./mock.js').then(m => m.mockImpl) : Promise.resolve(real);
  }
  return implPromise;
}

export async function apiGet(path) { return (await impl()).apiGet(path); }
export async function apiPost(path, body) { return (await impl()).apiPost(path, body); }
export async function connectWS(handlers) { return (await impl()).connectWS(handlers); }
export async function getMockControls() { const i = await impl(); return i.mockControls || null; }

// Watchdog heartbeat: backend exits after 120s without activity.
export function startHeartbeat() {
  const beat = () => apiPost('/api/heartbeat', {}).catch(() => {});
  setInterval(beat, 10000);
  document.addEventListener('visibilitychange', beat); // fire on hide/show too
  beat();
}
