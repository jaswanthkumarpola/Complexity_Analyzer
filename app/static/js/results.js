/**
 * results.js — Render analysis results into the DOM
 * All user-provided text is set via textContent (never innerHTML with untrusted data).
 */
'use strict';

// DOM references
const emptyState = document.getElementById('empty-state');
const resultsContent = document.getElementById('results-content');
const loadingOverlay = document.getElementById('loading-overlay');
const errorState = document.getElementById('error-state');
const errorMessage = document.getElementById('error-message');

const methodBadge = document.getElementById('method-badge');
const langDetected = document.getElementById('lang-detected');

const timeExpression = document.getElementById('time-expression');
const timeConfidence = document.getElementById('time-confidence');
const timeJustification = document.getElementById('time-justification');
const spaceExpression = document.getElementById('space-expression');
const spaceConfidence = document.getElementById('space-confidence');
const spaceJustification = document.getElementById('space-justification');

const bestCase = document.getElementById('best-case');
const avgCase = document.getElementById('avg-case');
const worstCase = document.getElementById('worst-case');

const explanationBody = document.getElementById('explanation-body');
const evidenceGrid = document.getElementById('evidence-grid');
const assumptionsBody = document.getElementById('assumptions-body');
const optimizationsList = document.getElementById('optimizations-list');
const chartDisclaimer = document.getElementById('chart-disclaimer');

const loadingSteps = ['step-detect', 'step-parse', 'step-rules', 'step-ai', 'step-result'];
let stepInterval = null;

/**
 * Show loading overlay and animate steps.
 */
function showLoading() {
  emptyState.classList.add('hidden');
  resultsContent.classList.add('hidden');
  errorState.classList.add('hidden');
  loadingOverlay.classList.remove('hidden');

  // Reset steps
  loadingSteps.forEach(id => {
    const el = document.getElementById(id);
    if (el) { el.classList.remove('active', 'done'); }
  });

  let stepIdx = 0;
  stepInterval = setInterval(() => {
    if (stepIdx < loadingSteps.length) {
      if (stepIdx > 0) {
        const prevEl = document.getElementById(loadingSteps[stepIdx - 1]);
        if (prevEl) { prevEl.classList.remove('active'); prevEl.classList.add('done'); }
      }
      const el = document.getElementById(loadingSteps[stepIdx]);
      if (el) el.classList.add('active');
      stepIdx++;
    } else {
      clearInterval(stepInterval);
    }
  }, 800);
}

/**
 * Hide loading overlay.
 */
function hideLoading() {
  if (stepInterval) clearInterval(stepInterval);
  loadingOverlay.classList.add('hidden');
}

/**
 * Show error state.
 */
function showError(message) {
  hideLoading();
  emptyState.classList.add('hidden');
  resultsContent.classList.add('hidden');
  errorState.classList.remove('hidden');
  // Use textContent to avoid XSS
  errorMessage.textContent = message || 'An unexpected error occurred.';
}

/**
 * Render full analysis result.
 * @param {object} result - AnalysisResponse from backend
 */
function renderResults(result) {
  hideLoading();
  errorState.classList.add('hidden');
  emptyState.classList.add('hidden');
  resultsContent.classList.remove('hidden');

  // --- Method badge ---
  const method = result.analysis_method || '';
  const methodLabels = {
    'ai_assisted': 'AI Assisted',
    'static_only': 'Static Analysis',
    'fallback': 'Fallback Mode',
    'hybrid': 'Hybrid',
  };
  methodBadge.textContent = methodLabels[method] || method;
  methodBadge.className = `method-badge ${method.includes('ai') ? 'ai' : method.includes('fallback') ? 'fallback' : 'static'}`;

  // --- Language ---
  const lang = result.language || {};
  langDetected.textContent = lang.display_name || lang.identifier || '?';

  // --- Time Complexity ---
  const tc = result.time_complexity || {};
  timeExpression.textContent = tc.expression || '—';
  timeConfidence.textContent = tc.confidence ? `${tc.confidence} confidence` : '';
  timeConfidence.className = `card-confidence conf-${tc.confidence || 'Unknown'}`;
  timeJustification.textContent = tc.justification || '';

  // --- Space Complexity ---
  const sc = result.space_complexity || {};
  spaceExpression.textContent = sc.expression || '—';
  spaceConfidence.textContent = sc.confidence ? `${sc.confidence} confidence` : '';
  spaceConfidence.className = `card-confidence conf-${sc.confidence || 'Unknown'}`;
  spaceJustification.textContent = sc.justification || '';

  // --- Case Analysis ---
  const cases = result.case_analysis || {};
  bestCase.textContent = cases.best_case?.expression || '—';
  avgCase.textContent = cases.average_case?.expression || '—';
  worstCase.textContent = cases.worst_case?.expression || '—';

  // --- Explanation ---
  explanationBody.textContent = result.explanation || '(No explanation provided.)';

  // --- Static Evidence ---
  renderEvidence(result.static_evidence || {});

  // --- Assumptions & Warnings ---
  renderAssumptions(
    result.assumptions || [],
    result.warnings || [],
    result.limitations || []
  );

  // --- Visualization ---
  if (result.visualization) {
    renderComplexityChart(result.visualization);
    if (result.visualization.disclaimer) {
      chartDisclaimer.textContent = result.visualization.disclaimer;
    }
  }

  // --- Optimizations ---
  renderOptimizations(result.optimizations || []);
}

/**
 * Render static evidence chips.
 */
function renderEvidence(evidence) {
  evidenceGrid.innerHTML = '';

  const chips = [
    { label: 'Parser', value: evidence.parser_used || 'none' },
    { label: 'Loops', value: evidence.loops?.length ?? 0 },
    { label: 'Max Nesting', value: evidence.nested_loops?.length > 0 ? `depth ${Math.max(...evidence.nested_loops.map(l => l.depth || 0))}` : 'none' },
    { label: 'Recursive Calls', value: evidence.recursive_calls?.length ?? 0 },
    { label: 'Has Sorting', value: evidence.has_sorting ? 'Yes' : 'No' },
    { label: 'Binary Search', value: evidence.has_binary_search ? 'Yes' : 'No' },
    { label: 'Early Exit', value: evidence.early_exits ? 'Yes' : 'No' },
    { label: 'Input Variables', value: evidence.input_variables?.join(', ') || 'none' },
  ];

  if (evidence.library_calls?.length) {
    chips.push({ label: 'Library Calls', value: evidence.library_calls.slice(0, 2).join(', ') });
  }
  if (evidence.dominant_operations?.length) {
    chips.push({ label: 'Dominant Ops', value: evidence.dominant_operations[0] });
  }
  if (evidence.parse_errors?.length) {
    chips.push({ label: 'Parse Errors', value: evidence.parse_errors[0].substring(0, 40) });
  }

  chips.forEach(({ label, value }) => {
    const chip = document.createElement('div');
    chip.className = 'evidence-chip';
    const lbl = document.createElement('span');
    lbl.className = 'evidence-chip-label';
    lbl.textContent = label;
    const val = document.createElement('span');
    val.className = 'evidence-chip-value';
    val.textContent = String(value);
    chip.appendChild(lbl);
    chip.appendChild(val);
    evidenceGrid.appendChild(chip);
  });

  // Evidence toggle
  const toggle = document.getElementById('evidence-toggle');
  const body = document.getElementById('evidence-body');
  if (toggle && body) {
    toggle.onclick = () => {
      const expanded = toggle.getAttribute('aria-expanded') === 'true';
      toggle.setAttribute('aria-expanded', String(!expanded));
      body.classList.toggle('hidden', expanded);
    };
    toggle.onkeydown = (e) => { if (e.key === 'Enter' || e.key === ' ') toggle.click(); };
  }
}

/**
 * Render assumptions, warnings, and limitations.
 */
function renderAssumptions(assumptions, warnings, limitations) {
  assumptionsBody.innerHTML = '';

  assumptions.forEach(text => {
    const el = document.createElement('div');
    el.className = 'assumption-item';
    el.textContent = `ℹ ${text}`;
    assumptionsBody.appendChild(el);
  });

  warnings.forEach(text => {
    const el = document.createElement('div');
    el.className = 'warning-item';
    el.textContent = `⚠ ${text}`;
    assumptionsBody.appendChild(el);
  });

  limitations.forEach(text => {
    const el = document.createElement('div');
    el.className = 'limitation-item';
    el.textContent = `⛔ ${text}`;
    assumptionsBody.appendChild(el);
  });
}

/**
 * Render optimization suggestion cards.
 */
function renderOptimizations(optimizations) {
  optimizationsList.innerHTML = '';

  if (!optimizations.length) {
    const el = document.createElement('div');
    el.className = 'opt-no-results';
    el.textContent = 'No specific optimization suggestions generated for this code.';
    optimizationsList.appendChild(el);
    return;
  }

  const confColors = { High: 'conf-High', Medium: 'conf-Medium', Low: 'conf-Low' };

  optimizations.forEach(opt => {
    const card = document.createElement('div');
    card.className = 'optimization-card';

    const header = document.createElement('div');
    header.className = 'opt-header';

    const title = document.createElement('div');
    title.className = 'opt-title';
    title.textContent = opt.title || 'Optimization';

    const confBadge = document.createElement('span');
    confBadge.className = `opt-conf ${confColors[opt.confidence] || 'conf-Low'}`;
    confBadge.textContent = opt.confidence || 'Low';

    header.appendChild(title);
    header.appendChild(confBadge);

    const body = document.createElement('div');
    body.className = 'opt-body';

    if (opt.issue_description) {
      const issue = document.createElement('p');
      issue.textContent = opt.issue_description;
      body.appendChild(issue);
    }
    if (opt.proposed_change) {
      const proposal = document.createElement('p');
      proposal.style.marginTop = '0.4rem';
      proposal.style.color = 'var(--purple-soft)';
      proposal.textContent = `→ ${opt.proposed_change}`;
      body.appendChild(proposal);
    }
    if (opt.trade_offs) {
      const tradeoff = document.createElement('p');
      tradeoff.style.marginTop = '0.3rem';
      tradeoff.style.fontSize = '0.74rem';
      tradeoff.style.color = 'var(--text-muted)';
      tradeoff.textContent = `Trade-offs: ${opt.trade_offs}`;
      body.appendChild(tradeoff);
    }

    // Impact badges
    if (opt.time_complexity_impact || opt.space_complexity_impact) {
      const impacts = document.createElement('div');
      impacts.className = 'opt-impact';
      if (opt.time_complexity_impact) {
        const t = document.createElement('span');
        t.className = 'opt-impact-item';
        t.textContent = `⏱ ${opt.time_complexity_impact}`;
        impacts.appendChild(t);
      }
      if (opt.space_complexity_impact) {
        const s = document.createElement('span');
        s.className = 'opt-impact-item';
        s.textContent = `🗄 ${opt.space_complexity_impact}`;
        impacts.appendChild(s);
      }
      body.appendChild(impacts);
    }

    card.appendChild(header);
    card.appendChild(body);
    optimizationsList.appendChild(card);
  });
}
