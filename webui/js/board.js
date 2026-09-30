// board.js — Page B: virtual development board + VGA monitor.
// Board artwork is data-driven from board/ep4ce10_pro.json (layout field).
import { apiGet, apiPost, connectWS, startHeartbeat, pageUrl, isMock, getMockControls } from './api.js';

const SVGNS = 'http://www.w3.org/2000/svg';
const $ = (id) => document.getElementById(id);

// board state pushed by backend over WS
const state = { power: false, configured: false, conf_done: false, sim_running: false, ideal: false, rev: 0 };

let scene, boardG;
let ledEls = [], confLedEl, powerLedEl, knobEl, noSignalG;
let canvas, ctx, imgData, buf32;
let lastFrame = 0;
let knobOffX = 0, knobOnX = 0;

init();

async function init() {
  $('tabIde').href = pageUrl('index.html');
  $('tabBoard').href = pageUrl('board.html');
  startHeartbeat();
  const def = await apiGet('/api/board');
  buildScene(def);
  wireControls();
  connectWS({
    onOpen: () => setConn(true),
    onClose: () => setConn(false),
    onMsg: onWsMessage,
    onFrame: onFrame,
  });
  // No-Signal watchdog: >500ms without a frame => monitor loses sync
  setInterval(() => {
    if (performance.now() - lastFrame > 500) showNoSignal(true);
  }, 200);
  showNoSignal(true);
  applyState();
}

function setConn(ok) {
  const el = $('connState');
  el.textContent = ok ? '' : 'Connection lost — reconnecting…';
  el.className = 'conn' + (ok ? '' : ' bad');
}

// ---------- scene construction (data-driven) ----------
function el(tag, attrs, parent) {
  const e = document.createElementNS(SVGNS, tag);
  for (const k in (attrs || {})) e.setAttribute(k, attrs[k]);
  if (parent) parent.appendChild(e);
  return e;
}
function txt(parent, x, y, str, cls, anchor) {
  const t = el('text', { x, y, class: cls || 'silk', 'text-anchor': anchor || 'middle' }, parent);
  t.textContent = str;
  return t;
}

function buildScene(def) {
  const L = def.layout, R = def.resources;
  scene = $('scene');
  scene.classList.add('off');

  // defs: gradients + glow filters
  const defs = el('defs', null, scene);
  defs.innerHTML = `
    <linearGradient id="pcbGrad" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="#0d6a41"/><stop offset="1" stop-color="#074a2d"/>
    </linearGradient>
    <linearGradient id="metalGrad" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="#f0f0f2"/><stop offset="0.5" stop-color="#b9bcc2"/><stop offset="1" stop-color="#d7d9de"/>
    </linearGradient>
    <linearGradient id="bezelGrad" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="#2a2b31"/><stop offset="1" stop-color="#141519"/>
    </linearGradient>
    <linearGradient id="vgaBlue" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="#3a63a8"/><stop offset="1" stop-color="#22406f"/>
    </linearGradient>
    <filter id="glowBlue" x="-80%" y="-80%" width="260%" height="260%">
      <feGaussianBlur stdDeviation="7" result="b"/>
      <feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge>
    </filter>
    <filter id="glowRed" x="-80%" y="-80%" width="260%" height="260%">
      <feGaussianBlur stdDeviation="5" result="b"/>
      <feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge>
    </filter>
    <filter id="glowGreen" x="-80%" y="-80%" width="260%" height="260%">
      <feGaussianBlur stdDeviation="5" result="b"/>
      <feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge>
    </filter>`;

  // ---- VGA cable (behind board/monitor) ----
  el('path', {
    d: 'M 105 470 C 60 760, 420 920, 720 880 C 950 850, 1010 700, 1035 460',
    class: 'cable', fill: 'none',
  }, scene);

  // ---- PCB ----
  boardG = el('g', { class: 'board', transform: 'translate(24,190) scale(0.79)' }, scene);
  const br = L.board_rect;
  el('rect', { x: br.x, y: br.y, width: br.w, height: br.h, rx: br.rx, class: 'pcb' }, boardG);
  for (const [hx, hy] of [[br.x + 32, br.y + 32], [br.x + br.w - 32, br.y + 32], [br.x + 32, br.y + br.h - 32], [br.x + br.w - 32, br.y + br.h - 32]]) {
    el('circle', { cx: hx, cy: hy, r: 11, class: 'mhole' }, boardG);
    el('circle', { cx: hx, cy: hy, r: 5, class: 'mhole-in' }, boardG);
  }
  txt(boardG, L.silk_title.x, L.silk_title.y, L.silk_title.text, 'silk title');
  txt(boardG, L.silk_title.x, L.silk_title.y + 26, 'EIE330 · Simple VGA Simulator', 'silk subtitle');

  // FPGA chip with pin stubs on all four sides
  const c = L.chip;
  const chipG = el('g', null, boardG);
  const pinCount = 14;
  for (let i = 0; i < pinCount; i++) {
    const fx = c.x + 12 + i * ((c.w - 24) / (pinCount - 1));
    el('line', { x1: fx, y1: c.y - 12, x2: fx, y2: c.y, class: 'chip-pin' }, chipG);
    el('line', { x1: fx, y1: c.y + c.h, x2: fx, y2: c.y + c.h + 12, class: 'chip-pin' }, chipG);
    const fy = c.y + 12 + i * ((c.h - 24) / (pinCount - 1));
    el('line', { x1: c.x - 12, y1: fy, x2: c.x, y2: fy, class: 'chip-pin' }, chipG);
    el('line', { x1: c.x + c.w, y1: fy, x2: c.x + c.w + 12, y2: fy, class: 'chip-pin' }, chipG);
  }
  el('rect', { x: c.x, y: c.y, width: c.w, height: c.h, rx: 6, class: 'chip' }, chipG);
  el('circle', { cx: c.x + 16, cy: c.y + 16, r: 7, class: 'chip-dot' }, chipG);
  c.text.forEach((line, i) => txt(chipG, c.x + c.w / 2, c.y + c.h / 2 - 10 + i * 26, line, 'chip-text'));

  // 50MHz oscillator
  const o = L.osc;
  el('rect', { x: o.x, y: o.y, width: o.w, height: o.h, rx: 7, class: 'osc' }, boardG);
  el('rect', { x: o.x + 5, y: o.y + 5, width: o.w - 10, height: o.h - 10, rx: 5, class: 'osc-in' }, boardG);
  txt(boardG, o.x + o.w / 2, o.y + o.h / 2 + 4, o.text, 'osc-text');
  txt(boardG, o.x + o.w / 2, o.y - 10, 'Y7', 'silk');

  // JTAG header (2x5)
  const j = L.jtag;
  el('rect', { x: j.x, y: j.y, width: j.w, height: j.h, rx: 4, class: 'jtag' }, boardG);
  for (let r = 0; r < 2; r++) for (let i = 0; i < 5; i++) {
    el('circle', { cx: j.x + 18 + i * ((j.w - 36) / 4), cy: j.y + 12 + r * 20, r: 4, class: 'jtag-pin' }, boardG);
  }
  txt(boardG, j.x + j.w / 2, j.y - 10, j.text, 'silk');

  // CONF_DONE LED
  const cd = L.conf_done;
  confLedEl = el('circle', { cx: cd.x, cy: cd.y, r: cd.r, class: 'confled' }, boardG);
  txt(boardG, cd.x + cd.r + 8, cd.y + 4, cd.text, 'silk', 'start');

  // power jack
  const pj = L.power_jack;
  el('circle', { cx: pj.x, cy: pj.y, r: pj.r, class: 'pjack' }, boardG);
  el('circle', { cx: pj.x, cy: pj.y, r: pj.r * 0.55, class: 'pjack-ring' }, boardG);
  el('circle', { cx: pj.x, cy: pj.y, r: 6, class: 'pjack-hole' }, boardG);
  txt(boardG, pj.x, pj.y + pj.r + 18, pj.text, 'silk');

  // power switch
  const ps = L.power_sw;
  const swG = el('g', { class: 'powersw', id: 'powerSw' }, boardG);
  el('rect', { x: ps.x, y: ps.y, width: ps.w, height: ps.h, rx: 8, class: 'psw-base' }, swG);
  el('rect', { x: ps.x + 6, y: ps.y + 8, width: ps.w - 12, height: ps.h - 16, rx: 5, class: 'psw-slot' }, swG);
  knobOffX = ps.x + 8;
  knobOnX = ps.x + ps.w - 8 - 38;
  knobEl = el('rect', { x: knobOffX, y: ps.y + 5, width: 38, height: ps.h - 10, rx: 5, class: 'psw-knob' }, swG);
  txt(boardG, ps.x + ps.w / 2, ps.y + ps.h + 20, ps.text, 'silk');
  txt(boardG, ps.x - 6, ps.y + ps.h / 2 + 4, 'OFF', 'silk tiny', 'end');
  txt(boardG, ps.x + ps.w + 6, ps.y + ps.h / 2 + 4, 'ON', 'silk tiny', 'start');

  // power LED
  const pl = L.power_led;
  powerLedEl = el('circle', { cx: pl.x, cy: pl.y, r: pl.r, class: 'powerled' }, boardG);
  txt(boardG, pl.x, pl.y + pl.r + 18, pl.text, 'silk');

  // VGA connector (DB15)
  const v = L.vga_conn;
  el('rect', { x: v.x, y: v.y, width: v.w, height: v.h, rx: 8, class: 'vgaconn' }, boardG);
  for (let r = 0; r < 3; r++) for (let i = 0; i < 5; i++) {
    el('circle', { cx: v.x + 22 + i * ((v.w - 44) / 4), cy: v.y + 13 + r * 17, r: 4.5, class: 'vga-hole' }, boardG);
  }
  txt(boardG, v.x + v.w / 2, v.y + v.h + 20, v.text, 'silk');

  // tactile buttons SW1..SW5
  L.buttons.forEach((b, i) => {
    const res = R[b.id];
    const g = el('g', { class: 'keybtn', 'data-i': i }, boardG);
    el('rect', { x: b.x - b.size / 2, y: b.y - b.size / 2, width: b.size, height: b.size, rx: 10, class: 'keybase' }, g);
    el('circle', { cx: b.x, cy: b.y, r: b.size * 0.33, class: 'keycap' }, g);
    txt(boardG, b.x, b.y + b.size / 2 + 22, res.silk, 'silk bold');
    txt(boardG, b.x, b.y + b.size / 2 + 40, res.label, 'silk small');
  });

  // user LEDs LED2..LED5
  L.leds.forEach(l => {
    const res = R[l.id];
    ledEls.push(el('circle', { cx: l.x, cy: l.y, r: l.r, class: 'led' }, boardG));
    txt(boardG, l.x, l.y + l.r + 20, res.label, 'silk');
  });

  // ---- monitor ----
  const mon = el('g', { transform: 'translate(1030,55)' }, scene);
  el('path', { d: 'M 300 560 L 400 560 L 438 655 L 262 655 Z', class: 'stand' }, mon);
  el('ellipse', { cx: 350, cy: 668, rx: 122, ry: 20, class: 'stand-base' }, mon);
  el('rect', { x: 0, y: 0, width: 700, height: 560, rx: 18, class: 'bezel' }, mon);
  el('rect', { x: 24, y: 24, width: 652, height: 492, rx: 6, class: 'screen-frame' }, mon);

  const fo = el('foreignObject', { x: 30, y: 30, width: 640, height: 480 }, mon);
  const div = document.createElement('div');
  div.setAttribute('xmlns', 'http://www.w3.org/1999/xhtml');
  div.className = 'screen-wrap';
  canvas = document.createElement('canvas');
  canvas.width = 640; canvas.height = 480;
  div.appendChild(canvas);
  fo.appendChild(div);

  noSignalG = el('g', { class: 'nosignal' }, mon);
  el('rect', { x: 30, y: 30, width: 640, height: 480, class: 'nosignal-bg' }, noSignalG);
  el('rect', { x: 240, y: 210, width: 220, height: 64, rx: 10, class: 'nosignal-box' }, noSignalG);
  txt(noSignalG, 350, 250, def.layout.monitor.no_signal_text || 'No Signal', 'nosignal-text');
  el('circle', { cx: 662, cy: 542, r: 5, class: 'mled' }, mon);
  txt(mon, 350, 545, 'VirtuView VM-640', 'mbrand');

  ctx = canvas.getContext('2d');
  imgData = ctx.createImageData(640, 480);
  buf32 = new Uint32Array(imgData.data.buffer);
}

// ---------- controls ----------
function wireControls() {
  scene.addEventListener('click', (ev) => {
    if (ev.target.closest && ev.target.closest('.powersw')) togglePower();
  });

  // hold-to-press buttons (mouse + touch via pointer events)
  scene.querySelectorAll('.keybtn').forEach(g => {
    const i = +g.dataset.i;
    g.addEventListener('pointerdown', (ev) => {
      ev.preventDefault();
      try { g.setPointerCapture(ev.pointerId); } catch (e) { /* noop */ }
      press(i, 0);
    });
    const release = () => press(i, 1);
    g.addEventListener('pointerup', release);
    g.addEventListener('pointercancel', release);
    g.addEventListener('lostpointercapture', release);
  });
  // keyboard: digits 1..5 map to SW1..SW5
  window.addEventListener('keydown', (ev) => {
    if (ev.repeat) return;
    const i = ['1', '2', '3', '4', '5'].indexOf(ev.key);
    if (i >= 0) press(i, 0);
  });
  window.addEventListener('keyup', (ev) => {
    const i = ['1', '2', '3', '4', '5'].indexOf(ev.key);
    if (i >= 0) press(i, 1);
  });

  $('idealSw').addEventListener('change', () => {
    apiPost('/api/ideal', { on: $('idealSw').checked }).catch(e => hint(e.message || String(e), true));
  });

  if (isMock()) {
    getMockControls().then(mc => {
      if (!mc) return;
      $('mockCtl').hidden = false;
      $('mockPause').addEventListener('change', () => { mc.pauseFrames = $('mockPause').checked; });
    });
  }
}

async function togglePower() {
  try { await apiPost('/api/power', { on: !state.power }); }
  catch (e) { hint(e.message || String(e), true); }
}

function press(i, s) {
  const cap = scene.querySelector(`.keybtn[data-i="${i}"] .keycap`);
  if (cap) cap.classList.toggle('down', s === 0);
  // physical button always moves; the board only reacts when powered + configured
  if (state.power) apiPost('/api/input', { button: i, state: s }).catch(() => {});
}

// ---------- WS messages ----------
function onWsMessage(m) {
  if (m.type === 'board') {
    Object.assign(state, m);
    applyState();
  }
}

function applyState() {
  scene.classList.toggle('off', !state.power);
  scene.classList.toggle('live', state.configured && state.sim_running);
  powerLedEl.classList.toggle('on', !!state.power);
  confLedEl.classList.toggle('on', !!state.conf_done);
  knobEl.setAttribute('x', state.power ? knobOnX : knobOffX);
  $('idealSw').checked = !!state.ideal;
  if (!state.power) setLeds(0);
  if (!state.power) hint('Board is OFF — flip the POWER switch on the board.');
  else if (!state.configured) hint('Powered, but FPGA not configured — use the Programmer in the EDA Tool.');
  else hint('Design running — press and hold SW1..SW5 (or keys 1-5).');
}

function hint(text, isErr) {
  const el = $('boardHint');
  el.textContent = text;
  el.classList.toggle('err', !!isErr);
}

// ---------- VGA frames ----------
function onFrame(ab) {
  const dv = new DataView(ab);
  if (dv.getUint32(0, true) !== 0x31474156) return; // 'VGA1'
  setLeds(dv.getUint8(8));
  const px = new Uint16Array(ab, 12);
  for (let i = 0; i < px.length; i++) {
    const v = px[i];
    const r = (v >> 11) & 31, g = (v >> 5) & 63, b = v & 31;
    buf32[i] = 0xFF000000 | (((b << 3) | (b >> 2)) << 16) | (((g << 2) | (g >> 4)) << 8) | ((r << 3) | (r >> 2));
  }
  ctx.putImageData(imgData, 0, 0);
  lastFrame = performance.now();
  showNoSignal(false);
}

function setLeds(bits) {
  ledEls.forEach((e, i) => e.classList.toggle('on', !!((bits >> i) & 1)));
}

function showNoSignal(show) {
  noSignalG.classList.toggle('hidden', !show);
}
