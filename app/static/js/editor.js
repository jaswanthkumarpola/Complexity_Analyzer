/**
 * editor.js — Code editor with line numbers, examples, file upload
 */
'use strict';

// ===== EXAMPLE CODE LIBRARY =====
const EXAMPLES = {
  constant: {
    lang: 'python',
    code: `def get_first_element(arr):
    """
    Return the first element of a non-empty array.
    Time Complexity: O(1) — single element access regardless of array size.
    Space Complexity: O(1) — no additional storage allocated.
    """
    return arr[0]


# Test
data = [10, 20, 30, 40, 50]
print(get_first_element(data))  # Output: 10
`,
  },

  linear: {
    lang: 'python',
    code: `def array_sum(arr):
    """
    Compute the sum of all elements in an array.
    Time Complexity: O(n) — single pass through n elements.
    Space Complexity: O(1) — only a constant number of variables.
    """
    total = 0
    for element in arr:
        total += element
    return total


def find_max(arr):
    """
    Find the maximum element in an unsorted array.
    Time Complexity: O(n) — must inspect every element.
    Space Complexity: O(1) — only stores the current maximum.
    """
    if not arr:
        raise ValueError("Array must not be empty")
    maximum = arr[0]
    for element in arr[1:]:
        if element > maximum:
            maximum = element
    return maximum


# Test
data = [3, 1, 4, 1, 5, 9, 2, 6, 5, 3]
print(f"Sum: {array_sum(data)}, Max: {find_max(data)}")
`,
  },

  quadratic: {
    lang: 'python',
    code: `def bubble_sort(arr):
    """
    Sort an array using the Bubble Sort algorithm.
    Time Complexity: O(n^2) worst/average case — nested loops each over n.
    Time Complexity: O(n) best case — already sorted array with early exit.
    Space Complexity: O(1) — sorts in-place, constant auxiliary space.
    """
    n = len(arr)
    for i in range(n):
        swapped = False
        for j in range(0, n - i - 1):
            if arr[j] > arr[j + 1]:
                arr[j], arr[j + 1] = arr[j + 1], arr[j]
                swapped = True
        if not swapped:
            break  # Early exit if already sorted


# Test
data = [64, 34, 25, 12, 22, 11, 90]
bubble_sort(data)
print(f"Sorted: {data}")
`,
  },

  logarithmic: {
    lang: 'python',
    code: `def binary_search(arr, target):
    """
    Search for a target in a sorted array using binary search.
    Time Complexity: O(log n) — search space halves each iteration.
    Space Complexity: O(1) — iterative implementation, no recursion stack.
    Assumption: arr is sorted in ascending order.
    """
    left, right = 0, len(arr) - 1

    while left <= right:
        mid = left + (right - left) // 2  # Avoids integer overflow
        if arr[mid] == target:
            return mid          # Found
        elif arr[mid] < target:
            left = mid + 1      # Target in right half
        else:
            right = mid - 1     # Target in left half

    return -1                   # Not found


# Test
sorted_array = [1, 3, 5, 7, 9, 11, 13, 15, 17, 19]
print(binary_search(sorted_array, 7))   # Output: 3
print(binary_search(sorted_array, 10))  # Output: -1
`,
  },

  linearithmic: {
    lang: 'python',
    code: `def merge_sort(arr):
    """
    Sort an array using Merge Sort (divide and conquer).
    Time Complexity: O(n log n) — divides log n times, merges O(n) each level.
    Space Complexity: O(n) — auxiliary arrays created during merge steps.
    """
    if len(arr) <= 1:
        return arr

    mid = len(arr) // 2
    left = merge_sort(arr[:mid])
    right = merge_sort(arr[mid:])
    return merge(left, right)


def merge(left, right):
    """Merge two sorted arrays into one sorted array."""
    result = []
    i = j = 0
    while i < len(left) and j < len(right):
        if left[i] <= right[j]:
            result.append(left[i])
            i += 1
        else:
            result.append(right[j])
            j += 1
    result.extend(left[i:])
    result.extend(right[j:])
    return result


# Test
data = [38, 27, 43, 3, 9, 82, 10]
sorted_data = merge_sort(data)
print(f"Sorted: {sorted_data}")
`,
  },

  exponential: {
    lang: 'python',
    code: `def fibonacci_naive(n):
    """
    Compute the nth Fibonacci number using naive recursion.
    Time Complexity: O(2^n) — two recursive calls per non-base case.
    Space Complexity: O(n) — maximum recursion stack depth is n.
    WARNING: Extremely slow for n > 35. Do not use in production.
    """
    if n <= 1:
        return n
    return fibonacci_naive(n - 1) + fibonacci_naive(n - 2)


# Demonstrate growth — notice how much slower each step gets
for i in range(1, 15):
    result = fibonacci_naive(i)
    print(f"fib({i:2d}) = {result}")
`,
  },

  memoized: {
    lang: 'python',
    code: `def fibonacci_memoized(n, memo=None):
    """
    Compute the nth Fibonacci number with memoization.
    Time Complexity: O(n) — each unique subproblem solved exactly once.
    Space Complexity: O(n) — memo dictionary stores n values plus call stack.
    Compare with naive recursive O(2^n) — memoization is dramatically faster.
    """
    if memo is None:
        memo = {}
    if n in memo:
        return memo[n]
    if n <= 1:
        return n
    memo[n] = fibonacci_memoized(n - 1, memo) + fibonacci_memoized(n - 2, memo)
    return memo[n]


def fibonacci_iterative(n):
    """
    Iterative Fibonacci for comparison.
    Time Complexity: O(n)  Space Complexity: O(1)
    """
    if n <= 1:
        return n
    a, b = 0, 1
    for _ in range(2, n + 1):
        a, b = b, a + b
    return b


# Both are O(n) but iterative uses O(1) space vs O(n) for memoized
for i in [5, 10, 20, 30, 40]:
    print(f"fib({i}) = {fibonacci_memoized(i)} (memo)  {fibonacci_iterative(i)} (iter)")
`,
  },
};

// ===== EDITOR STATE =====
let currentUploadedFile = null;
let isExamplesMenuOpen = false;

// ===== DOM REFERENCES =====
const codeEditor = document.getElementById('code-editor');
const lineNumbers = document.getElementById('line-numbers');
const charCount = document.getElementById('char-count');
const langSelect = document.getElementById('lang-select');
const detectBadge = document.getElementById('detect-badge');
const btnExample = document.getElementById('btn-example');
const btnUpload = document.getElementById('btn-upload');
const btnClear = document.getElementById('btn-clear');
const btnClearFile = document.getElementById('btn-clear-file');
const fileInput = document.getElementById('file-input');
const uploadInfo = document.getElementById('upload-info');
const uploadFilename = document.getElementById('upload-filename');
const examplesMenu = document.getElementById('examples-menu');

// ===== LINE NUMBERS =====
function updateLineNumbers() {
  const lines = codeEditor.value.split('\n');
  lineNumbers.textContent = lines.map((_, i) => i + 1).join('\n');
}

function updateCharCount() {
  const len = codeEditor.value.length;
  charCount.textContent = `${len.toLocaleString()} chars`;
}

// ===== LANGUAGE SELECT POPULATION =====
async function populateLanguageSelect(languages) {
  // Clear all options except auto-detect
  while (langSelect.options.length > 1) langSelect.remove(1);

  // Group: parser-available first, then others
  const withParser = languages.filter(l => l.parser_available);
  const withStatic = languages.filter(l => !l.parser_available && l.static_analysis && l.identifier !== 'generic');
  const other = languages.filter(l => l.identifier === 'generic');

  function addGroup(label, langs) {
    if (!langs.length) return;
    const optgroup = document.createElement('optgroup');
    optgroup.label = label;
    langs.forEach(lang => {
      const opt = document.createElement('option');
      opt.value = lang.identifier;
      opt.textContent = lang.display_name;
      optgroup.appendChild(opt);
    });
    langSelect.appendChild(optgroup);
  }

  addGroup('Full Parser Support', withParser);
  addGroup('Heuristic Analysis', withStatic);
  addGroup('Other', other);
}

// ===== DETECTED LANGUAGE BADGE =====
function showDetectedLanguage(lang, method, confidence) {
  if (method === 'user_selected') {
    detectBadge.classList.add('hidden');
    return;
  }
  detectBadge.textContent = `${lang} detected (${confidence})`;
  detectBadge.classList.remove('hidden');
}

// ===== EXAMPLES =====
function toggleExamplesMenu(e) {
  e.stopPropagation();
  isExamplesMenuOpen = !isExamplesMenuOpen;
  examplesMenu.classList.toggle('hidden', !isExamplesMenuOpen);
}

function closeExamplesMenu() {
  isExamplesMenuOpen = false;
  examplesMenu.classList.add('hidden');
}

function loadExample(exampleKey) {
  const example = EXAMPLES[exampleKey];
  if (!example) return;

  codeEditor.value = example.code;
  // Set language
  const opts = langSelect.options;
  for (let i = 0; i < opts.length; i++) {
    if (opts[i].value === example.lang) {
      langSelect.selectedIndex = i;
      break;
    }
  }
  clearUpload();
  updateLineNumbers();
  updateCharCount();
  closeExamplesMenu();
  detectBadge.classList.add('hidden');

  // Dispatch change event so app.js can react
  codeEditor.dispatchEvent(new Event('change'));
}

// ===== FILE UPLOAD =====
function handleFileSelect(file) {
  if (!file) return;
  const MAX_SIZE = 512 * 1024; // 512 KB client-side guard
  if (file.size > MAX_SIZE) {
    alert(`File too large. Maximum size is 512 KB. Your file is ${(file.size / 1024).toFixed(1)} KB.`);
    fileInput.value = '';
    return;
  }

  const reader = new FileReader();
  reader.onload = (e) => {
    codeEditor.value = e.target.result;
    currentUploadedFile = file;
    uploadFilename.textContent = file.name;
    uploadInfo.classList.remove('hidden');
    updateLineNumbers();
    updateCharCount();
    codeEditor.dispatchEvent(new Event('change'));

    // Try to set language from extension
    const ext = file.name.split('.').pop()?.toLowerCase();
    if (ext) {
      const opts = langSelect.options;
      // Do not auto-select; let backend detect from filename
    }
  };
  reader.readAsText(file);
}

function clearUpload() {
  currentUploadedFile = null;
  fileInput.value = '';
  uploadInfo.classList.add('hidden');
  uploadFilename.textContent = '';
}

// ===== EDITOR EVENTS =====
codeEditor.addEventListener('input', () => {
  updateLineNumbers();
  updateCharCount();
});

codeEditor.addEventListener('scroll', () => {
  lineNumbers.scrollTop = codeEditor.scrollTop;
});

// Tab key support
codeEditor.addEventListener('keydown', (e) => {
  if (e.key === 'Tab') {
    e.preventDefault();
    const start = codeEditor.selectionStart;
    const end = codeEditor.selectionEnd;
    codeEditor.value = codeEditor.value.substring(0, start) + '  ' + codeEditor.value.substring(end);
    codeEditor.selectionStart = codeEditor.selectionEnd = start + 2;
    updateLineNumbers();
  }
});

btnExample.addEventListener('click', toggleExamplesMenu);

document.addEventListener('click', (e) => {
  if (!examplesMenu.classList.contains('hidden') && !examplesMenu.contains(e.target) && e.target !== btnExample) {
    closeExamplesMenu();
  }
});

examplesMenu.querySelectorAll('.example-item').forEach(item => {
  item.addEventListener('click', () => loadExample(item.dataset.example));
});

btnUpload.addEventListener('click', () => fileInput.click());

fileInput.addEventListener('change', (e) => {
  if (e.target.files?.[0]) handleFileSelect(e.target.files[0]);
});

// Drag & drop onto the editor area
codeEditor.addEventListener('dragover', (e) => { e.preventDefault(); codeEditor.style.borderColor = 'var(--border-focus)'; });
codeEditor.addEventListener('dragleave', () => { codeEditor.style.borderColor = ''; });
codeEditor.addEventListener('drop', (e) => {
  e.preventDefault();
  codeEditor.style.borderColor = '';
  const file = e.dataTransfer?.files?.[0];
  if (file) handleFileSelect(file);
});

btnClear.addEventListener('click', () => {
  codeEditor.value = '';
  clearUpload();
  updateLineNumbers();
  updateCharCount();
  detectBadge.classList.add('hidden');
  codeEditor.dispatchEvent(new Event('change'));
});

btnClearFile.addEventListener('click', () => {
  codeEditor.value = '';
  clearUpload();
  updateLineNumbers();
  updateCharCount();
});

// Initialize
updateLineNumbers();
updateCharCount();
