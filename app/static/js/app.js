/**
 * app.js — Main application controller
 * Wires editor, API, and results together.
 */
'use strict';

// DOM references
const btnAnalyze = document.getElementById('btn-analyze');
const analyzeLabel = document.getElementById('analyze-label');
const btnSpinner = document.getElementById('btn-spinner');
const analyzeIcon = document.getElementById('analyze-icon');
const btnRetry = document.getElementById('btn-retry');
const statusBadge = document.getElementById('status-badge');
const statusDot = document.getElementById('status-dot');
const statusLabel = document.getElementById('status-label');
const aiNotice = document.getElementById('ai-notice');
const aiNoticeText = document.getElementById('ai-notice-text');
const footerVersion = document.getElementById('footer-version');

let isAnalyzing = false;
let lastCode = '';
let lastLanguage = null;

// ===== STARTUP =====
async function initialize() {
  await Promise.all([checkHealth(), loadLanguages()]);
}

async function checkHealth() {
  try {
    const health = await apiHealth();
    const config = await apiConfigStatus();

    // Update status badge
    if (health.ai_provider_configured) {
      statusDot.className = 'status-dot ai';
      statusLabel.textContent = `AI: ${config.ai_model}`;
      aiNoticeText.textContent = `AI-assisted mode (${config.ai_provider} / ${config.ai_model})`;
    } else {
      statusDot.className = 'status-dot warn';
      statusLabel.textContent = 'Fallback mode';
      aiNoticeText.textContent = 'Fallback mode — static analysis only (no AI key configured)';
    }

    // Footer version
    if (footerVersion) footerVersion.textContent = `v${health.version}`;

  } catch (err) {
    statusDot.className = 'status-dot error';
    statusLabel.textContent = 'Backend offline';
    aiNoticeText.textContent = 'Cannot connect to backend server';
    console.error('Health check failed:', err);
  }
}

async function loadLanguages() {
  try {
    const data = await apiLanguages();
    if (data.languages) {
      await populateLanguageSelect(data.languages);
    }
  } catch (err) {
    console.warn('Could not load language list:', err);
  }
}

// ===== ANALYSIS FLOW =====
async function runAnalysis() {
  if (isAnalyzing) return;

  const code = codeEditor.value;
  if (!code.trim()) {
    shakeButton();
    codeEditor.focus();
    return;
  }

  // Prevent double-submit
  isAnalyzing = true;
  setAnalyzingState(true);
  showLoading();

  const selectedLang = langSelect.value || null;
  const filename = currentUploadedFile?.name || null;

  try {
    let result;

    if (currentUploadedFile && code === (await readFileAsText(currentUploadedFile))) {
      // Analyze as file upload
      result = await apiAnalyzeFile(currentUploadedFile, selectedLang);
    } else {
      // Analyze as text
      result = await apiAnalyze(code, selectedLang, filename);
    }

    lastCode = code;
    lastLanguage = selectedLang;

    renderResults(result);

    // Update detected language badge if auto-detected
    const lang = result.language;
    if (lang && (!selectedLang || selectedLang === '')) {
      showDetectedLanguage(lang.display_name, lang.detection_method, lang.detection_confidence);
    }

  } catch (err) {
    console.error('Analysis failed:', err);
    showError(err.message || 'Analysis failed. Please check the server and try again.');
  } finally {
    isAnalyzing = false;
    setAnalyzingState(false);
  }
}

function setAnalyzingState(analyzing) {
  btnAnalyze.disabled = analyzing;
  if (analyzing) {
    analyzeLabel.textContent = 'Analyzing…';
    analyzeIcon.classList.add('hidden');
    btnSpinner.classList.remove('hidden');
  } else {
    analyzeLabel.textContent = 'Analyze Code';
    analyzeIcon.classList.remove('hidden');
    btnSpinner.classList.add('hidden');
  }
}

function shakeButton() {
  btnAnalyze.style.animation = 'none';
  btnAnalyze.offsetHeight; // reflow
  btnAnalyze.style.animation = 'shake 0.4s ease';
  setTimeout(() => { btnAnalyze.style.animation = ''; }, 400);
}

// Inject shake animation
const shakeStyle = document.createElement('style');
shakeStyle.textContent = `
@keyframes shake {
  0%, 100% { transform: translateX(0); }
  20% { transform: translateX(-6px); }
  40% { transform: translateX(6px); }
  60% { transform: translateX(-4px); }
  80% { transform: translateX(4px); }
}
`;
document.head.appendChild(shakeStyle);

/**
 * Read a File object as text (returns a promise).
 */
async function readFileAsText(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = e => resolve(e.target.result);
    reader.onerror = reject;
    reader.readAsText(file);
  });
}

// ===== EVENT LISTENERS =====
btnAnalyze.addEventListener('click', runAnalysis);

// Keyboard shortcut: Ctrl+Enter or Cmd+Enter to analyze
document.addEventListener('keydown', (e) => {
  if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
    e.preventDefault();
    runAnalysis();
  }
});

btnRetry.addEventListener('click', () => {
  errorState.classList.add('hidden');
  emptyState.classList.remove('hidden');
});

// Clear results when code changes substantially
codeEditor.addEventListener('change', () => {
  // Only reset if there are visible results and code changed
  if (!resultsContent.classList.contains('hidden') && codeEditor.value !== lastCode) {
    // Don't auto-clear; let user decide. Just update char count.
  }
});

// ===== INIT =====
initialize().catch(console.error);
