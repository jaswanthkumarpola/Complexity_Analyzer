/**
 * chat.js — Floating chat assistant for the AI Complexity Analyzer.
 *
 * - Creates its own button, panel and styles (no HTML/CSS edits needed).
 * - Sends the conversation plus your code and the latest analysis to /api/chat.
 * - Hooks renderResults() to remember the latest analysis.
 * - All text is rendered with textContent / text nodes (never innerHTML with
 *   untrusted data); only **bold**, `inline code` and ``` code blocks are formatted.
 */
(function () {
  'use strict';

  const CHAT_ENDPOINT = '/api/chat';
  const REQUEST_TIMEOUT_MS = 60000;
  const MAX_INPUT_CHARS = 4000;

  const SUGGESTIONS_WITH_RESULT = [
    'Explain this result step by step',
    "Why isn't it faster?",
    'How can I optimize this?',
    'What is the worst case?',
  ];
  const SUGGESTIONS_GENERAL = [
    'What is Big-O notation?',
    'O(n log n) vs O(n²)?',
    'How do I use this tool?',
  ];

  // ---- state ---------------------------------------------------------------
  let lastAnalysis = null;   // compact summary of the latest result
  let analyzedCode = '';     // code that analysis was run on
  let history = [];          // [{role, content}]
  let pending = false;
  let isOpen = false;

  // ---- DOM refs (filled by build()) ----------------------------------------
  let fab, panel, messagesEl, suggestionsEl, inputEl, sendBtn, contextEl;

  // ---------------------------------------------------------------------------
  // Helpers
  // ---------------------------------------------------------------------------

  function el(tag, className, text) {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined) node.textContent = text;
    return node;
  }

  function editorCode() {
    const ed = document.getElementById('code-editor');
    return ed ? ed.value : '';
  }

  function summarize(result) {
    const tc = result.time_complexity || {};
    const sc = result.space_complexity || {};
    const cases = result.case_analysis || {};
    const lang = result.language || {};
    return {
      language: lang.display_name || lang.identifier || undefined,
      method: result.analysis_method || undefined,
      time_complexity: tc.expression || undefined,
      time_confidence: tc.confidence || undefined,
      space_complexity: sc.expression || undefined,
      space_confidence: sc.confidence || undefined,
      best_case: cases.best_case && cases.best_case.expression || undefined,
      average_case: cases.average_case && cases.average_case.expression || undefined,
      worst_case: cases.worst_case && cases.worst_case.expression || undefined,
      explanation: (result.explanation || '').slice(0, 3500) || undefined,
    };
  }

  // Remember the latest analysis by wrapping renderResults (defined in results.js)
  function hookResults() {
    if (typeof renderResults !== 'function' || renderResults.__chatHooked) return;
    const original = renderResults;
    const wrapped = function (result) {
      try {
        lastAnalysis = summarize(result || {});
        analyzedCode = editorCode();
        refreshContext();
        renderSuggestions();
      } catch (e) { /* never break the main UI */ }
      return original.apply(this, arguments);
    };
    wrapped.__chatHooked = true;
    renderResults = wrapped;
  }

  // ---------------------------------------------------------------------------
  // Styles
  // ---------------------------------------------------------------------------

  function injectStyles() {
    if (document.getElementById('chat-style')) return;
    const s = document.createElement('style');
    s.id = 'chat-style';
    s.textContent = `
      .chat-fab { position:fixed; right:1.25rem; bottom:1.25rem; z-index:1000; width:3.4rem; height:3.4rem; border-radius:50%; border:0; cursor:pointer;
        background:linear-gradient(135deg,var(--purple-primary,#8B5CF6),var(--purple-dark,#6D28D9)); color:#fff; display:flex; align-items:center; justify-content:center;
        box-shadow:var(--shadow-purple,0 0 20px rgba(139,92,246,.3)),var(--shadow-md,0 4px 16px rgba(0,0,0,.5)); transition:transform .18s ease; }
      .chat-fab:hover { transform:scale(1.06); }
      .chat-fab:focus-visible, .chat-icon-btn:focus-visible, .chat-chip:focus-visible, .chat-send:focus-visible { outline:2px solid var(--purple-soft,#C4B5FD); outline-offset:2px; }
      .chat-panel { position:fixed; right:1.25rem; bottom:5.2rem; z-index:1000; width:min(410px,calc(100vw - 2rem)); height:min(580px,calc(100vh - 7rem));
        display:flex; flex-direction:column; background:var(--bg-panel,#181824); border:1px solid var(--border,#2A293A); border-radius:var(--radius-lg,14px);
        box-shadow:var(--shadow-lg,0 8px 32px rgba(0,0,0,.6)); overflow:hidden; font-family:var(--font-sans,system-ui,sans-serif); }
      .chat-panel[hidden] { display:none; }
      .chat-head { display:flex; align-items:center; gap:.5rem; padding:.75rem .9rem; border-bottom:1px solid var(--border,#2A293A); background:var(--bg-secondary,#12121B); }
      .chat-head-text { flex:1; min-width:0; }
      .chat-title { margin:0; font-size:.92rem; font-weight:600; color:var(--text-primary,#F5F3FF); }
      .chat-context { margin:.1rem 0 0; font-size:.68rem; color:var(--text-muted,#6B6B80); white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
      .chat-icon-btn { background:transparent; border:0; color:var(--text-secondary,#A1A1B5); cursor:pointer; padding:.35rem .5rem; border-radius:var(--radius-sm,6px); font-size:.72rem; font-family:inherit; }
      .chat-icon-btn:hover { background:var(--bg-hover,#232336); color:var(--text-primary,#F5F3FF); }
      .chat-messages { flex:1; overflow-y:auto; padding:.9rem; display:flex; flex-direction:column; gap:.65rem; }
      .chat-msg { max-width:92%; padding:.55rem .75rem; border-radius:var(--radius-md,10px); font-size:.82rem; line-height:1.5; color:var(--text-primary,#F5F3FF); word-wrap:break-word; overflow-wrap:anywhere; }
      .chat-msg.user { align-self:flex-end; background:var(--purple-dark,#6D28D9); border-bottom-right-radius:2px; white-space:pre-wrap; }
      .chat-msg.assistant { align-self:flex-start; background:var(--bg-card,#1E1E2E); border:1px solid var(--border,#2A293A); border-bottom-left-radius:2px; }
      .chat-msg.error { align-self:flex-start; background:rgba(248,113,113,.12); border:1px solid rgba(248,113,113,.4); color:var(--red,#F87171); }
      .chat-msg p { margin:0 0 .5rem; white-space:pre-wrap; }
      .chat-msg p:last-child { margin-bottom:0; }
      .chat-inline { font-family:var(--font-mono,monospace); font-size:.78rem; background:var(--bg-active,#2A2940); padding:.08rem .3rem; border-radius:4px; color:var(--text-code,#E2E0FF); }
      .chat-code { margin:.45rem 0; padding:.6rem .7rem; background:var(--bg-main,#0B0B10); border:1px solid var(--border,#2A293A); border-radius:var(--radius-sm,6px); overflow-x:auto; }
      .chat-code code { font-family:var(--font-mono,monospace); font-size:.76rem; color:var(--text-code,#E2E0FF); white-space:pre; }
      .chat-typing { display:inline-flex; gap:.25rem; padding:.2rem 0; }
      .chat-typing span { width:.42rem; height:.42rem; border-radius:50%; background:var(--text-muted,#6B6B80); animation:chat-bounce 1s infinite ease-in-out; }
      .chat-typing span:nth-child(2) { animation-delay:.15s; } .chat-typing span:nth-child(3) { animation-delay:.3s; }
      @keyframes chat-bounce { 0%,80%,100% { opacity:.3; transform:translateY(0); } 40% { opacity:1; transform:translateY(-3px); } }
      @media (prefers-reduced-motion: reduce) { .chat-typing span { animation:none; opacity:.7; } .chat-fab { transition:none; } }
      .chat-suggestions { display:flex; flex-wrap:wrap; gap:.4rem; padding:0 .9rem .6rem; }
      .chat-chip { background:var(--purple-glow,rgba(139,92,246,.15)); color:var(--purple-soft,#C4B5FD); border:1px solid var(--border-hover,#3D3C52); border-radius:999px;
        padding:.3rem .7rem; font-size:.72rem; cursor:pointer; font-family:inherit; }
      .chat-chip:hover { background:var(--bg-active,#2A2940); }
      .chat-form { display:flex; align-items:flex-end; gap:.5rem; padding:.7rem .9rem .35rem; border-top:1px solid var(--border,#2A293A); }
      .chat-input { flex:1; resize:none; max-height:120px; min-height:2.3rem; padding:.5rem .65rem; background:var(--bg-main,#0B0B10); color:var(--text-primary,#F5F3FF);
        border:1px solid var(--border,#2A293A); border-radius:var(--radius-md,10px); font-family:inherit; font-size:.82rem; line-height:1.4; }
      .chat-input:focus { outline:none; border-color:var(--border-focus,#8B5CF6); }
      .chat-send { height:2.3rem; padding:0 .9rem; border:0; border-radius:var(--radius-md,10px); background:var(--purple-primary,#8B5CF6); color:#fff; font-weight:600; font-size:.78rem; cursor:pointer; font-family:inherit; }
      .chat-send:disabled { opacity:.5; cursor:not-allowed; }
      .chat-foot { margin:0; padding:.2rem .9rem .6rem; font-size:.64rem; color:var(--text-muted,#6B6B80); }
      @media (max-width:520px) { .chat-panel { right:.5rem; left:.5rem; width:auto; bottom:4.9rem; height:min(75vh,calc(100vh - 6rem)); } .chat-fab { right:.75rem; bottom:.75rem; } }
    `;
    document.head.appendChild(s);
  }

  // ---------------------------------------------------------------------------
  // Rendering messages (safe: text nodes only)
  // ---------------------------------------------------------------------------

  function appendInline(parent, text) {
    const re = /(`[^`\n]+`|\*\*[^*\n]+\*\*)/g;
    let last = 0;
    let m;
    while ((m = re.exec(text)) !== null) {
      if (m.index > last) parent.appendChild(document.createTextNode(text.slice(last, m.index)));
      const tok = m[0];
      if (tok.charAt(0) === '`') {
        parent.appendChild(el('code', 'chat-inline', tok.slice(1, -1)));
      } else {
        parent.appendChild(el('strong', '', tok.slice(2, -2)));
      }
      last = m.index + tok.length;
    }
    if (last < text.length) parent.appendChild(document.createTextNode(text.slice(last)));
  }

  function renderRich(container, text) {
    container.textContent = '';
    text.split('```').forEach((part, i) => {
      if (i % 2 === 1) {
        // fenced code block: drop an optional language tag on the first line
        let code = part;
        const nl = code.indexOf('\n');
        if (nl !== -1 && /^[\w+#.-]*$/.test(code.slice(0, nl).trim())) code = code.slice(nl + 1);
        const pre = el('pre', 'chat-code');
        pre.appendChild(el('code', '', code.replace(/\n$/, '')));
        container.appendChild(pre);
      } else {
        part.split(/\n{2,}/).forEach(block => {
          if (!block.trim()) return;
          const p = el('p');
          appendInline(p, block.replace(/^\n+|\n+$/g, ''));
          container.appendChild(p);
        });
      }
    });
  }

  function addMessage(role, text) {
    const msg = el('div', `chat-msg ${role}`);
    if (role === 'assistant') renderRich(msg, text);
    else msg.textContent = text;
    messagesEl.appendChild(msg);
    messagesEl.scrollTop = messagesEl.scrollHeight;
    return msg;
  }

  function addTyping() {
    const msg = el('div', 'chat-msg assistant');
    const dots = el('span', 'chat-typing');
    dots.setAttribute('aria-label', 'Assistant is typing');
    for (let i = 0; i < 3; i++) dots.appendChild(el('span'));
    msg.appendChild(dots);
    messagesEl.appendChild(msg);
    messagesEl.scrollTop = messagesEl.scrollHeight;
    return msg;
  }

  function renderWelcome() {
    const msg = el('div', 'chat-msg assistant');
    renderRich(msg, "Hi! I can explain your complexity results, walk through why code is O(n) or O(n²), and suggest optimizations. Paste code, click **Analyze Code**, then ask me anything.");
    messagesEl.appendChild(msg);
  }

  function renderSuggestions() {
    if (!suggestionsEl) return;
    suggestionsEl.textContent = '';
    if (history.length > 0) return;
    (lastAnalysis ? SUGGESTIONS_WITH_RESULT : SUGGESTIONS_GENERAL).forEach(text => {
      const chip = el('button', 'chat-chip', text);
      chip.type = 'button';
      chip.addEventListener('click', () => sendMessage(text));
      suggestionsEl.appendChild(chip);
    });
  }

  function refreshContext() {
    if (!contextEl) return;
    if (lastAnalysis && lastAnalysis.time_complexity) {
      contextEl.textContent = `Context: your code · ${lastAnalysis.time_complexity} time`;
    } else if (editorCode().trim()) {
      contextEl.textContent = 'Context: your code (not analyzed yet)';
    } else {
      contextEl.textContent = 'General questions about complexity';
    }
  }

  // ---------------------------------------------------------------------------
  // Sending
  // ---------------------------------------------------------------------------

  function setPending(value) {
    pending = value;
    sendBtn.disabled = value;
    inputEl.disabled = value;
  }

  async function sendMessage(rawText) {
    const text = (rawText || '').trim().slice(0, MAX_INPUT_CHARS);
    if (!text || pending) return;

    history.push({ role: 'user', content: text });
    addMessage('user', text);
    inputEl.value = '';
    autoGrow();
    renderSuggestions();
    setPending(true);
    const typing = addTyping();

    const body = { messages: history.slice(-12) };
    const code = lastAnalysis ? analyzedCode : editorCode();
    if (code && code.trim()) body.code = code;
    if (lastAnalysis) body.analysis = lastAnalysis;

    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);

    try {
      const res = await fetch(CHAT_ENDPOINT, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
        signal: controller.signal,
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        let detail = err.detail;
        if (Array.isArray(detail)) detail = 'The message could not be processed.';
        throw new Error(detail || `Chat failed (HTTP ${res.status})`);
      }
      const data = await res.json();
      typing.remove();
      history.push({ role: 'assistant', content: data.reply });
      addMessage('assistant', data.reply);
    } catch (e) {
      typing.remove();
      history.pop();          // drop the failed user message so a retry is clean
      inputEl.value = text;   // give the text back
      autoGrow();
      const msg = e.name === 'AbortError'
        ? 'The assistant took too long to answer. Please try again.'
        : (e.message || 'Something went wrong.');
      addMessage('error', msg);
    } finally {
      clearTimeout(timer);
      setPending(false);
      inputEl.focus();
    }
  }

  function clearChat() {
    if (pending) return;
    history = [];
    messagesEl.textContent = '';
    renderWelcome();
    renderSuggestions();
    refreshContext();
    inputEl.focus();
  }

  function autoGrow() {
    inputEl.style.height = 'auto';
    inputEl.style.height = `${Math.min(inputEl.scrollHeight, 120)}px`;
  }

  // ---------------------------------------------------------------------------
  // Open / close
  // ---------------------------------------------------------------------------

  function setOpen(open) {
    isOpen = open;
    panel.hidden = !open;
    fab.setAttribute('aria-expanded', String(open));
    fab.setAttribute('aria-label', open ? 'Close chat assistant' : 'Open chat assistant');
    if (open) {
      refreshContext();
      renderSuggestions();
      inputEl.focus();
      messagesEl.scrollTop = messagesEl.scrollHeight;
    } else {
      fab.focus();
    }
  }

  // ---------------------------------------------------------------------------
  // Build UI
  // ---------------------------------------------------------------------------

  function build() {
    injectStyles();

    fab = el('button', 'chat-fab');
    fab.type = 'button';
    fab.setAttribute('aria-label', 'Open chat assistant');
    fab.setAttribute('aria-expanded', 'false');
    fab.setAttribute('aria-controls', 'chat-panel');
    // static, trusted icon markup
    fab.innerHTML = '<svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M21 15a2 2 0 0 1-2 2H8l-5 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>';
    fab.addEventListener('click', () => setOpen(!isOpen));

    panel = el('section', 'chat-panel');
    panel.id = 'chat-panel';
    panel.hidden = true;
    panel.setAttribute('role', 'dialog');
    panel.setAttribute('aria-label', 'Complexity assistant chat');

    const head = el('div', 'chat-head');
    const headText = el('div', 'chat-head-text');
    headText.appendChild(el('h3', 'chat-title', 'Complexity Assistant'));
    contextEl = el('p', 'chat-context', '');
    headText.appendChild(contextEl);

    const newBtn = el('button', 'chat-icon-btn', 'New chat');
    newBtn.type = 'button';
    newBtn.addEventListener('click', clearChat);

    const closeBtn = el('button', 'chat-icon-btn', '✕');
    closeBtn.type = 'button';
    closeBtn.setAttribute('aria-label', 'Close chat');
    closeBtn.addEventListener('click', () => setOpen(false));

    head.appendChild(headText);
    head.appendChild(newBtn);
    head.appendChild(closeBtn);

    messagesEl = el('div', 'chat-messages');
    messagesEl.setAttribute('role', 'log');
    messagesEl.setAttribute('aria-live', 'polite');

    suggestionsEl = el('div', 'chat-suggestions');

    const form = el('form', 'chat-form');
    inputEl = el('textarea', 'chat-input');
    inputEl.rows = 1;
    inputEl.maxLength = MAX_INPUT_CHARS;
    inputEl.placeholder = 'Ask about your code or Big-O…';
    inputEl.setAttribute('aria-label', 'Message');
    inputEl.addEventListener('input', autoGrow);
    inputEl.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' && !e.shiftKey && !e.isComposing) {
        e.preventDefault();
        sendMessage(inputEl.value);
      }
    });

    sendBtn = el('button', 'chat-send', 'Send');
    sendBtn.type = 'submit';
    form.addEventListener('submit', (e) => {
      e.preventDefault();
      sendMessage(inputEl.value);
    });
    form.appendChild(inputEl);
    form.appendChild(sendBtn);

    const foot = el('p', 'chat-foot', 'AI can make mistakes. Your code and analysis are sent to the AI provider.');

    panel.appendChild(head);
    panel.appendChild(messagesEl);
    panel.appendChild(suggestionsEl);
    panel.appendChild(form);
    panel.appendChild(foot);

    document.body.appendChild(panel);
    document.body.appendChild(fab);

    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape' && isOpen) setOpen(false);
    });

    renderWelcome();
    renderSuggestions();
    refreshContext();
  }

  function init() {
    build();
    hookResults();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();