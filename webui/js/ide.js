// ide.js — Page A: EDA tool (Quartus Prime Lite look-alike).
import { apiGet, apiPost, connectWS, startHeartbeat, pageUrl, isMock } from './api.js';

const $ = (id) => document.getElementById(id);

// ---- page state ----
let project = null;          // {path, name, top, device, ports:[{name,dir,width}]}
let assignments = {};        // port-ref -> pin
let boardDef = null;         // board JSON (resources + layout)
let steps = {                // step -> {state, summary}
  synthesis: { state: 'idle', summary: null },
  fitter:    { state: 'idle', summary: null },
  assemble:  { state: 'idle', summary: null },
};
let sof = null;
let selected = 'all';        // selected node in the Tasks tree
let subtab = 'pinout';       // fitter sub-tab
let messages = [];           // {step, level, text}
let programming = false;
let fsState = { path: null, parent: null, dirs: [] };

const STEP_ORDER = ['synthesis', 'fitter', 'assemble'];
const STEP_TITLE = {
  all: 'Flow Overview',
  synthesis: 'Analysis & Synthesis — Flow Summary',
  fitter: 'Fitter (Place & Route)',
  assemble: 'Assembler — Output Files',
};

init();

async function init() {
  $('tabIde').href = pageUrl('index.html');
  $('tabBoard').href = pageUrl('board.html');
  if (isMock()) $('mockFlag').hidden = false;
  startHeartbeat();
  wireTasks();
  wireMessages();
  wireFsModal();
  wireProgrammer();
  wireSubtabs();
  try { boardDef = await apiGet('/api/board'); } catch (e) { /* board view still works without */ }
  await refreshProject();
  await refreshStatus();
  connectWS({
    onOpen: () => { setConn(true); refreshStatus(); },
    onClose: () => setConn(false),
    onMsg: onWsMessage,
  });
  renderReport();
}

// ---------- connection ----------
function setConn(ok) {
  const el = $('connState');
  el.textContent = ok ? '' : 'Connection lost — reconnecting…';
  el.className = 'conn' + (ok ? '' : ' bad');
}

// ---------- WebSocket messages ----------
function onWsMessage(m) {
  if (m.type === 'log') {
    addMessage(m);
  } else if (m.type === 'step') {
    if (steps[m.step]) {
      steps[m.step] = { state: m.state, summary: m.summary ?? steps[m.step].summary };
      if (m.step === 'assemble' && m.state === 'ok' && m.summary) sof = m.summary;
      updateTaskIcons();
      $('statusText').textContent = m.state === 'running'
        ? `Running ${STEP_TITLE[m.step] || m.step}…` : 'Ready';
      renderReport();
    }
  } else if (m.type === 'program') {
    programProgress(m);
  } else if (m.type === 'board') {
    $('boardState').textContent =
      'Board: ' + (m.power ? (m.configured ? `RUNNING (rev ${m.rev})` : 'ON, unconfigured') : 'OFF');
  }
}

// ---------- Tasks tree ----------
function wireTasks() {
  document.querySelectorAll('#taskTree .trow[data-select]').forEach(row => {
    const step = row.dataset.select;
    row.addEventListener('click', (ev) => {
      if (ev.target.closest('.trun')) return;
      if (ev.target.closest('.twisty')) return;
      selectNode(step);
    });
    row.addEventListener('dblclick', (ev) => {
      if (ev.target.closest('.trun')) return;
      runStep(step);
    });
    const runBtn = row.querySelector('.trun');
    if (runBtn) runBtn.addEventListener('click', (ev) => { ev.stopPropagation(); runStep(step); });
  });
  $('twisty').addEventListener('click', () => {
    $('taskChildren').classList.toggle('collapsed');
    $('twisty').classList.toggle('closed');
  });
  $('programmerRow').addEventListener('click', openProgrammer);
}

function selectNode(step) {
  selected = step;
  document.querySelectorAll('#taskTree .trow').forEach(r => r.classList.toggle('sel', r.dataset.select === step));
  $('reportSubtabs').hidden = step !== 'fitter';
  $('reportTitle').textContent = STEP_TITLE[step] || step;
  $('reportSub').textContent = '';
  renderReport();
}

function updateTaskIcons() {
  for (const step of STEP_ORDER) {
    const icon = document.querySelector(`.tnode[data-step="${step}"] .ticon`);
    icon.className = 'ticon st-' + steps[step].state;
  }
  // aggregate state for "Compile Design"
  const states = STEP_ORDER.map(s => steps[s].state);
  let agg = 'idle';
  if (states.includes('running')) agg = 'running';
  else if (states.includes('fail')) agg = 'fail';
  else if (states.every(s => s === 'ok')) agg = 'ok';
  else if (states.includes('stale') || states.includes('ok')) agg = 'stale';
  document.querySelector('.tnode[data-step="all"] .ticon').className = 'ticon st-' + agg;
}

async function runStep(step) {
  if (!project) { toast('Open a project first (Open Project…)', true); return; }
  // Prerequisite check: running a later stage while an earlier one is not OK.
  if (step !== 'all') {
    const idx = STEP_ORDER.indexOf(step);
    const bad = STEP_ORDER.slice(0, idx).find(s => steps[s].state !== 'ok');
    if (bad) {
      const go = await confirmModal(
        `"${STEP_TITLE[step].split(' — ')[0]}" depends on "${STEP_TITLE[bad].split(' — ')[0]}", ` +
        `which is ${steps[bad].state === 'stale' ? 'out of date' : 'not done yet'}.\n` +
        `Run the full compilation flow instead?`);
      if (!go) return;
      step = 'all';
    }
  }
  try {
    await apiPost('/api/compile/' + step, {});
  } catch (e) {
    addMessage({ step: 'project', level: 'error', text: `Error: ${e.message || e}` });
    toast(e.message || String(e), true);
  }
}

// ---------- report area ----------
function wireSubtabs() {
  document.querySelectorAll('#reportSubtabs .subtab').forEach(b => {
    b.addEventListener('click', () => { subtab = b.dataset.sub; renderReport(); });
  });
}

function renderReport() {
  const body = $('reportBody');
  if (selected === 'all') return renderOverview(body);
  if (selected === 'synthesis') return renderSynthesis(body);
  if (selected === 'fitter') return renderFitter(body);
  if (selected === 'assemble') return renderAssemble(body);
}

function renderOverview(body) {
  const rows = STEP_ORDER.map(s => {
    const st = steps[s];
    return `<div class="ovrow">
      <span class="ticon st-${st.state}"></span>
      <span class="ovname">${STEP_TITLE[s].split(' — ')[0]}</span>
      <span class="ovstate">${st.state}</span>
    </div>`;
  }).join('');
  const sofLine = sof
    ? `<div class="ovsof mono">Programming file: ${esc(sof.name)} (${fmtBytes(sof.size_bytes)})</div>`
    : `<div class="ovsof muted">No programming file yet — run Assembler.</div>`;
  body.innerHTML = `<div class="overview">${rows}${sofLine}</div>`;
}

function renderSynthesis(body) {
  const s = steps.synthesis;
  if (!s.summary) { body.innerHTML = `<div class="placeholder">${phText(s.state)}</div>`; return; }
  $('reportSub').textContent = 'Flow Summary';
  body.innerHTML = `<pre class="flowtext">${esc(s.summary)}</pre>`;
}

function renderFitter(body) {
  const s = steps.fitter;
  document.querySelectorAll('#reportSubtabs .subtab').forEach(b => b.classList.toggle('active', b.dataset.sub === subtab));
  if (subtab === 'pinplanner') return renderPinPlanner(body);
  if (!s.summary) { body.innerHTML = `<div class="placeholder">${phText(s.state)}</div>`; return; }
  if (subtab === 'pinout') {
    $('reportSub').textContent = 'Pin-Out';
    const rows = s.summary.pins.map(p =>
      `<tr><td class="mono">${esc(p.pin)}</td><td class="mono">${esc(p.port)}</td>
       <td>${esc(p.resource || '')}</td><td>${esc(p.dir)}</td></tr>`).join('');
    body.innerHTML = `<table class="datatable"><thead>
      <tr><th>Pin</th><th>Port</th><th>Board Resource</th><th>Dir</th></tr></thead>
      <tbody>${rows}</tbody></table>`;
  } else if (subtab === 'timing') {
    $('reportSub').textContent = 'Timing Summary';
    const t = s.summary.timing;
    const cls = t.pass ? 'pass' : 'fail';
    body.innerHTML = `<div class="timing">
      <div class="tcard ${cls}"><label>Fmax (estimated)</label><b>${t.fmax_mhz.toFixed(2)} MHz</b></div>
      <div class="tcard"><label>Required (50 MHz clock)</label><b>${t.required_mhz.toFixed(2)} MHz / 20.00 ns</b></div>
      <div class="tcard ${cls}"><label>Setup Slack</label><b>${t.slack_ns.toFixed(2)} ns</b></div>
      <div class="tnote ${cls}">${t.pass
        ? 'Timing requirements met. 时序满足。'
        : 'Timing requirements NOT met — the design is too slow for the 50 MHz clock. 时序不满足。'}</div>
    </div>`;
  }
}

function renderAssemble(body) {
  const s = steps.assemble;
  const info = s.summary || sof;
  if (!info) { body.innerHTML = `<div class="placeholder">${phText(s.state)}</div>`; return; }
  body.innerHTML = `<div class="asmfile">
    <div class="row"><label>Programming File</label><span class="mono">${esc(info.name)}</span></div>
    <div class="row"><label>Size</label><span class="mono">${fmtBytes(info.size_bytes)}</span></div>
    <div class="row"><label>Generated</label><span class="mono">${new Date(info.mtime).toLocaleString()}</span></div>
    <div class="row"><label>Revision</label><span class="mono">r${info.revision}</span></div>
    <div class="row muted">Use the Programmer (Tasks pane) to configure the board with this file.</div>
  </div>`;
}

function phText(state) {
  if (state === 'running') return 'Running…';
  if (state === 'fail') return 'Stage failed — see Messages for details.';
  if (state === 'stale') return 'Out of date — run this stage again.';
  return 'Not run yet. Double-click the stage in the Tasks pane.';
}

// ---------- Pin Planner ----------
function boardPinList() {
  if (!boardDef) return [];
  const r = boardDef.resources;
  const out = [
    { pin: r.clk.pin, resource: 'Clock 50MHz (Y7)', group: 'Clock' },
    { pin: r.sw1.pin, resource: 'SW1 RESET', group: 'Buttons' },
    { pin: r.sw2.pin, resource: 'SW2 KEY1', group: 'Buttons' },
    { pin: r.sw3.pin, resource: 'SW3 KEY2', group: 'Buttons' },
    { pin: r.sw4.pin, resource: 'SW4 KEY3', group: 'Buttons' },
    { pin: r.sw5.pin, resource: 'SW5 KEY4', group: 'Buttons' },
    { pin: r.led0.pin, resource: 'LED2 (blue)', group: 'LEDs' },
    { pin: r.led1.pin, resource: 'LED3 (blue)', group: 'LEDs' },
    { pin: r.led2.pin, resource: 'LED4 (blue)', group: 'LEDs' },
    { pin: r.led3.pin, resource: 'LED5 (blue)', group: 'LEDs' },
    { pin: r.vga_hs.pin, resource: 'VGA_HSYNC', group: 'VGA' },
    { pin: r.vga_vs.pin, resource: 'VGA_VSYNC', group: 'VGA' },
  ];
  r.vga_d.pins.forEach((p, i) => out.push({ pin: p, resource: `VGA_D${i}`, group: 'VGA' }));
  return out;
}

function projectPortBits() {
  const bits = [];
  for (const p of (project ? project.ports : [])) {
    if (p.width > 1) for (let i = p.width - 1; i >= 0; i--) bits.push({ ref: `${p.name}[${i}]`, dir: p.dir });
    else bits.push({ ref: p.name, dir: p.dir });
  }
  return bits;
}

function renderPinPlanner(body) {
  $('reportSub').textContent = 'Pin Planner';
  if (!project || !boardDef) { body.innerHTML = '<div class="placeholder">Open a project first.</div>'; return; }
  const pins = boardPinList();
  const pinRes = Object.fromEntries(pins.map(p => [p.pin, p.resource]));
  const usedBy = {}; // pin -> port
  for (const [port, pin] of Object.entries(assignments)) usedBy[pin] = port;

  const rows = projectPortBits().map(b => {
    const cur = assignments[b.ref] || '';
    const opts = ['<option value="">—</option>'].concat(pins.map(p => {
      const clash = usedBy[p.pin] && usedBy[p.pin] !== b.ref;
      return `<option value="${p.pin}" ${p.pin === cur ? 'selected' : ''} ${clash ? 'disabled' : ''}>
        PIN_${p.pin}${clash ? ' (used)' : ''}</option>`;
    })).join('');
    return `<tr data-port="${esc(b.ref)}" class="${cur ? 'assigned' : ''}">
      <td class="mono">${esc(b.ref)}</td><td>${b.dir}</td>
      <td><select class="pinsel">${opts}</select></td>
      <td class="rescell">${esc(pinRes[cur] || '')}</td></tr>`;
  }).join('');

  const groups = {};
  for (const p of pins) (groups[p.group] = groups[p.group] || []).push(p);
  const groupHtml = Object.entries(groups).map(([g, ps]) =>
    `<div class="pgroup"><label>${g}</label><div class="pbtns">${ps.map(p =>
      `<button class="pinbtn ${usedBy[p.pin] ? 'used' : ''}" data-pin="${p.pin}"
        title="${esc(p.resource)}${usedBy[p.pin] ? ' → ' + esc(usedBy[p.pin]) : ''}">${p.pin}</button>`).join('')
    }</div></div>`).join('');

  body.innerHTML = `<div class="pinplanner">
    <div class="ppscroll"><table class="datatable pintable"><thead>
      <tr><th>Port</th><th>Dir</th><th>Pin</th><th>Board Resource</th></tr></thead>
      <tbody>${rows}</tbody></table></div>
    <div class="ppboard">${groupHtml}</div>
  </div>`;

  body.querySelectorAll('.pinsel').forEach(sel => {
    sel.addEventListener('change', async () => {
      const tr = sel.closest('tr');
      const port = tr.dataset.port;
      const prev = assignments[port] || '';
      const pin = sel.value;
      try {
        if (pin) await apiPost('/api/qsf/assign', { port, pin });
        else await apiPost('/api/qsf/unassign', { port });
        if (pin) assignments[port] = pin; else delete assignments[port];
        renderPinPlanner(body); // refresh used/disabled state
      } catch (e) {
        toast(e.message || String(e), true);
        sel.value = prev;
      }
    });
  });
  body.querySelectorAll('.pinbtn').forEach(btn => {
    btn.addEventListener('click', () => {
      body.querySelectorAll('.pintable tr.hit').forEach(r => r.classList.remove('hit'));
      const port = usedBy[btn.dataset.pin];
      if (!port) return;
      const tr = body.querySelector(`tr[data-port="${CSS.escape(port)}"]`);
      if (tr) { tr.classList.add('hit'); tr.scrollIntoView({ block: 'nearest' }); }
    });
  });
}

// ---------- Messages ----------
function wireMessages() {
  $('btnMessages').addEventListener('click', () => { toggleDrawer(); });
  $('msgClose').addEventListener('click', () => { $('msgDrawer').hidden = true; });
  $('msgClear').addEventListener('click', () => { messages = []; renderMessages(); updateBadge(); });
  $('msgFilter').addEventListener('change', renderMessages);
}
function toggleDrawer() {
  const d = $('msgDrawer');
  d.hidden = !d.hidden;
  if (!d.hidden) renderMessages();
}
function addMessage(m) {
  messages.push({ ...m, ts: new Date() });
  updateBadge(m.level === 'error');
  if (!$('msgDrawer').hidden) renderMessages();
}
function updateBadge(flash) {
  const errs = messages.filter(m => m.level === 'error').length;
  const warns = messages.filter(m => m.level === 'warning').length;
  const badge = $('msgBadge');
  badge.hidden = !(errs || warns);
  badge.textContent = (errs ? `✖ ${errs} ` : '') + (warns ? `⚠ ${warns}` : '');
  badge.classList.toggle('has-err', errs > 0);
  if (flash && errs) {
    badge.classList.remove('flash');
    void badge.offsetWidth; // restart animation
    badge.classList.add('flash');
  }
}
function renderMessages() {
  const f = $('msgFilter').value;
  const list = messages.filter(m => !f || m.step === f);
  $('msgList').innerHTML = list.map(m =>
    `<div class="msg lvl-${m.level}"><span class="mtime">${m.ts.toLocaleTimeString()}</span>
     <span class="mstep">[${esc(m.step)}]</span> <span>${esc(m.text)}</span></div>`).join('')
    || '<div class="placeholder">No messages.</div>';
  $('msgList').scrollTop = $('msgList').scrollHeight;
}

// ---------- Open Project ----------
function wireFsModal() {
  $('btnOpenProject').addEventListener('click', openFsModal);
  $('fsCancel').addEventListener('click', () => { $('openProjModal').hidden = true; });
  $('fsUp').addEventListener('click', () => { if (fsState.parent) loadFs(fsState.parent); });
  $('fsSelect').addEventListener('click', async () => {
    $('fsError').hidden = true;
    try {
      await apiPost('/api/project/open', { path: fsState.path });
      $('openProjModal').hidden = true;
      await refreshProject();
      await refreshStatus();
      toast('Project opened: ' + project.name);
      selectNode('all');
    } catch (e) {
      $('fsError').textContent = e.message || String(e);
      $('fsError').hidden = false;
    }
  });
}
async function openFsModal() {
  $('openProjModal').hidden = false;
  $('fsError').hidden = true;
  await loadFs(null); // home
}
async function loadFs(path) {
  try {
    const data = path ? await apiGet('/api/fs/list?path=' + encodeURIComponent(path)) : await apiGet('/api/fs/home');
    fsState = data;
    $('fsPath').textContent = data.path;
    $('fsUp').disabled = !data.parent;
    $('fsList').innerHTML = data.dirs.map(d =>
      `<div class="fsrow" data-path="${esc(d.path)}">
         <span class="fsicon">📁</span><span class="fsname">${esc(d.name)}</span>
         <span class="fsmeta">${d.v ? d.v + ' .v' : ''}${d.qsf ? ' · QSF ✓' : ''}</span>
       </div>`).join('') || '<div class="placeholder">Empty folder.</div>';
    $('fsList').querySelectorAll('.fsrow').forEach(row => {
      row.addEventListener('dblclick', () => loadFs(row.dataset.path));
    });
  } catch (e) {
    $('fsError').textContent = e.message || String(e);
    $('fsError').hidden = false;
  }
}

// ---------- Programmer ----------
function wireProgrammer() {
  $('progClose').addEventListener('click', () => { $('progModal').hidden = true; });
  $('progGoBoard').addEventListener('click', (ev) => { ev.preventDefault(); location.href = pageUrl('board.html'); });
  $('progStart').addEventListener('click', startProgram);
}
async function openProgrammer() {
  if (!project) { toast('Open a project first (Open Project…)', true); return; }
  $('progModal').hidden = false;
  $('progMsg').hidden = true;
  $('progDone').hidden = true;
  $('progBar').style.width = '0%';
  $('progPhase').textContent = 'Idle';
  programming = false;
  $('progStart').disabled = false;
  await refreshStatus();
  $('progFile').textContent = sof ? sof.name : '(no .sof file — run Assembler first)';
}
async function startProgram() {
  $('progMsg').hidden = true;
  $('progDone').hidden = true;
  programming = true;
  $('progStart').disabled = true;
  try {
    await apiPost('/api/program', {});
  } catch (e) {
    // e.g. BOARD_OFF: board not powered — show the backend message as-is
    $('progMsg').textContent = e.message || String(e);
    $('progMsg').hidden = false;
    $('progPhase').textContent = 'Failed';
    programming = false;
    $('progStart').disabled = false;
  }
}
function programProgress(m) {
  if ($('progModal').hidden) return;
  $('progBar').style.width = (m.percent || 0) + '%';
  $('progPhase').textContent = m.phase + (m.phase === 'Done' ? '' : '…');
  if (m.phase === 'Done') {
    programming = false;
    $('progStart').disabled = false;
    $('progDone').hidden = false;
  }
}

// ---------- data loading ----------
async function refreshProject() {
  try {
    project = await apiGet('/api/project');
    $('projName').textContent = project.name;
    $('projPath').textContent = project.path;
    $('projTop').textContent = project.top;
    try { assignments = (await apiGet('/api/qsf')).assignments || {}; } catch (e) { assignments = {}; }
  } catch (e) {
    project = null;
    $('projName').textContent = '—';
    $('projPath').textContent = '—';
    $('projTop').textContent = '—';
  }
}
async function refreshStatus() {
  try {
    const s = await apiGet('/api/compile/status');
    for (const k of STEP_ORDER) if (s.steps && s.steps[k]) steps[k] = s.steps[k];
    sof = s.sof || null;
    updateTaskIcons();
    renderReport();
  } catch (e) { /* backend not ready yet */ }
}

// ---------- confirm modal ----------
function confirmModal(text) {
  return new Promise(resolve => {
    $('confirmText').textContent = text;
    $('confirmModal').hidden = false;
    const done = (v) => { $('confirmModal').hidden = true; resolve(v); };
    $('confirmOk').onclick = () => done(true);
    $('confirmCancel').onclick = () => done(false);
  });
}

// ---------- misc ----------
function toast(text, isErr) {
  const t = document.createElement('div');
  t.className = 'toast' + (isErr ? ' err' : '');
  t.textContent = text;
  $('toasts').appendChild(t);
  setTimeout(() => t.classList.add('show'));
  setTimeout(() => { t.classList.remove('show'); setTimeout(() => t.remove(), 400); }, 4200);
}
function esc(s) {
  return String(s ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
}
function fmtBytes(n) {
  if (n >= 1048576) return (n / 1048576).toFixed(2) + ' MB';
  if (n >= 1024) return (n / 1024).toFixed(1) + ' KB';
  return n + ' B';
}
