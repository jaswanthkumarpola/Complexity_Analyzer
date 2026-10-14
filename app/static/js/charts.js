'use strict';

let complexityChart = null;

const CURVE_COLORS = {
  'O(1)':       { color: '#34D399', dash: [] },
  'O(log n)':   { color: '#60A5FA', dash: [] },
  'O(n)':       { color: '#A78BFA', dash: [] },
  'O(n log n)': { color: '#FBBF24', dash: [] },
  'O(n²)':      { color: '#FB923C', dash: [] },
  'O(n³)':      { color: '#F87171', dash: [] },
  'O(2ⁿ)':      { color: '#E879F9', dash: [5, 3] },
  'O(n!)':      { color: '#94A3B8', dash: [2, 4] },
};

// Growth math (all in log10 so huge values never overflow)
function log10Factorial(n) {
  n = Math.round(n);
  if (n < 2) return 0;
  if (n <= 170) {
    let s = 0;
    for (let i = 2; i <= n; i++) s += Math.log10(i);
    return s;
  }
  // Stirling's approximation
  return (n * Math.log(n) - n + 0.5 * Math.log(2 * Math.PI * n)) / Math.LN10;
}

const GROWTH = {
  'O(1)':       { name: 'Constant',     log10: () => 0 },
  'O(log n)':   { name: 'Logarithmic',  log10: n => Math.log10(Math.max(Math.log2(n), 1)) },
  'O(n)':       { name: 'Linear',       log10: n => Math.log10(n) },
  'O(n log n)': { name: 'Linearithmic', log10: n => Math.log10(n) + Math.log10(Math.max(Math.log2(n), 1)) },
  'O(n²)':      { name: 'Quadratic',    log10: n => 2 * Math.log10(n) },
  'O(n³)':      { name: 'Cubic',        log10: n => 3 * Math.log10(n) },
  'O(2ⁿ)':      { name: 'Exponential',  log10: n => n * Math.log10(2) },
  'O(n!)':      { name: 'Factorial',    log10: n => log10Factorial(n) },
};
const CLASS_ORDER = Object.keys(GROWTH);

const OPS_PER_SECOND = 1e9;         
const LOG10_UNIVERSE_SECONDS = 17.64;
const X_MIN = 2;
const X_MAX = 100;

const SUPERSCRIPT = { '0': '⁰', '1': '¹', '2': '²', '3': '³', '4': '⁴', '5': '⁵', '6': '⁶', '7': '⁷', '8': '⁸', '9': '⁹', '-': '⁻' };
const toSuperscript = (s) => String(s).split('').map(c => SUPERSCRIPT[c] || c).join('');

/** Format a quantity given as log10(value). */
function formatLog10(l) {
  if (!isFinite(l)) return '∞';
  if (l < 9) return Math.round(Math.pow(10, l)).toLocaleString('en-US');
  const exp = Math.floor(l);
  const mant = Math.pow(10, l - exp);
  return `${mant.toFixed(1)}×10${toSuperscript(exp)}`;
}

/** Format a duration given as log10(seconds). */
function formatDurationLog10(ls) {
  if (ls > LOG10_UNIVERSE_SECONDS) return 'longer than the age of the universe';
  const sec = Math.pow(10, ls);
  const fmt = (v, unit) => `${v < 10 ? v.toFixed(1) : Math.round(v).toLocaleString('en-US')} ${unit}`;
  if (sec < 1e-6) return '< 1 µs';
  if (sec < 1e-3) return fmt(sec * 1e6, 'µs');
  if (sec < 1)    return fmt(sec * 1e3, 'ms');
  if (sec < 60)   return fmt(sec, 's');
  if (sec < 3600) return fmt(sec / 60, 'min');
  if (sec < 86400) return fmt(sec / 3600, 'hours');
  if (sec < 3.156e7) return fmt(sec / 86400, 'days');
  return fmt(sec / 3.156e7, 'years');
}

/** Axis tick label: 1, 10, 1k, 1M, 1B ... */
function compactNumber(v) {
  if (v >= 1e9) return `${+(v / 1e9).toPrecision(3)}B`;
  if (v >= 1e6) return `${+(v / 1e6).toPrecision(3)}M`;
  if (v >= 1e3) return `${+(v / 1e3).toPrecision(3)}k`;
  return Number.isInteger(v) ? String(v) : v.toFixed(1);
}

function withAlpha(hex, alpha) {
  const h = hex.replace('#', '');
  const r = parseInt(h.substring(0, 2), 16);
  const g = parseInt(h.substring(2, 4), 16);
  const b = parseInt(h.substring(4, 6), 16);
  return `rgba(${r},${g},${b},${alpha})`;
}

// State
const vizState = {
  viz: null,
  classes: CLASS_ORDER.slice(),
  highlight: null,
  logScale: false,
  hidden: new Set(),
  nExp: 30,          // slider value; n = 10^(nExp/10)
};

// Styles (injected once; uses the app's CSS variables)
function ensureStyles() {
  if (document.getElementById('chart-extras-style')) return;
  const style = document.createElement('style');
  style.id = 'chart-extras-style';
  style.textContent = `
    .chart-toolbar { display:flex; align-items:center; justify-content:space-between; gap:.75rem; flex-wrap:wrap; margin-bottom:.6rem; }
    .chart-predicted { font-size:.8rem; color:var(--text-secondary); }
    .chart-predicted strong { color:var(--purple-soft); }
    .chart-seg { display:inline-flex; border:1px solid var(--border); border-radius:var(--radius-sm); overflow:hidden; }
    .chart-seg button { background:transparent; color:var(--text-muted); border:0; padding:.3rem .75rem; font-size:.72rem; cursor:pointer; font-family:inherit; }
    .chart-seg button.on { background:var(--purple-glow); color:var(--purple-soft); font-weight:600; }
    .chart-hint { font-size:.7rem; color:var(--text-muted); margin:.4rem 0 0; min-height:1em; }
    button.legend-btn { background:transparent; border:0; padding:.15rem .3rem; cursor:pointer; font-family:inherit; border-radius:var(--radius-sm); }
    button.legend-btn:hover { background:var(--bg-hover); }
    button.legend-btn.off { opacity:.35; text-decoration:line-through; }
    .n-calc { margin-top:1rem; background:var(--bg-card); border:1px solid var(--border); border-radius:var(--radius-md); padding:1rem; }
    .n-calc-title { font-size:.85rem; font-weight:600; color:var(--text-primary); margin:0 0 .6rem; }
    .n-calc-slider { display:flex; align-items:center; gap:.75rem; margin-bottom:.75rem; }
    .n-calc-slider input[type=range] { flex:1; accent-color:var(--purple-primary); }
    .n-calc-n { font-family:monospace; font-size:.85rem; color:var(--purple-soft); min-width:7.5rem; text-align:right; }
    .n-calc-row { display:grid; grid-template-columns:6.5rem 1fr 1.3fr; gap:.5rem; padding:.3rem .5rem; font-size:.74rem; color:var(--text-muted); border-left:3px solid transparent; border-radius:var(--radius-sm); }
    .n-calc-row.head { font-size:.66rem; text-transform:uppercase; letter-spacing:.05em; }
    .n-calc-row.hl { background:var(--purple-glow); border-left-color:var(--purple-primary); color:var(--text-primary); font-weight:600; }
    .n-calc-note { font-size:.68rem; color:var(--text-muted); margin:.6rem 0 0; font-style:italic; }
  `;
  document.head.appendChild(style);
}

// Public entry point (called from results.js

/**
 * Render the complexity growth chart and the n-calculator.
 * @param {object} vizData - VisualizationData from backend
 */
function renderComplexityChart(vizData) {
  const canvas = document.getElementById('complexity-chart');
  const legendEl = document.getElementById('chart-legend');
  const disclaimerEl = document.getElementById('chart-disclaimer');
  if (!canvas || !legendEl) return;

  ensureStyles();

  if (disclaimerEl && vizData.disclaimer) disclaimerEl.textContent = vizData.disclaimer;

  // Which curves to draw, and which one is predicted
  const fromBackend = Object.keys(vizData.curves || {}).filter(k => GROWTH[k]);
  vizState.viz = vizData;
  vizState.classes = fromBackend.length ? CLASS_ORDER.filter(k => fromBackend.includes(k)) : CLASS_ORDER.slice();
  vizState.highlight = GROWTH[vizData.highlight_curve] ? vizData.highlight_curve : null;
  vizState.hidden = new Set();

  buildToolbar(canvas);
  buildLegend(legendEl);
  buildCalculator(legendEl);

  const chartUnavailable = window.CHARTJS_FAILED || typeof Chart === 'undefined';
  if (chartUnavailable) {
    renderTextFallback(canvas, vizData);
    return;
  }
  drawChart(canvas);
}

// Toolbar (predicted label + scale toggle)
function buildToolbar(canvas) {
  const wrapper = canvas.parentElement;
  const old = document.getElementById('chart-toolbar');
  if (old) old.remove();
  const oldHint = document.getElementById('chart-hint');
  if (oldHint) oldHint.remove();

  // Give the canvas a stable height (the chart no longer depends on aspect ratio)
  wrapper.style.position = 'relative';
  wrapper.style.height = '300px';
  wrapper.style.maxHeight = 'none';

  const bar = document.createElement('div');
  bar.id = 'chart-toolbar';
  bar.className = 'chart-toolbar';

  const predicted = document.createElement('div');
  predicted.className = 'chart-predicted';
  if (vizState.highlight) {
    predicted.appendChild(document.createTextNode('Predicted: '));
    const strong = document.createElement('strong');
    strong.textContent = `${vizState.highlight} · ${GROWTH[vizState.highlight].name}`;
    predicted.appendChild(strong);
  } else {
    predicted.textContent = 'The predicted complexity is not one of the standard curves shown.';
  }

  const seg = document.createElement('div');
  seg.className = 'chart-seg';
  seg.setAttribute('role', 'group');
  seg.setAttribute('aria-label', 'Y-axis scale');
  [['Linear', false], ['Log', true]].forEach(([text, isLog]) => {
    const btn = document.createElement('button');
    btn.type = 'button';
    btn.textContent = text;
    btn.className = vizState.logScale === isLog ? 'on' : '';
    btn.setAttribute('aria-pressed', String(vizState.logScale === isLog));
    btn.addEventListener('click', () => {
      vizState.logScale = isLog;
      Array.from(seg.children).forEach(b => {
        const on = (b.textContent === 'Log') === isLog;
        b.className = on ? 'on' : '';
        b.setAttribute('aria-pressed', String(on));
      });
      const cv = document.getElementById('complexity-chart');
      if (cv && typeof Chart !== 'undefined' && !window.CHARTJS_FAILED) drawChart(cv);
    });
    seg.appendChild(btn);
  });

  bar.appendChild(predicted);
  bar.appendChild(seg);
  wrapper.parentElement.insertBefore(bar, wrapper);

  const hint = document.createElement('p');
  hint.id = 'chart-hint';
  hint.className = 'chart-hint';
  wrapper.parentElement.insertBefore(hint, wrapper.nextSibling);
}

function updateHint() {
  const hint = document.getElementById('chart-hint');
  if (!hint) return;
  hint.textContent = vizState.logScale
    ? 'Log scale: every gridline is 10× higher, so all curves fit. Straight-looking lines still grow very differently.'
    : 'Linear scale: curves that leave the top edge have grown past the chart. Switch to Log to see them all.';
}

// Chart

function seriesFor(label) {
  const pts = [];
  for (let n = X_MIN; n <= X_MAX; n++) {
    pts.push({ x: n, y: Math.pow(10, GROWTH[label].log10(n)) });
  }
  return pts;
}

function drawChart(canvas) {
  if (complexityChart) {
    complexityChart.destroy();
    complexityChart = null;
  }
  updateHint();

  const hl = vizState.highlight;
  const datasets = vizState.classes.map(label => {
    const style = CURVE_COLORS[label] || { color: '#64748B', dash: [] };
    const isHL = label === hl;
    const dim = hl && !isHL;
    return {
      label,
      data: seriesFor(label),
      borderColor: dim ? withAlpha(style.color, 0.5) : style.color,
      backgroundColor: 'transparent',
      borderWidth: isHL ? 3.5 : 1.5,
      borderDash: style.dash,
      pointRadius: 0,
      pointHoverRadius: isHL ? 5 : 3,
      tension: 0.2,
      order: isHL ? 0 : 1,
      hidden: vizState.hidden.has(label),
    };
  });

  // Y-axis configuration
  let yScale;
  if (vizState.logScale) {
    yScale = {
      type: 'logarithmic',
      min: 0.5,
      max: 1e9,
      ticks: {
        color: '#6B6B80', font: { size: 10 },
        callback: (v) => {
          const l = Math.log10(v);
          return Math.abs(l - Math.round(l)) < 1e-9 ? compactNumber(v) : '';
        },
      },
    };
  } else {
    let max = 10000;
    if (hl) {
      const top = Math.pow(10, GROWTH[hl].log10(X_MAX)) * 1.15;
      max = Math.min(Math.max(top, 10), 1e6);
    }
    yScale = {
      type: 'linear',
      min: 0,
      max,
      ticks: { color: '#6B6B80', font: { size: 10 }, callback: (v) => compactNumber(v) },
    };
  }
  yScale.title = {
    display: true,
    text: 'Operations (relative)',
    color: '#6B6B80',
    font: { size: 11, family: 'Inter' },
  };
  yScale.grid = { color: 'rgba(42,41,58,0.8)' };

  const ctx = canvas.getContext('2d');
  complexityChart = new Chart(ctx, {
    type: 'line',
    data: { datasets },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      animation: { duration: 250 },
      interaction: { mode: 'index', intersect: false },
      plugins: {
        legend: { display: false },
        tooltip: {
          backgroundColor: '#1E1E2E',
          borderColor: '#2A293A',
          borderWidth: 1,
          titleColor: '#F5F3FF',
          bodyColor: '#A1A1B5',
          padding: 10,
          itemSort: (a, b) => b.parsed.y - a.parsed.y,
          callbacks: {
            title: (items) => (items.length ? `n = ${items[0].parsed.x}` : ''),
            label: (c) => {
              const marker = c.dataset.label === hl ? ' ← predicted' : '';
              return ` ${c.dataset.label}: ${formatLog10(Math.log10(c.parsed.y))}${marker}`;
            },
          },
        },
      },
      scales: {
        x: {
          type: 'linear',
          min: X_MIN,
          max: X_MAX,
          title: {
            display: true,
            text: (vizState.viz && vizState.viz.x_axis_label) || 'Input size (n)',
            color: '#6B6B80',
            font: { size: 11, family: 'Inter' },
          },
          ticks: { color: '#6B6B80', font: { size: 10 } },
          grid: { color: 'rgba(42,41,58,0.8)' },
        },
        y: yScale,
      },
    },
  });
}

// Legend (click to hide / show a curve)

function buildLegend(legendEl) {
  legendEl.innerHTML = '';
  vizState.classes.forEach((label, idx) => {
    const style = CURVE_COLORS[label] || { color: '#64748B' };
    const isHL = label === vizState.highlight;

    const btn = document.createElement('button');
    btn.type = 'button';
    btn.className = `legend-item legend-btn${isHL ? ' active' : ''}`;
    btn.setAttribute('aria-pressed', 'true');
    btn.title = 'Click to hide or show this curve';

    const swatch = document.createElement('span');
    swatch.className = 'legend-swatch';
    swatch.style.background = style.color;

    const text = document.createElement('span');
    text.textContent = `${label}${isHL ? ' ✦' : ''}`;

    btn.appendChild(swatch);
    btn.appendChild(text);

    btn.addEventListener('click', () => {
      const nowHidden = !vizState.hidden.has(label);
      if (nowHidden) vizState.hidden.add(label); else vizState.hidden.delete(label);
      btn.classList.toggle('off', nowHidden);
      btn.setAttribute('aria-pressed', String(!nowHidden));
      if (complexityChart) {
        complexityChart.setDatasetVisibility(idx, !nowHidden);
        complexityChart.update();
      }
    });
    legendEl.appendChild(btn);
  });
}

// "Real inputs" calculator

function buildCalculator(legendEl) {
  const old = document.getElementById('n-calculator');
  if (old) old.remove();

  const box = document.createElement('div');
  box.id = 'n-calculator';
  box.className = 'n-calc';

  const title = document.createElement('h4');
  title.className = 'n-calc-title';
  title.textContent = 'What does this mean for real inputs?';

  const sliderRow = document.createElement('div');
  sliderRow.className = 'n-calc-slider';

  const slider = document.createElement('input');
  slider.type = 'range';
  slider.min = '10';   // n = 10
  slider.max = '70';   // n = 10,000,000
  slider.step = '1';
  slider.value = String(vizState.nExp);
  slider.setAttribute('aria-label', 'Input size n');

  const nOut = document.createElement('div');
  nOut.className = 'n-calc-n';
  nOut.setAttribute('aria-live', 'polite');

  sliderRow.appendChild(slider);
  sliderRow.appendChild(nOut);

  const table = document.createElement('div');
  table.className = 'n-calc-table';

  const note = document.createElement('p');
  note.className = 'n-calc-note';
  note.textContent = `Illustrative only: assumes ${OPS_PER_SECOND.toExponential(0).replace('e+', '×10^')} simple operations per second and ignores constants, memory and hardware.`;

  box.appendChild(title);
  box.appendChild(sliderRow);
  box.appendChild(table);
  box.appendChild(note);
  legendEl.parentElement.insertBefore(box, legendEl.nextSibling);

  const update = () => {
    vizState.nExp = Number(slider.value);
    const n = Math.round(Math.pow(10, vizState.nExp / 10));
    nOut.textContent = `n = ${n.toLocaleString('en-US')}`;
    renderCalcRows(table, n);
  };
  slider.addEventListener('input', update);
  update();
}

function renderCalcRows(table, n) {
  table.innerHTML = '';

  const addRow = (cls, a, b, c) => {
    const row = document.createElement('div');
    row.className = `n-calc-row${cls ? ' ' + cls : ''}`;
    [a, b, c].forEach(t => {
      const cell = document.createElement('span');
      cell.textContent = t;
      row.appendChild(cell);
    });
    table.appendChild(row);
  };

  addRow('head', 'Class', 'Operations', 'Approx. time');
  vizState.classes.forEach(label => {
    const l = GROWTH[label].log10(n);
    const ls = l - Math.log10(OPS_PER_SECOND);
    addRow(label === vizState.highlight ? 'hl' : '', label, formatLog10(l), formatDurationLog10(ls));
  });
}

// Text fallback when Chart.js is unavailable

function renderTextFallback(canvas, vizData) {
  canvas.style.display = 'none';
  const wrapper = canvas.parentElement;
  wrapper.style.height = 'auto';
  const old = document.getElementById('chart-text-fallback');
  if (old) old.remove();

  const div = document.createElement('div');
  div.id = 'chart-text-fallback';
  div.style.cssText = 'font-family:monospace;font-size:0.75rem;color:#A1A1B5;padding:0.5rem;';

  const heading = document.createElement('strong');
  heading.textContent = 'Complexity Classes (Chart.js unavailable)';
  div.appendChild(heading);

  vizState.classes.forEach(label => {
    const line = document.createElement('div');
    const isHL = label === vizData.highlight_curve;
    line.textContent = `${isHL ? '→ ' : '  '}${label}${isHL ? ' (predicted)' : ''}`;
    div.appendChild(line);
  });
  wrapper.appendChild(div);
}