/**
 * api.js — Backend communication layer
 * All API calls are made here; no API keys are ever in this file.
 */
'use strict';

const API_BASE = '/api';

/**
 * Fetch the health status from the backend.
 * @returns {Promise<object>}
 */
async function apiHealth() {
  const res = await fetch(`${API_BASE}/health`);
  if (!res.ok) throw new Error(`Health check failed: ${res.status}`);
  return res.json();
}

/**
 * Fetch the list of supported languages.
 * @returns {Promise<object>}
 */
async function apiLanguages() {
  const res = await fetch(`${API_BASE}/languages`);
  if (!res.ok) throw new Error(`Languages fetch failed: ${res.status}`);
  return res.json();
}

/**
 * Detect the programming language of a code snippet.
 * @param {string} code
 * @param {string|null} filename
 * @returns {Promise<object>}
 */
async function apiDetectLanguage(code, filename = null) {
  const body = { code };
  if (filename) body.filename = filename;
  const res = await fetch(`${API_BASE}/detect-language`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Detection failed: ${res.status}`);
  }
  return res.json();
}

/**
 * Analyze source code for complexity.
 * @param {string} code
 * @param {string|null} language - Language identifier override
 * @param {string|null} filename
 * @param {object} settings - Analysis settings
 * @returns {Promise<object>}
 */
async function apiAnalyze(code, language = null, filename = null, settings = {}) {
  const body = { code, settings: { include_optimizations: true, include_visualization: true, ...settings } };
  if (language) body.language = language;
  if (filename) body.filename = filename;

  const res = await fetch(`${API_BASE}/analyze`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Analysis failed: ${res.status}`);
  }
  return res.json();
}

/**
 * Analyze an uploaded file for complexity.
 * @param {File} file
 * @param {string|null} language
 * @returns {Promise<object>}
 */
async function apiAnalyzeFile(file, language = null) {
  const formData = new FormData();
  formData.append('file', file);
  if (language) formData.append('language', language);

  const res = await fetch(`${API_BASE}/analyze-file`, {
    method: 'POST',
    body: formData,
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `File analysis failed: ${res.status}`);
  }
  return res.json();
}

/**
 * Fetch configuration status.
 * @returns {Promise<object>}
 */
async function apiConfigStatus() {
  const res = await fetch(`${API_BASE}/config/status`);
  if (!res.ok) throw new Error(`Config status failed: ${res.status}`);
  return res.json();
}
