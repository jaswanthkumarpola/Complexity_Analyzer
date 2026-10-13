"""
Strict validation of a manually selected language against the submitted code.

When the user picks a language explicitly (auto-detect OFF), the pasted code
must actually look like that language. Otherwise the request is rejected with
HTTP 422 before any analysis or AI call is made.
"""
from __future__ import annotations

import ast
import re
from typing import Dict, List, Optional, Tuple

from fastapi import HTTPException, status

from app.core.language_registry import get_language

# Only the first N characters are scanned for signatures (speed + ReDoS safety).
_SCAN_LIMIT = 20_000

_M = re.MULTILINE

# (regex, weight) — weight reflects how exclusive the pattern is to the language.
_RAW_SIGNATURES: Dict[str, List[Tuple[str, int]]] = {
    "python": [
        (r"^[ \t]*def\s+\w+\s*\(.*\)\s*(->\s*[^:]+)?:\s*(#.*)?$", 4),
        (r"^[ \t]*class\s+\w+\s*(\(.*\))?\s*:\s*(#.*)?$", 3),
        (r"^[ \t]*from\s+[\w.]+\s+import\s+", 3),
        (r"^[ \t]*import\s+[\w.]+(\s+as\s+\w+)?\s*$", 1),
        (r"^[ \t]*(elif\s.+|else|try|finally|except(\s.+)?)\s*:\s*(#.*)?$", 3),
        (r"^[ \t]*for\s+[\w, ()]+\s+in\s+.+:\s*(#.*)?$", 3),
        (r"^[ \t]*(if|while|with)\s+[^{;]+:\s*(#.*)?$", 2),
        (r"__name__\s*==\s*['\"]__main__['\"]", 3),
        (r"\b(range|len|enumerate|isinstance)\s*\(", 1),
        (r"\bself\b", 1),
        (r"\b(True|False|None)\b", 1),
    ],
    "javascript": [
        (r"\bconsole\.(log|error|warn|info)\s*\(", 3),
        (r"\bconst\s+[\w$]+\s*=", 2),
        (r"\blet\s+[\w$]+\s*(=|;)", 1),
        (r"\bvar\s+[\w$]+\s*=", 1),
        (r"\bfunction\s*[\w$]*\s*\(", 2),
        (r"\bfor\s*\(\s*(let|const)\s+", 3),
        (r"===|!==", 2),
        (r"\b(module\.exports|require\s*\(\s*['\"])", 3),
        (r"^[ \t]*export\s+(default|const|function|class|async)\b", 2),
        (r"^[ \t]*import\s+.+\s+from\s+['\"]", 2),
        (r"\b(document|window)\.\w+", 2),
        (r"\bundefined\b", 2),
        (r"=>", 1),
        (r"\b(async\s+function|new\s+Promise|\.then\s*\()", 2),
    ],
    # TypeScript-ONLY constructs (anything not valid plain JavaScript)
    "typescript": [
        (r":\s*(string|number|boolean|any|unknown|never|void)\b(\[\])?\s*([,;)=>{|\]]|$)", 3),
        (r"^[ \t]*export\s+(declare\s+)?interface\s+\w+", 3),
        (r"^[ \t]*interface\s+\w+(<[^>]*>)?\s*(extends\s+[\w, <>]+)?\s*\{", 1),
        (r"^[ \t]*(export\s+)?type\s+\w+(<[^>]*>)?\s*=", 3),
        (r"\bas\s+(string|number|any|unknown|const)\b", 2),
        (r"\)\s*:\s*Promise<", 3),
        (r"\b(readonly|private|public|protected)\s+\w+\s*:", 2),
    ],
    "java": [
        (r"\bSystem\.(out|err)\.print", 4),
        (r"\bimport\s+javax?\.", 4),
        (r"\bpublic\s+static\s+void\s+main\s*\(\s*String(\s*\[\s*\]|\.\.\.)\s*\w+\s*\)", 4),
        (r"\b(ArrayList|HashMap|HashSet|LinkedList)\s*<", 2),
        (r"@Override\b", 3),
        (r"\bthrows\s+\w+", 3),
        (r"\bnew\s+Scanner\s*\(|\bSystem\.in\b", 3),
        (r"^[ \t]*package\s+[\w.]+\s*;", 2),
        (r"\b(public|private|protected)\s+(static\s+)?(String|boolean)\b", 2),
        (r"\bfinal\s+(int|String|double|long)\b", 2),
    ],
    "csharp": [
        (r"^[ \t]*using\s+System(\.\w+)*\s*;", 4),
        (r"\bConsole\.(WriteLine|Write|ReadLine)\s*\(", 4),
        (r"\bstatic\s+(void|int|async\s+Task)\s+Main\s*\(", 4),
        (r"\bforeach\s*\(\s*(var|\w+)\s+\w+\s+in\s", 3),
        (r"\bget;\s*set;", 3),
        (r"\bpublic\s+(static\s+)?(async\s+)?(Task|void|int|string|bool)\s+[A-Z]\w*\s*\(", 2),
        (r"\bnamespace\s+[\w.]+\s*(\{|;|$)", 1),
    ],
    # C++-ONLY constructs (anything not valid plain C)
    "cpp": [
        (r"#include\s*<(iostream|vector|string|algorithm|map|set|queue|stack|cmath|"
         r"bits/stdc\+\+\.h|unordered_map|unordered_set|climits|cstdio|cstdlib|cstring|"
         r"numeric|utility|functional|memory)>", 4),
        (r"\bstd::\w+", 3),
        (r"\busing\s+namespace\s+std\b", 4),
        (r"\b(cout|cin|cerr)\s*(<<|>>)", 3),
        (r"\btemplate\s*<", 3),
        (r"\b(vector|map|set|unordered_map|pair|queue|stack)\s*<[^>]+>\s+\w+", 3),
        (r"\bnullptr\b", 3),
    ],
    "c": [
        (r"#include\s*<(stdio|stdlib|string|math|ctype|limits|stdbool|stdint|time|assert)\.h>", 4),
        (r"\b(printf|scanf|malloc|calloc)\s*\(", 2),
        (r"\bint\s+main\s*\(", 2),
        (r"\btypedef\s+struct\b", 3),
    ],
    "go": [
        (r"^[ \t]*package\s+\w+\s*$", 3),
        (r"^[ \t]*func\s+(\(\w+\s+\*?\w+\)\s*)?\w+\s*\(", 4),
        (r"\bfmt\.(Print|Println|Printf|Sprintf|Errorf)", 4),
        (r":=", 2),
        (r"^[ \t]*import\s+\(", 3),
        (r"\bdefer\s+\w+", 2),
    ],
    "rust": [
        (r"\bfn\s+\w+\s*(<[^>]*>)?\s*\(", 4),
        (r"\blet\s+mut\s+\w+", 4),
        (r"\b(println|print|format|vec)!\s*[(\[]", 4),
        (r"^[ \t]*use\s+(std|crate|super)::", 4),
        (r"\bimpl\s+(<[^>]*>\s*)?\w+|\bpub\s+(fn|struct|enum)\b", 3),
        (r"&mut\s+\w+", 3),
        (r"\bVec<", 2),
    ],
    "ruby": [
        (r"^[ \t]*def\s+\w+[?!]?(\s*\(.*\))?\s*$", 3),
        (r"^[ \t]*end\s*$", 2),
        (r"\b(puts\s+[\"'\w]|require_relative|attr_accessor|attr_reader)\b", 3),
        (r"\bdo\s*\|\w+(,\s*\w+)*\|", 4),
        (r"^[ \t]*(elsif|unless)\b", 3),
        (r"^[ \t]*class\s+[A-Z]\w*(\s*<\s*\w+)?\s*$", 3),
    ],
    "php": [
        (r"<\?php", 5),
        (r"\$\w+\s*=", 2),
        (r"\$\w+->\w+", 3),
        (r"\bforeach\s*\(\s*\$\w+\s+as\s", 4),
        (r"\bfunction\s+\w+\s*\(\s*\$\w+", 3),
        (r"\barray\s*\(", 2),
        (r"\becho\b", 1),
    ],
    "kotlin": [
        (r"\bfun\s+\w+\s*(<[^>]*>)?\s*\(", 4),
        (r"\bval\s+\w+\s*(:\s*[\w<>?]+)?\s*=", 2),
        (r"\bprintln\s*\(", 1),
        (r"^[ \t]*(data|sealed|open)\s+class\b|\bcompanion\s+object\b|\blateinit\b|\bsuspend\s+fun\b", 4),
    ],
    "swift": [
        (r"\bfunc\s+\w+\s*(<[^>]*>)?\s*\([^)]*:\s*\w+", 4),
        (r"\bfunc\s+\w+\s*(<[^>]*>)?\s*\(.*\)\s*->", 3),
        (r"\bimport\s+(Foundation|UIKit|SwiftUI)\b", 4),
        (r"\b(guard\s+let|if\s+let)\b", 3),
    ],
}

_SIGNATURES: Dict[str, List[Tuple["re.Pattern[str]", int]]] = {
    lang: [(re.compile(rx, _M), w) for rx, w in sigs]
    for lang, sigs in _RAW_SIGNATURES.items()
}

# Selecting key X also legitimately accepts code written in the listed languages.
_COMPATIBLE: Dict[str, set] = {
    "typescript": {"javascript"},
    "cpp": {"c"},
    "objc": {"c"},
}

# Selecting key X must reject code that uses strict-superset-only features of Y.
_STRICT_SUPERSET: Dict[str, str] = {
    "javascript": "typescript",
    "c": "cpp",
}

# Cheap structural hints that code is brace/semicolon style, i.e. not Python.
_C_STYLE_RE = re.compile(
    r"(;[ \t]*$)|(\)[ \t]*\{[ \t]*$)|(^[ \t]*//)|(/\*)|(^[ \t]*#include\b)", _M
)


def _score_all(code: str) -> Dict[str, int]:
    sample = code[:_SCAN_LIMIT]
    scores: Dict[str, int] = {}
    for lang, sigs in _SIGNATURES.items():
        total = sum(w for rx, w in sigs if rx.search(sample))
        if total:
            scores[lang] = total
    return scores


def _python_syntax_ok(code: str) -> bool:
    try:
        ast.parse(code)
        return True
    except SyntaxError:
        return False
    except Exception:  # null bytes, recursion limits, etc. — not a language signal
        return True


def _display(identifier: str) -> str:
    lang = get_language(identifier)
    return lang.display_name if lang else identifier


def _mismatch(selected: str, detected: Optional[str]) -> HTTPException:
    sel_name = _display(selected)
    if detected:
        det_name = _display(detected)
        detail = (
            f"Language mismatch: you selected {sel_name}, but the submitted code "
            f"looks like {det_name}. Select {det_name} (or switch to Auto-detect) "
            f"and try again."
        )
    else:
        detail = (
            f"Language mismatch: you selected {sel_name}, but the submitted code "
            f"does not look like valid {sel_name}. Select the correct language "
            f"(or switch to Auto-detect) and try again."
        )
    return HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=detail)


def validate_language_selection(code: str, selected: Optional[str]) -> None:
    """
    Enforce a manual language selection.

    - Empty / None / "auto"  -> auto-detect mode, nothing to enforce.
    - Unknown identifier      -> HTTP 422 (never silently ignored).
    - "generic"               -> nothing to enforce.
    - Code that clearly belongs to another language -> HTTP 422.
    """
    selected_id = (selected or "").strip().lower()
    if selected_id in ("", "auto", "auto-detect", "autodetect"):
        return

    if get_language(selected_id) is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Unsupported language '{selected}'. Choose a language from the list or use Auto-detect.",
        )
    if selected_id == "generic":
        return

    scores = _score_all(code)
    sel_score = scores.get(selected_id, 0)
    compatible = _COMPATIBLE.get(selected_id, set())
    others = {
        lang: s for lang, s in scores.items()
        if lang != selected_id and lang not in compatible
    }
    best_lang: Optional[str] = max(others, key=lambda k: others[k]) if others else None
    best_score = others[best_lang] if best_lang else 0

    # Python: the AST parser is the definitive judge.
    if selected_id == "python" and not _python_syntax_ok(code):
        if best_score >= 2 or _C_STYLE_RE.search(code[:_SCAN_LIMIT]):
            raise _mismatch("python", best_lang if best_score >= 1 else None)
        return  # genuine Python typo: let the pipeline report the syntax error

    # Strict supersets (TypeScript-only syntax in "JavaScript", C++-only in "C").
    superset = _STRICT_SUPERSET.get(selected_id)
    if superset and scores.get(superset, 0) >= 3:
        raise _mismatch(selected_id, superset)

    # General rule.
    threshold = 3 if selected_id in _SIGNATURES else 4
    if best_lang and best_score >= threshold and best_score > sel_score:
        raise _mismatch(selected_id, best_lang)
    if best_lang and selected_id in _SIGNATURES and sel_score == 0 and best_score >= 2:
        raise _mismatch(selected_id, best_lang)