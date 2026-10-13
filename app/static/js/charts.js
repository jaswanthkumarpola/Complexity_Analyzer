/**
 * charts.js — Complexity growth curve visualization using Chart.js
 * Gracefully degrades if Chart.js CDN is unavailable.
 */
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

/**
 * Render the complexity growth chart.
 * @param {object} vizData - VisualizationData from backend
 */
function renderComplexityChart(vizData) {
  const canvas = document.getElementById('complexity-chart');
  const legendEl = document.getElementById('chart-legend');
  const disclaimerEl = document.getElementById('chart-disclaimer');

  if (!canvas) return;

  // Show disclaimer
  if (disclaimerEl && vizData.disclaimer) {
    disclaimerEl.textContent = vizData.disclaimer;
  }

  // Fallback: text table if Chart.js not available
  if (window.CHARTJS_FAILED || typeof Chart === 'undefined') {
    renderTextFallback(canvas, vizData);
    return;
  }

  // Destroy previous chart
  if (complexityChart) {
    complexityChart.destroy();
    complexityChart = null;
  }

  const labels = (vizData.x_values || []).map(n => {
    if (n >= 1000) return `${n / 1000}k`;
    return String(Math.round(n));
  });

  const datasets = [];
  const curveEntries = Object.entries(vizData.curves || {});

  for (const [label, values] of curveEntries) {
    const config = CURVE_COLORS[label] || { color: '#64748B', dash: [] };
    const isHighlighted = label === vizData.highlight_curve;
    const capped = values.map(v => Math.min(v, 50000)); // Cap for readability

    datasets.push({
      label,
      data: capped,
      borderColor: config.color,
      backgroundColor: 'transparent',
      borderWidth: isHighlighted ? 3 : 1.5,
      borderDash: config.dash,
      pointRadius: isHighlighted ? 4 : 0,
      pointHoverRadius: 5,
      pointBackgroundColor: config.color,
      tension: 0.3,
      order: isHighlighted ? 0 : 1,
    });
  }

  const ctx = canvas.getContext('2d');
  complexityChart = new Chart(ctx, {
    type: 'line',
    data: { labels, datasets },
    options: {
      responsive: true,
      maintainAspectRatio: true,
      interaction: {
        mode: 'index',
        intersect: false,
      },
      plugins: {
        legend: { display: false },
        tooltip: {
          backgroundColor: '#1E1E2E',
          borderColor: '#2A293A',
          borderWidth: 1,
          titleColor: '#F5F3FF',
          bodyColor: '#A1A1B5',
          padding: 10,
          callbacks: {
            label: (ctx) => {
              const isHL = ctx.dataset.label === vizData.highlight_curve;
              const marker = isHL ? ' ← predicted' : '';
              return ` ${ctx.dataset.label}: ${ctx.parsed.y.toFixed(1)}${marker}`;
            },
          },
        },
      },
      scales: {
        x: {
          title: {
            display: true,
            text: vizData.x_axis_label || 'Input size (n)',
            color: '#6B6B80',
            font: { size: 11, family: 'Inter' },
          },
          ticks: { color: '#6B6B80', font: { size: 10 } },
          grid: { color: 'rgba(42,41,58,0.8)' },
        },
        y: {
          title: {
            display: true,
            text: vizData.y_axis_label || 'Relative growth',
            color: '#6B6B80',
            font: { size: 11, family: 'Inter' },
          },
          ticks: { color: '#6B6B80', font: { size: 10 } },
          grid: { color: 'rgba(42,41,58,0.8)' },
          max: 2000,
          min: 0,
        },
      },
    },
  });

  // Build legend
  if (legendEl) {
    legendEl.innerHTML = '';
    for (const [label] of curveEntries) {
      const config = CURVE_COLORS[label] || { color: '#64748B' };
      const isHL = label === vizData.highlight_curve;
      const item = document.createElement('div');
      item.className = `legend-item${isHL ? ' active' : ''}`;
      item.innerHTML = `
        <span class="legend-swatch" style="background:${config.color}"></span>
        <span>${label}${isHL ? ' ✦' : ''}</span>
      `;
      legendEl.appendChild(item);
    }
  }
}

/**
 * Text-based fallback when Chart.js is unavailable.
 */
function renderTextFallback(canvas, vizData) {
  canvas.style.display = 'none';
  const wrapper = canvas.parentElement;
  const div = document.createElement('div');
  div.style.cssText = 'font-family:monospace;font-size:0.75rem;color:#A1A1B5;padding:0.5rem;';
  div.innerHTML = '<strong>Complexity Classes (Chart.js unavailable)</strong><br>';

  const rows = Object.entries(vizData.curves || {}).map(([label]) => {
    const isHL = label === vizData.highlight_curve;
    return `${isHL ? '→ ' : '  '}${label}${isHL ? ' (predicted)' : ''}`;
  });
  div.innerHTML += rows.join('<br>');
  wrapper.appendChild(div);
}
