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
let selected = sessionStorage.getItem('ide.selected') || 'all';  // selected node in the Tasks tree
let subtab = 'pinout';       // fitter sub-tab
let messages = [];           // {step, level, text}
let programming = false;
let fsState = { path: null, parent: null, dirs: [] };

const STEP_ORDER = ['synthesis', 'fitter', 'assemble'];
const COMPILE_STEPS = ['all', ...STEP_ORDER];
const STEP_TITLE = {
  all: 'Flow Overview',
  top: 'Top Module',
  pinplanner: 'Pin Planner',
  synthesis: 'Analysis & Synthesis — Flow Summary',
  fitter: 'Fitter (Place & Route)',
  assemble: 'Assembler — Output Files',
  programmer: 'Programmer',
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
  wireToolsSettings();
  wireSubtabs();
  try { boardDef = await apiGet('/api/board'); } catch (e) { /* board view still works without */ }
  await refreshProject();
  await refreshStatus();
  connectWS({
    onOpen: () => { setConn(true); refreshStatus(); },
    onClose: () => setConn(false),
    onMsg: onWsMessage,
  });
  selectNode(selected);  // restores the view the user was on (page switches)
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
      const prev = steps[m.step];
      steps[m.step] = {
        state: m.state,
        summary: m.summary ?? prev.summary,
        pins: m.pins ?? prev.pins,
        timing: m.timing ?? prev.timing,
        sof: m.sof ?? prev.sof,
      };
      if (m.sof) sof = m.sof;
      updateTaskIcons();
      $('statusText').textContent = m.state === 'running'
        ? `Running ${STEP_TITLE[m.step] || m.step}…` : 'Ready';
      renderReport();
    }
  } else if (m.type === 'program') {
    programProgress(m);
  } else if (m.type === 'board') {
    $('boardState').textContent =
      'Board: ' + (m.power ? (m.configured ? 'RUNNING' : 'ON, unconfigured') : 'OFF');
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
}

function selectNode(step) {
  selected = step;
  sessionStorage.setItem('ide.selected', step);
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
  const topIcon = $('topIcon');
  if (topIcon) topIcon.className = 'ticon st-' + (project && project.top ? 'ok' : 'idle');
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
  if (!COMPILE_STEPS.includes(step)) return;
  if (!project) { toast('Open a project first (Open Project…)', true); return; }
  if (!project.top) { toast('Select a top module first (Tasks → Top Module)', true); return; }
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
  if (selected === 'top') return renderTopModule(body);
  if (selected === 'pinplanner') return renderPinPlanner(body);
  if (selected === 'programmer') return renderProgrammer(body);
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
  if (!s.summary) { body.innerHTML = `<div class="placeholder">${phText(s.state)}</div>`; return; }
  if (subtab === 'pinout') {
    $('reportSub').textContent = 'Pin-Out';
    const rows = (s.pins || []).map(p =>
      `<tr><td class="mono">${esc(p.pin)}</td><td class="mono">${esc(p.port)}</td>
       <td>${esc(p.resource || '')}</td><td>${esc(p.dir)}</td></tr>`).join('');
    body.innerHTML = `<table class="datatable"><thead>
      <tr><th>Pin</th><th>Port</th><th>Board Resource</th><th>Dir</th></tr></thead>
      <tbody>${rows}</tbody></table>`;
  } else if (subtab === 'timing') {
    $('reportSub').textContent = 'Timing Summary';
    const t = s.timing;
    if (!t) { body.innerHTML = `<div class="placeholder">No timing data — run Fitter.</div>`; return; }
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
  const info = s.sof || sof;
  if (!info) { body.innerHTML = `<div class="placeholder">${phText(s.state)}</div>`; return; }
  body.innerHTML = `<div class="asmfile">
    <div class="row"><label>Programming File</label><span class="mono">${esc(info.name)}</span></div>
    <div class="row"><label>Size</label><span class="mono">${fmtBytes(info.size_bytes)}</span></div>
    <div class="row"><label>Generated</label><span class="mono">${new Date(info.mtime * 1000).toLocaleString()}</span></div>
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
  if (!project || !boardDef) { body.innerHTML = '<div class="placeholder">Open a project first.</div>'; return; }
  if (!project.top) { body.innerHTML = '<div class="placeholder">Select a top module first (Tasks → Top Module).</div>'; return; }
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

// ---------- Tools & Settings ----------
function wireToolsSettings() {
  $('btnTools').addEventListener('click', openTools);
  $('btnSettings').addEventListener('click', openSettings);
  $('toolsClose').addEventListener('click', () => { $('toolsModal').hidden = true; });
  $('toolsCheck').addEventListener('click', () => runToolsProbe('check'));
  $('toolsSelftest').addEventListener('click', () => runToolsProbe('selftest'));
  $('setCancel').addEventListener('click', () => { $('settingsModal').hidden = true; });
  $('setSave').addEventListener('click', saveSettings);
}

async function openTools() {
  $('toolsModal').hidden = false;
  await runToolsProbe('check');
}

async function runToolsProbe(mode) {
  const tbody = $('toolsTableBody');
  $('toolsCheck').disabled = true;
  $('toolsSelftest').disabled = true;
  tbody.innerHTML = '<tr><td colspan="5" class="placeholder">Checking…</td></tr>';
  try {
    const d = await apiPost('/api/diagnostics/' + mode, {});
    tbody.innerHTML = Object.entries(d).map(([name, t]) => `
      <tr>
        <td class="mono">${esc(name)}</td>
        <td class="mono">${esc(t.required || '—')}</td>
        <td class="mono">${esc(t.path || '—')}</td>
        <td class="mono">${esc(t.version || '—')}</td>
        <td class="${!t.ok ? 'toolbad' : t.warn ? 'toolwarn' : 'toolok'}">${!t.ok ? '✗' : t.warn ? '⚠' : '✓'} ${esc(t.detail || '')}</td>
      </tr>`).join('');
  } catch (e) {
    tbody.innerHTML = `<tr><td colspan="5" class="toolbad">${esc(e.message || String(e))}</td></tr>`;
  } finally {
    $('toolsCheck').disabled = false;
    $('toolsSelftest').disabled = false;
  }
}

async function openSettings() {
  $('settingsModal').hidden = false;
  $('setError').hidden = true;
  try {
    const d = await apiGet('/api/settings/tools');
    $('setVerilator').value = d.overrides.verilator || '';
    $('setGxx').value = d.overrides['g++'] || '';
    $('setYosys').value = d.overrides.yosys || '';
    $('setProvider').textContent = '当前工具链来源 / toolchain provider: ' +
      (d.provider === 'wsl' ? 'WSL（自动回退）' : d.provider === 'native' ? '本机原生 / native' : '未找到 / none');
  } catch (e) {
    $('setProvider').textContent = '';
  }
}

async function saveSettings() {
  $('setError').hidden = true;
  try {
    await apiPost('/api/settings/tools', {
      tools: {
        verilator: $('setVerilator').value.trim(),
        'g++': $('setGxx').value.trim(),
        yosys: $('setYosys').value.trim(),
      },
    });
    $('settingsModal').hidden = true;
    toast('Settings saved');
  } catch (e) {
    $('setError').textContent = e.message || String(e);
    $('setError').hidden = false;
  }
}

// ---------- Open Project ----------
function wireFsModal() {
  $('btnOpenProject').addEventListener('click', openFsModal);
  $('fsCancel').addEventListener('click', () => { $('openProjModal').hidden = true; });
  $('fsUp').addEventListener('click', () => { if (fsState.parent) loadFs(fsState.parent); });
  $('fsPath').addEventListener('keydown', (ev) => {
    if (ev.key === 'Enter') loadFs($('fsPath').value.trim());
  });
  $('fsBrowse').addEventListener('click', async () => {
    try {
      const r = await apiPost('/api/fs/browse', {});
      if (r && r.path) await loadFs(r.path);
    } catch (e) {
      $('fsError').textContent = e.message || String(e);
      $('fsError').hidden = false;
    }
  });
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
    $('fsPath').value = data.path;
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

// ---------- Top Module ----------
function renderTopModule(body) {
  if (!project) { body.innerHTML = '<div class="placeholder">Open a project first (Open Project…).</div>'; return; }
  const mods = project.modules || [];
  if (!mods.length) { body.innerHTML = '<div class="placeholder">No Verilog modules found in this project.</div>'; return; }
  const cur = project.top;
  body.innerHTML = `<div class="topmod">
    <p class="muted small">选择本工程的顶层模块 / Select the top-level module（写入 .qsf 的 TOP_LEVEL_ENTITY）：</p>
    ${mods.map(m => `
      <label class="toprow ${m.supported === false ? 'disabled' : ''}">
        <input type="radio" name="topmod" value="${esc(m.name)}" ${m.name === cur ? 'checked' : ''} ${m.supported === false ? 'disabled' : ''}>
        <span class="mono">${esc(m.name)}</span>
        <span class="muted small">${esc(m.file || '')} · ${(m.ports || []).length} ports${m.supported === false ? ' · unsupported: ' + esc(m.reason || '') : ''}</span>
      </label>`).join('')}
    <div style="margin-top:12px"><button id="topApply" class="btn primary">Set as Top</button></div>
  </div>`;
  $('topApply').addEventListener('click', async () => {
    const sel = body.querySelector('input[name="topmod"]:checked');
    if (!sel) { toast('Select a module first', true); return; }
    try {
      await apiPost('/api/project/top', { top: sel.value });
      await refreshProject();
      await refreshStatus();
      toast('Top module: ' + sel.value);
      renderTopModule(body);
    } catch (e) { toast(e.message || String(e), true); }
  });
}

// ---------- Programmer (inline in the report area) ----------
let progExternal = sessionStorage.getItem('ide.progFile') || null;  // chosen .sof (survives page switches)

async function renderProgrammer(body) {
  if (!project) { body.innerHTML = '<div class="placeholder">Open a project first.</div>'; return; }
  if (!project.top) { body.innerHTML = '<div class="placeholder">Select a top module first (Tasks → Top Module).</div>'; return; }
  body.innerHTML = `<div class="programmer">
    <div class="prow"><label>Hardware:</label> USB-Blaster (virtual) <span class="oktext">[Connected]</span> <span class="mono muted">Mode: JTAG</span></div>
    <div class="prow"><label>File:</label>
      <span id="progFilePath" class="mono ${progExternal ? '' : 'muted'}">${progExternal ? esc(progExternal) : '(未选择 — 请点击 Browse… 选择 .sof 文件 / no file selected)'}</span>
      <button id="progBrowse" class="btn small">Browse…</button>
    </div>
    <div class="progress"><div id="progBar" class="progress-bar"></div></div>
    <div id="progPhase" class="prow phase">Idle</div>
    <div id="progMsg" class="errtext" hidden></div>
    <div id="progDone" class="oktext big" hidden>100% — Configuration successful (CONF_DONE).
      <a id="progGoBoard" href="#">Go to Development Board →</a></div>
    <div class="prow"><button id="progStart" class="btn primary" ${progExternal ? '' : 'disabled'}>Start</button></div>
  </div>`;
  $('progBrowse').addEventListener('click', async () => {
    try {
      const r = await apiPost('/api/fs/browse', { mode: 'file' });
      if (r && r.path) {
        progExternal = r.path;
        sessionStorage.setItem('ide.progFile', progExternal);
        renderProgrammer(body);
      }
    } catch (e) { toast(e.message || String(e), true); }
  });
  $('progGoBoard').addEventListener('click', (ev) => { ev.preventDefault(); location.href = pageUrl('board.html'); });
  $('progStart').addEventListener('click', startProgram);
}

async function startProgram() {
  $('progMsg').hidden = true;
  $('progDone').hidden = true;
  programming = true;
  $('progStart').disabled = true;
  try {
    await apiPost('/api/program', { sof: progExternal });
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
  if (selected !== 'programmer') return;
  const bar = $('progBar');
  if (!bar) return;
  bar.style.width = (m.percent || 0) + '%';
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
    $('projPath').textContent = project.path;
    try { assignments = (await apiGet('/api/qsf')).assignments || {}; } catch (e) { assignments = {}; }
    updateTaskIcons();
  } catch (e) {
    project = null;
    $('projPath').textContent = '—';
    updateTaskIcons();
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
