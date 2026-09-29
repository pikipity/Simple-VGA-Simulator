// mock.js — in-browser fake backend used with ?mock=1. No network calls.
// Simulates: project/QSF, compile pipeline (with WS step/log messages),
// programmer ritual, board state machine, and 30fps fake VGA frames.

const sleep = (ms) => new Promise(r => setTimeout(r, ms));

// ---------- board definition (mirror of board/ep4ce10_pro.json) ----------
let boardDef = null;
async function loadBoardDef() {
  if (boardDef) return boardDef;
  for (const url of ['../board/ep4ce10_pro.json', '/board/ep4ce10_pro.json']) {
    try {
      const r = await fetch(url);
      if (r.ok) { boardDef = await r.json(); return boardDef; }
    } catch (e) { /* try next */ }
  }
  // Fallback copy (only used when the repo file is unreachable).
  boardDef = {
    name: 'EP4CE10_Pro Virtual Board', device: 'EP4CE10F17C8N', family: 'Cyclone IV E', clock_hz: 50000000,
    resources: {
      clk: { kind: 'clock', label: 'Y7 50MHz', pin: 'E1' },
      sw1: { kind: 'button', label: 'RESET', silk: 'SW1', pin: 'M15', active_low: true, wrapper: 'key_reset' },
      sw2: { kind: 'button', label: 'KEY1', silk: 'SW2', pin: 'M2', active_low: true, wrapper: 'key[0]' },
      sw3: { kind: 'button', label: 'KEY2', silk: 'SW3', pin: 'M1', active_low: true, wrapper: 'key[1]' },
      sw4: { kind: 'button', label: 'KEY3', silk: 'SW4', pin: 'E15', active_low: true, wrapper: 'key[2]' },
      sw5: { kind: 'button', label: 'KEY4', silk: 'SW5', pin: 'E16', active_low: true, wrapper: 'key[3]' },
      led0: { kind: 'led', label: 'LED2', pin: 'L7', active_low: true, wrapper: 'led[0]' },
      led1: { kind: 'led', label: 'LED3', pin: 'M6', active_low: true, wrapper: 'led[1]' },
      led2: { kind: 'led', label: 'LED4', pin: 'P3', active_low: true, wrapper: 'led[2]' },
      led3: { kind: 'led', label: 'LED5', pin: 'N3', active_low: true, wrapper: 'led[3]' },
      vga_hs: { kind: 'vga', label: 'VGA_HSYNC', pin: 'C2', wrapper: 'vga_hs' },
      vga_vs: { kind: 'vga', label: 'VGA_VSYNC', pin: 'D1', wrapper: 'vga_vs' },
      vga_d: { kind: 'vga_bus', label: 'VGA_D[15:0]', width: 16, wrapper: 'vga_d',
        pins: ['B4','A2','B5','A6','B6','F6','F7','A7','B7','E8','F8','A8','B8','E7','E6','A5'] },
    },
    vga: { width: 640, height: 480, fps: 60 },
    layout: {
      viewBox: '0 0 1200 780',
      board_rect: { x: 10, y: 10, w: 1180, h: 760, rx: 18 },
      chip: { x: 470, y: 280, w: 240, h: 240, text: ['Cyclone IV E', 'EP4CE10F17C8N'] },
      osc: { x: 780, y: 300, w: 90, h: 46, text: '50.000MHz' },
      jtag: { x: 980, y: 60, w: 150, h: 44, text: 'JTAG / USB-Blaster' },
      conf_done: { x: 900, y: 380, r: 10, text: 'CONF_DONE' },
      power_jack: { x: 60, y: 60, r: 34, text: 'DC 6~12V' },
      power_sw: { x: 180, y: 66, w: 96, h: 42, text: 'POWER' },
      power_led: { x: 310, y: 87, r: 11, text: 'POWER', color: 'red' },
      vga_conn: { x: 24, y: 300, w: 140, h: 60, text: 'VGA' },
      buttons: [
        { id: 'sw1', x: 190, y: 660, size: 58 }, { id: 'sw2', x: 330, y: 660, size: 58 },
        { id: 'sw3', x: 470, y: 660, size: 58 }, { id: 'sw4', x: 610, y: 660, size: 58 },
        { id: 'sw5', x: 750, y: 660, size: 58 },
      ],
      leds: [
        { id: 'led0', x: 260, y: 570, r: 15 }, { id: 'led1', x: 420, y: 570, r: 15 },
        { id: 'led2', x: 580, y: 570, r: 15 }, { id: 'led3', x: 740, y: 570, r: 15 },
      ],
      silk_title: { x: 600, y: 140, text: 'EP4CE10_Pro  Virtual Board' },
      monitor: { screen_w: 640, screen_h: 480, no_signal_text: 'No Signal' },
    },
  };
  return boardDef;
}

// ---------- fake filesystem ----------
const HOME = 'C:/Users/student';
const FS = new Map([
  [HOME, ['Documents', 'Downloads', 'EIE330']],
  [HOME + '/Documents', []],
  [HOME + '/Downloads', []],
  [HOME + '/EIE330', ['Example_1_ColorBar', 'Example_2_BallMove', 'Lab1_Blinky']],
  [HOME + '/EIE330/Example_1_ColorBar', []],
  [HOME + '/EIE330/Example_2_BallMove', []],
  [HOME + '/EIE330/Lab1_Blinky', []],
]);
const FS_META = new Map([
  [HOME + '/EIE330/Example_1_ColorBar', { v: 3, qsf: true, top: 'ColorBar' }],
  [HOME + '/EIE330/Example_2_BallMove', { v: 3, qsf: true, top: 'Simple_VGA' }],
  [HOME + '/EIE330/Lab1_Blinky', { v: 1, qsf: false, top: 'top' }],
]);

// ---------- project templates ----------
const VGA_PINS = ['B4','A2','B5','A6','B6','F6','F7','A7','B7','E8','F8','A8','B8','E7','E6','A5'];
function defaultQsf(ports) {
  const a = {};
  const put = (p, pin) => { if (ports.some(pp => pp.name === p.split('[')[0])) a[p] = pin; };
  put('sys_clk', 'E1'); put('clk', 'E1');
  put('sys_rst_n', 'M15');
  ['key[0]','key[1]','key[2]','key[3]'].forEach((p, i) => put(p, ['M2','M1','E15','E16'][i]));
  ['led[0]','led[1]','led[2]','led[3]'].forEach((p, i) => put(p, ['L7','M6','P3','N3'][i]));
  ['up','down','left','right'].forEach((p, i) => put(p, ['M2','M1','E15','E16'][i]));
  ['led1','led2','led3','led4'].forEach((p, i) => put(p, ['L7','M6','P3','N3'][i]));
  put('hsync', 'C2'); put('vsync', 'D1');
  for (let i = 0; i < 16; i++) put(`rgb[${i}]`, VGA_PINS[i]);
  return a;
}
const PROJECTS = {
  ColorBar: {
    top: 'ColorBar',
    ports: [
      { name: 'sys_clk', dir: 'input', width: 1 },
      { name: 'sys_rst_n', dir: 'input', width: 1 },
      { name: 'hsync', dir: 'output', width: 1 },
      { name: 'vsync', dir: 'output', width: 1 },
      { name: 'rgb', dir: 'output', width: 16 },
    ],
  },
  Simple_VGA: {
    top: 'Simple_VGA',
    ports: [
      { name: 'sys_clk', dir: 'input', width: 1 },
      { name: 'sys_rst_n', dir: 'input', width: 1 },
      { name: 'up', dir: 'input', width: 1 },
      { name: 'down', dir: 'input', width: 1 },
      { name: 'left', dir: 'input', width: 1 },
      { name: 'right', dir: 'input', width: 1 },
      { name: 'hsync', dir: 'output', width: 1 },
      { name: 'vsync', dir: 'output', width: 1 },
      { name: 'rgb', dir: 'output', width: 16 },
      { name: 'led1', dir: 'output', width: 1 },
      { name: 'led2', dir: 'output', width: 1 },
      { name: 'led3', dir: 'output', width: 1 },
      { name: 'led4', dir: 'output', width: 1 },
    ],
  },
  top: {
    top: 'top',
    ports: [
      { name: 'clk', dir: 'input', width: 1 },
      { name: 'rst_n', dir: 'input', width: 1 },
      { name: 'led', dir: 'output', width: 4 },
    ],
  },
};

// ---------- global mock state ----------
const state = {
  project: null,            // {path, name, top, ports}
  qsf: {},                  // port-ref -> pin, e.g. 'rgb[0]' -> 'B4'
  steps: {
    synthesis: { state: 'idle', summary: null },
    fitter:    { state: 'idle', summary: null },
    assemble:  { state: 'idle', summary: null },
  },
  sof: null,
  sofRev: 0,
  running: false,
  programming: false,
  board: { power: false, configured: false, conf_done: false, sim_running: false, ideal: false, rev: 0 },
  buttons: [1, 1, 1, 1, 1], // SW1..SW5, 1=released 0=pressed
};

const clients = new Set();
function broadcast(obj) {
  for (const c of clients) { try { c.onMsg && c.onMsg(obj); } catch (e) { /* noop */ } }
  if (bc) bc.postMessage({ kind: 'msg', payload: obj }); // sync other tabs (page A <-> page B)
}

// --- cross-tab state sharing: the real backend holds state centrally; the mock
// --- emulates that with localStorage (survives navigation) + BroadcastChannel (live sync).
const CH = 'svs_mock_v1';
const bc = ('BroadcastChannel' in window) ? new BroadcastChannel(CH) : null;

(function hydrate() {
  try {
    const raw = localStorage.getItem(CH);
    if (!raw) return;
    const s = JSON.parse(raw);
    if (s.project) state.project = s.project;
    if (s.qsf) state.qsf = s.qsf;
    if (s.steps) state.steps = s.steps;
    if (s.sof) { state.sof = s.sof; state.sofRev = s.sofRev || 0; }
    if (s.board) Object.assign(state.board, s.board);
    if (s.buttons) state.buttons = s.buttons;
  } catch (e) { /* corrupted state: start fresh */ }
})();

function stateSnapshot() {
  return { project: state.project, qsf: state.qsf, steps: state.steps,
    sof: state.sof, sofRev: state.sofRev, board: state.board, buttons: state.buttons };
}
function persist() {
  try { localStorage.setItem(CH, JSON.stringify({ ts: Date.now(), ...stateSnapshot() })); } catch (e) { /* noop */ }
  if (bc) bc.postMessage({ kind: 'state', state: stateSnapshot() });
}
if (bc) bc.onmessage = (ev) => {
  const d = ev.data || {};
  if (d.kind === 'msg') {
    for (const c of clients) { try { c.onMsg && c.onMsg(d.payload); } catch (e) { /* noop */ } }
  } else if (d.kind === 'state') {
    state.project = d.state.project; state.qsf = d.state.qsf; state.steps = d.state.steps;
    state.sof = d.state.sof; state.sofRev = d.state.sofRev; state.buttons = d.state.buttons;
    Object.assign(state.board, d.state.board);
  }
};

function bcastBoard() { persist(); broadcast({ type: 'board', ...state.board }); }
function setStep(step, st, summary) {
  state.steps[step] = { state: st, summary: summary ?? state.steps[step].summary };
  persist();
  broadcast({ type: 'step', step, state: st, summary: state.steps[step].summary });
}
function log(step, level, text) { broadcast({ type: 'log', step, level, text }); }
function markStale(step) { if (state.steps[step].state === 'ok') setStep(step, 'stale'); }

function allPins() {
  const r = boardDef.resources;
  return [r.clk.pin, r.sw1.pin, r.sw2.pin, r.sw3.pin, r.sw4.pin, r.sw5.pin,
    r.led0.pin, r.led1.pin, r.led2.pin, r.led3.pin, r.vga_hs.pin, r.vga_vs.pin, ...r.vga_d.pins];
}
function pinResource(pin) {
  const r = boardDef.resources;
  const table = [[r.clk.pin, 'Clock 50MHz'], [r.sw1.pin, 'SW1 RESET'], [r.sw2.pin, 'SW2 KEY1'],
    [r.sw3.pin, 'SW3 KEY2'], [r.sw4.pin, 'SW4 KEY3'], [r.sw5.pin, 'SW5 KEY4'],
    [r.led0.pin, 'LED2'], [r.led1.pin, 'LED3'], [r.led2.pin, 'LED4'], [r.led3.pin, 'LED5'],
    [r.vga_hs.pin, 'VGA_HSYNC'], [r.vga_vs.pin, 'VGA_VSYNC']];
  for (const [p, name] of table) if (p === pin) return name;
  const i = r.vga_d.pins.indexOf(pin);
  return i >= 0 ? `VGA_D${i}` : '';
}
function portBits() {
  const bits = [];
  for (const p of state.project.ports) {
    if (p.width > 1) for (let i = p.width - 1; i >= 0; i--) bits.push({ ref: `${p.name}[${i}]`, dir: p.dir });
    else bits.push({ ref: p.name, dir: p.dir });
  }
  return bits;
}

// ---------- compile pipeline simulation ----------
async function runSynthesis() {
  setStep('synthesis', 'running');
  log('synthesis', 'info', 'Info: Running Analysis & Synthesis');
  await sleep(500);
  log('synthesis', 'info', 'Info: Elaborating entity "' + state.project.top + '"');
  await sleep(400);
  log('synthesis', 'warning', 'Warning (10240): Verilog HDL Always Construct warning: inferring latch(es) for variable "pix_data"');
  await sleep(400);
  const le = 980 + Math.floor(Math.random() * 120);
  const regs = 180 + Math.floor(Math.random() * 60);
  const pins = portBits().length;
  const summary = [
    'Flow Summary',
    '------------------------------------',
    `Flow Status                    Successful - ${new Date().toString().slice(0, 24)}`,
    'Quartus Prime Version          23.1std.0 Build 991 Lite Edition',
    `Top-level Entity Name          ${state.project.top}`,
    'Family                         Cyclone IV E',
    'Device                         EP4CE10F17C8',
    `Total logic elements           ${le.toLocaleString()} / 10,320 ( ${Math.round(le / 10320 * 100)} % )`,
    `Total registers                ${regs}`,
    `Total pins                     ${pins} / 180 ( ${Math.round(pins / 180 * 100)} % )`,
    'Total memory bits              0 / 423,936 ( 0 % )',
    'Embedded Multiplier 9-bit      0 / 46 ( 0 % )',
    'Total PLLs                     0 / 2 ( 0 % )',
  ].join('\n');
  log('synthesis', 'info', 'Info: Analysis & Synthesis was successful (0 errors, 1 warning)');
  setStep('synthesis', 'ok', summary);
  markStale('fitter'); markStale('assemble');
}

async function runFitter() {
  setStep('fitter', 'running');
  log('fitter', 'info', 'Info: Running Fitter (Place & Route)');
  await sleep(500);
  const missing = portBits().filter(b => !state.qsf[b.ref]);
  if (missing.length) {
    for (const b of missing.slice(0, 4)) {
      log('fitter', 'error', `Error (176353): Can't place pin "${b.ref}" — no location assignment. Use Pin Planner to assign a pin.`);
    }
    log('fitter', 'error', `Error: Fitter failed, ${missing.length} port(s) have no pin assignment`);
    setStep('fitter', 'fail');
    markStale('assemble');
    return;
  }
  log('fitter', 'info', 'Info: Placed ' + portBits().length + ' pins');
  await sleep(500);
  const fmax = 108.4 + Math.round(Math.random() * 400) / 10;
  const period = 1000 / fmax;
  const slack = 20 - period;
  const summary = {
    pins: Object.entries(state.qsf).map(([port, pin]) => ({
      pin: 'PIN_' + pin, port, resource: pinResource(pin), dir: (portBits().find(b => b.ref === port) || {}).dir || '?',
    })),
    timing: { fmax_mhz: fmax, required_mhz: 50, period_ns: +period.toFixed(2), slack_ns: +slack.toFixed(2), pass: slack >= 0 },
  };
  if (!summary.timing.pass) log('fitter', 'error', 'Error: Setup timing requirement not met (slack ' + summary.timing.slack_ns + ' ns)');
  log('fitter', 'info', 'Info: Fitter was successful');
  setStep('fitter', 'ok', summary);
  markStale('assemble');
}

async function runAssemble() {
  setStep('assemble', 'running');
  log('assemble', 'info', 'Info: Running Assembler (Generate Programming Files)');
  await sleep(700);
  log('assemble', 'info', 'Info: Generating SRAM object file');
  await sleep(700);
  state.sofRev += 1;
  state.sof = {
    name: `output_files/${state.project.top}_r${state.sofRev}.sof`,
    size_bytes: 2867200 + state.sofRev * 977,
    mtime: new Date().toISOString(),
    revision: state.sofRev,
  };
  const summary = { ...state.sof };
  log('assemble', 'info', `Info: Generated programming file ${state.sof.name}`);
  setStep('assemble', 'ok', summary);
}

async function runStep(step) {
  if (state.running) throw { code: 'BUSY', message: 'A compile step is already running' };
  if (!state.project) throw { code: 'NO_PROJECT', message: 'No project is open' };
  state.running = true;
  try {
    if (step === 'synthesis') await runSynthesis();
    else if (step === 'fitter') await runFitter();
    else if (step === 'assemble') await runAssemble();
    else if (step === 'all') {
      await runSynthesis();
      if (state.steps.synthesis.state === 'ok') await runFitter();
      if (state.steps.fitter.state === 'ok') await runAssemble();
    }
  } finally { state.running = false; }
}

async function runProgram() {
  state.programming = true;
  state.board.configured = false; state.board.conf_done = false; state.board.sim_running = false;
  bcastBoard();
  const phases = [['Connecting', 10], ['Erasing', 25], ['Programming', 55], ['Programming', 85], ['Verifying', 100]];
  for (const [phase, percent] of phases) {
    broadcast({ type: 'program', phase, percent });
    await sleep(phase === 'Verifying' ? 400 : 450);
  }
  state.board.configured = true; state.board.conf_done = true; state.board.sim_running = true;
  state.board.rev = state.sofRev;
  bcastBoard();
  broadcast({ type: 'program', phase: 'Done', percent: 100 });
  state.programming = false;
}

// ---------- fake VGA frames (color bars + bouncing ball + key squares) ----------
let frameNo = 0, ballX = 320, ballY = 240, ballVX = 7, ballVY = 5;
const W = 640, H = 480;
const BAR_COLORS = [0xC618, 0xFFE0, 0x07E0 | 0x001F, 0x07E0, 0xF81F, 0xF800, 0x001F, 0x0000]; // gray,yellow,cyan,green,magenta,red,blue,black
function buildFrame() {
  const buf = new ArrayBuffer(12 + W * H * 2);
  const dv = new DataView(buf);
  const px = new Uint16Array(buf, 12);
  frameNo++;
  if (state.buttons[0] === 0) { ballX = 320; ballY = 240; } // SW1 RESET recenters ball
  ballX += ballVX; ballY += ballVY;
  if (ballX < 20 || ballX > W - 20) ballVX = -ballVX;
  if (ballY < 20 || ballY > H - 20) ballVY = -ballVY;
  const t = frameNo * 0.04;
  for (let y = 0; y < H; y++) {
    const shade = 0.72 + 0.28 * Math.sin(t + y * 0.012);
    const row = y * W;
    for (let x = 0; x < W; x++) {
      let c = BAR_COLORS[(x / 80) | 0];
      // apply moving brightness gradient
      let r5 = (c >> 11) & 31, g6 = (c >> 5) & 63, b5 = c & 31;
      r5 = (r5 * shade) | 0; g6 = (g6 * shade) | 0; b5 = (b5 * shade) | 0;
      const dx = x - ballX, dy = y - ballY;
      if (dx * dx + dy * dy < 324) { r5 = 31; g6 = 63; b5 = 31; }
      px[row + x] = (r5 << 11) | (g6 << 5) | b5;
    }
  }
  // bottom strip: 5 squares showing SW1..SW5 state (pressed = green)
  for (let i = 0; i < 5; i++) {
    const on = state.buttons[i] === 0;
    const c = on ? ((0 << 11) | (63 << 5) | 0) : 0x2104;
    for (let y = 442; y < 472; y++) for (let x = 40 + i * 60; x < 76 + i * 60; x++) px[y * W + x] = c;
  }
  const ledBits = ((frameNo >> 4) & 0xF) ^
    ((state.buttons[1] === 0) ? 1 : 0) ^ ((state.buttons[2] === 0) ? 2 : 0) ^
    ((state.buttons[3] === 0) ? 4 : 0) ^ ((state.buttons[4] === 0) ? 8 : 0);
  dv.setUint32(0, 0x31474156, true);
  dv.setUint32(4, frameNo, true);
  dv.setUint8(8, ledBits);
  dv.setUint8(9, 0);
  dv.setUint16(10, 0, true);
  return buf;
}
setInterval(() => {
  if (!state.board.power || !state.board.configured || mockControls.pauseFrames) return;
  const targets = [...clients].filter(c => c.onFrame);
  if (!targets.length) return;
  const buf = buildFrame();
  for (const c of targets) { try { c.onFrame(buf); } catch (e) { /* noop */ } }
}, 33); // ~30fps is enough for preview

// ---------- mock controls (dev aids, e.g. pause frames to test No Signal) ----------
export const mockControls = { pauseFrames: false, state };

// ---------- the mock backend impl (same surface as real one in api.js) ----------
export const mockImpl = {
  mockControls,

  async apiGet(path) {
    await sleep(60);
    if (path === '/api/fs/home' || path.startsWith('/api/fs/list')) {
      const p = path.includes('path=') ? decodeURIComponent(path.split('path=')[1]) : HOME;
      const names = FS.get(p);
      if (!names) throw { code: 'NO_DIR', message: 'Directory not found: ' + p };
      const parent = p === HOME ? null : p.slice(0, p.lastIndexOf('/'));
      return {
        path: p, parent,
        dirs: names.map(n => {
          const full = p + '/' + n;
          const meta = FS_META.get(full) || { v: 0, qsf: false };
          return { name: n, path: full, v: meta.v, qsf: meta.qsf };
        }),
      };
    }
    if (path === '/api/project') {
      if (!state.project) throw { code: 'NO_PROJECT', message: 'No project is open' };
      return state.project;
    }
    if (path === '/api/qsf') {
      if (!state.project) throw { code: 'NO_PROJECT', message: 'No project is open' };
      return { assignments: { ...state.qsf } };
    }
    if (path === '/api/board') return loadBoardDef();
    if (path === '/api/compile/status') {
      return {
        steps: JSON.parse(JSON.stringify(state.steps)),
        sof: state.sof,
      };
    }
    throw { code: 'NOT_FOUND', message: 'Unknown API: ' + path };
  },

  async apiPost(path, body) {
    body = body || {};
    if (path === '/api/heartbeat') return { ts: Date.now() };
    if (path === '/api/project/open') {
      await sleep(150);
      const meta = FS_META.get(body.path);
      if (!FS.has(body.path)) throw { code: 'NO_DIR', message: 'Directory not found: ' + body.path };
      if (!meta || !meta.v) throw { code: 'NO_RTL', message: 'This folder has no .v files. Choose a project folder.' };
      const tpl = PROJECTS[meta.top];
      state.project = {
        path: body.path, name: body.path.split('/').pop(), top: tpl.top,
        device: 'EP4CE10F17C8', family: 'Cyclone IV E',
        ports: tpl.ports, files: tpl.ports.length ? ['rtl/' + tpl.top + '.v'] : [],
      };
      state.qsf = defaultQsf(tpl.ports);
      state.sof = null; state.sofRev = 0;
      for (const s of ['synthesis', 'fitter', 'assemble']) setStep(s, 'idle', null);
      log('project', 'info', `Info: Opened project ${state.project.name}`);
      return state.project;
    }
    if (path === '/api/qsf/assign') {
      if (!state.project) throw { code: 'NO_PROJECT', message: 'No project is open' };
      if (!allPins().includes(body.pin)) throw { code: 'BAD_PIN', message: `Pin ${body.pin} does not exist on this board` };
      const other = Object.entries(state.qsf).find(([p, pin]) => pin === body.pin && p !== body.port);
      if (other) throw { code: 'PIN_CONFLICT', message: `Pin ${body.pin} is already assigned to "${other[0]}"` };
      state.qsf[body.port] = body.pin;
      persist();
      markStale('fitter'); markStale('assemble');
      return { assignments: { ...state.qsf } };
    }
    if (path === '/api/qsf/unassign') {
      delete state.qsf[body.port];
      persist();
      markStale('fitter'); markStale('assemble');
      return { assignments: { ...state.qsf } };
    }
    if (path.startsWith('/api/compile/')) {
      const step = path.split('/').pop();
      if (!['synthesis', 'fitter', 'assemble', 'all'].includes(step)) throw { code: 'NOT_FOUND', message: 'Unknown step' };
      runStep(step); // async; progress reported over WS
      return { started: true };
    }
    if (path === '/api/program') {
      if (state.programming) throw { code: 'BUSY', message: 'Programmer is busy' };
      if (!state.board.power) {
        throw { code: 'BOARD_OFF', message: '未检测到开发板，请检查电源和 USB-Blaster 连接 (No board detected — check power and USB-Blaster cable)' };
      }
      if (!state.sof) throw { code: 'NO_SOF', message: 'No programming file found. Run Assembler first.' };
      runProgram();
      return { started: true };
    }
    if (path === '/api/power') {
      state.board.power = !!body.on;
      if (!state.board.power) { // SRAM semantics: configuration lost on power-off
        state.board.configured = false; state.board.conf_done = false; state.board.sim_running = false;
      }
      bcastBoard();
      return { ...state.board };
    }
    if (path === '/api/input') {
      const b = body.button | 0;
      if (b >= 0 && b < 5) state.buttons[b] = body.state ? 1 : 0;
      persist();
      return { ok: true };
    }
    if (path === '/api/ideal') {
      state.board.ideal = !!body.on;
      bcastBoard();
      return { ideal: state.board.ideal };
    }
    throw { code: 'NOT_FOUND', message: 'Unknown API: ' + path };
  },

  connectWS(handlers) {
    const client = { ...handlers };
    clients.add(client);
    queueMicrotask(() => {
      handlers.onOpen && handlers.onOpen();
      // snapshot on connect, like the real backend
      handlers.onMsg && handlers.onMsg({ type: 'board', ...state.board });
      for (const [step, s] of Object.entries(state.steps)) {
        handlers.onMsg && handlers.onMsg({ type: 'step', step, state: s.state, summary: s.summary });
      }
    });
    return { close() { clients.delete(client); } };
  },
};
