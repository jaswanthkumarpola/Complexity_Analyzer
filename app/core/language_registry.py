"""
Central language registry.
Defines all supported languages, their file extensions, parser availability,
and known limitations. Add new languages here without touching other modules.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class LanguageDefinition:
    """Complete description of a language's analysis capabilities."""
    identifier: str                  # Internal key, e.g. "python"
    display_name: str                # Human-readable, e.g. "Python"
    extensions: List[str]            # File extensions (without dot)
    pygments_lexer: Optional[str]    # Pygments lexer name for detection
    parser_available: bool = False   # Whether a structural parser is wired in
    static_analysis: bool = True     # Whether basic static analysis is supported
    known_limitations: List[str] = field(default_factory=list)
    keywords: List[str] = field(default_factory=list)   # Heuristic detection


# ---------------------------------------------------------------------------
# Registry definition — edit this list to add/remove languages
# ---------------------------------------------------------------------------

_DEFINITIONS: List[LanguageDefinition] = [
    LanguageDefinition(
        identifier="python",
        display_name="Python",
        extensions=["py", "pyw", "pyi"],
        pygments_lexer="Python3Lexer",
        parser_available=True,
        static_analysis=True,
        known_limitations=[],
        keywords=["def ", "import ", "range(", "len(", "elif ", "lambda ", "print(", ":"],
    ),
    LanguageDefinition(
        identifier="javascript",
        display_name="JavaScript",
        extensions=["js", "mjs", "cjs"],
        pygments_lexer="JavascriptLexer",
        parser_available=False,
        static_analysis=True,
        known_limitations=["Parser-based analysis not available; uses heuristics."],
        keywords=["console.log(", "const ", "let ", "var ", "function ", "=>", "require(", "module.exports"],
    ),
    LanguageDefinition(
        identifier="typescript",
        display_name="TypeScript",
        extensions=["ts", "tsx"],
        pygments_lexer="TypeScriptLexer",
        parser_available=False,
        static_analysis=True,
        known_limitations=["No TS parser; type annotations ignored in analysis."],
        keywords=["interface ", ": string", ": number", "type ", "enum "],
    ),
    LanguageDefinition(
        identifier="java",
        display_name="Java",
        extensions=["java"],
        pygments_lexer="JavaLexer",
        parser_available=False,
        static_analysis=True,
        known_limitations=["Heuristic analysis only; no AST parser."],
        keywords=["public class", "System.out", "void ", "import java."],
    ),
    LanguageDefinition(
        identifier="cpp",
        display_name="C++",
        extensions=["cpp", "cxx", "cc", "c++", "hpp", "hxx"],
        pygments_lexer="CppLexer",
        parser_available=False,
        static_analysis=True,
        known_limitations=["Heuristic analysis; templates not modeled."],
        keywords=["#include", "std::", "cout", "cin", "namespace"],
    ),
    LanguageDefinition(
        identifier="c",
        display_name="C",
        extensions=["c", "h"],
        pygments_lexer="CLexer",
        parser_available=False,
        static_analysis=True,
        known_limitations=["Heuristic analysis; pointer aliasing not modeled."],
        keywords=["#include", "printf(", "scanf(", "int main(", "malloc("],
    ),
    LanguageDefinition(
        identifier="csharp",
        display_name="C#",
        extensions=["cs"],
        pygments_lexer="CSharpLexer",
        parser_available=False,
        static_analysis=True,
        known_limitations=["Heuristic analysis only."],
        keywords=["using System", "namespace ", "Console.Write", "class "],
    ),
    LanguageDefinition(
        identifier="go",
        display_name="Go",
        extensions=["go"],
        pygments_lexer="GoLexer",
        parser_available=False,
        static_analysis=True,
        known_limitations=["Goroutine concurrency not modeled."],
        keywords=["package ", "func ", "fmt.Print", "import (", ":="],
    ),
    LanguageDefinition(
        identifier="rust",
        display_name="Rust",
        extensions=["rs"],
        pygments_lexer="RustLexer",
        parser_available=False,
        static_analysis=True,
        known_limitations=["Ownership/borrow semantics not modeled."],
        keywords=["fn main()", "let mut", "println!", "use std::"],
    ),
    LanguageDefinition(
        identifier="kotlin",
        display_name="Kotlin",
        extensions=["kt", "kts"],
        pygments_lexer="KotlinLexer",
        parser_available=False,
        static_analysis=True,
        known_limitations=["Coroutines not modeled."],
        keywords=["fun ", "println(", "val ", "var ", "data class"],
    ),
    LanguageDefinition(
        identifier="swift",
        display_name="Swift",
        extensions=["swift"],
        pygments_lexer="SwiftLexer",
        parser_available=False,
        static_analysis=True,
        known_limitations=["ARC memory model not reflected in space estimates."],
        keywords=["func ", "let ", "var ", "print(", "import Foundation"],
    ),
    LanguageDefinition(
        identifier="ruby",
        display_name="Ruby",
        extensions=["rb"],
        pygments_lexer="RubyLexer",
        parser_available=False,
        static_analysis=True,
        known_limitations=["Dynamic dispatch and blocks not fully modeled."],
        keywords=["puts ", "require '", "attr_accessor", "do |"  , ".each ", "end\n"],
    ),
    LanguageDefinition(
        identifier="php",
        display_name="PHP",
        extensions=["php"],
        pygments_lexer="PhpLexer",
        parser_available=False,
        static_analysis=True,
        known_limitations=["Superglobals and external HTTP not modeled."],
        keywords=["<?php", "echo ", "$_GET", "function "],
    ),
    LanguageDefinition(
        identifier="scala",
        display_name="Scala",
        extensions=["scala"],
        pygments_lexer="ScalaLexer",
        parser_available=False,
        static_analysis=True,
        known_limitations=["Functional idioms and lazy evaluation not fully modeled."],
        keywords=["object ", "val ", "case class", "println(", "extends ", "trait "],
    ),
    LanguageDefinition(
        identifier="r",
        display_name="R",
        extensions=["r", "R"],
        pygments_lexer="RLexer",
        parser_available=False,
        static_analysis=True,
        known_limitations=["Vectorized operations may have non-obvious complexity."],
        keywords=["library(", "function(", "<-", "print(", "ggplot("],
    ),
    LanguageDefinition(
        identifier="julia",
        display_name="Julia",
        extensions=["jl"],
        pygments_lexer="JuliaLexer",
        parser_available=False,
        static_analysis=True,
        known_limitations=["JIT compilation effects not modeled."],
        keywords=["function ", "println(", "using ", "module "],
    ),
    LanguageDefinition(
        identifier="dart",
        display_name="Dart",
        extensions=["dart"],
        pygments_lexer="DartLexer",
        parser_available=False,
        static_analysis=True,
        known_limitations=["Async/await and streams not modeled."],
        keywords=["void main()", "print(", "class ", "import 'dart:"],
    ),
    LanguageDefinition(
        identifier="lua",
        display_name="Lua",
        extensions=["lua"],
        pygments_lexer="LuaLexer",
        parser_available=False,
        static_analysis=True,
        known_limitations=["Metatables not modeled."],
        keywords=["function ", "print(", "local ", "require(", "end"],
    ),
    LanguageDefinition(
        identifier="perl",
        display_name="Perl",
        extensions=["pl", "pm"],
        pygments_lexer="PerlLexer",
        parser_available=False,
        static_analysis=True,
        known_limitations=["Regex-heavy code complexity not modeled."],
        keywords=["sub ", "print ", "my $", "use strict"],
    ),
    LanguageDefinition(
        identifier="haskell",
        display_name="Haskell",
        extensions=["hs", "lhs"],
        pygments_lexer="HaskellLexer",
        parser_available=False,
        static_analysis=True,
        known_limitations=["Lazy evaluation and monadic effects not modeled."],
        keywords=["module ", "import ", "main =", "where", "let "],
    ),
    LanguageDefinition(
        identifier="elixir",
        display_name="Elixir",
        extensions=["ex", "exs"],
        pygments_lexer="ElixirLexer",
        parser_available=False,
        static_analysis=True,
        known_limitations=["BEAM concurrency model not modeled."],
        keywords=["defmodule ", "IO.puts", "|>", "do\n", "end\n"],
    ),
    LanguageDefinition(
        identifier="sql",
        display_name="SQL",
        extensions=["sql"],
        pygments_lexer="SqlLexer",
        parser_available=False,
        static_analysis=True,
        known_limitations=[
            "Query complexity depends on query plans, indexes, and the database engine.",
            "Big-O estimates are theoretical; actual performance is data-dependent.",
        ],
        keywords=["SELECT ", "FROM ", "WHERE ", "JOIN ", "INSERT INTO"],
    ),
    LanguageDefinition(
        identifier="bash",
        display_name="Bash/Shell",
        extensions=["sh", "bash"],
        pygments_lexer="BashLexer",
        parser_available=False,
        static_analysis=True,
        known_limitations=["External command complexity is unknown."],
        keywords=["#!/bin/bash", "#!/bin/sh", "echo ", "$(", "fi\n", "done\n"],
    ),
    LanguageDefinition(
        identifier="powershell",
        display_name="PowerShell",
        extensions=["ps1", "psm1"],
        pygments_lexer="PowerShellLexer",
        parser_available=False,
        static_analysis=True,
        known_limitations=["Cmdlet complexity is not modeled."],
        keywords=["Write-Host", "Get-Item", "Param(", "foreach ", "$_"],
    ),
    LanguageDefinition(
        identifier="matlab",
        display_name="MATLAB",
        extensions=["m"],
        pygments_lexer="MatlabLexer",
        parser_available=False,
        static_analysis=True,
        known_limitations=["Built-in vectorized operations not individually modeled."],
        keywords=["function ", "disp(", "fprintf(", "%", "end"],
    ),
    LanguageDefinition(
        identifier="fortran",
        display_name="Fortran",
        extensions=["f", "f90", "f95", "f03", "f08", "for"],
        pygments_lexer="FortranLexer",
        parser_available=False,
        static_analysis=True,
        known_limitations=["Array syntax and DO loops handled heuristically."],
        keywords=["PROGRAM ", "END PROGRAM", "DO ", "REAL(", "INTEGER("],
    ),
    LanguageDefinition(
        identifier="assembly",
        display_name="Assembly",
        extensions=["asm", "s"],
        pygments_lexer="NasmLexer",
        parser_available=False,
        static_analysis=False,
        known_limitations=[
            "Complexity analysis of assembly is highly architecture-dependent.",
            "Control flow, calling conventions, and external routines must be known.",
            "Only very limited heuristic analysis is possible.",
        ],
        keywords=["mov ", "jmp ", "call ", "ret", "section "],
    ),
    LanguageDefinition(
        identifier="cobol",
        display_name="COBOL",
        extensions=["cob", "cbl"],
        pygments_lexer="CobolLexer",
        parser_available=False,
        static_analysis=True,
        known_limitations=["PERFORM loop structure heuristically analyzed."],
        keywords=["IDENTIFICATION DIVISION", "PERFORM ", "MOVE ", "DISPLAY "],
    ),
    LanguageDefinition(
        identifier="solidity",
        display_name="Solidity",
        extensions=["sol"],
        pygments_lexer="SolidityLexer",
        parser_available=False,
        static_analysis=True,
        known_limitations=["Gas cost is not modeled; only algorithmic complexity."],
        keywords=["pragma solidity", "contract ", "function ", "mapping("],
    ),
    LanguageDefinition(
        identifier="objc",
        display_name="Objective-C",
        extensions=["m", "mm"],
        pygments_lexer="ObjectiveCLexer",
        parser_available=False,
        static_analysis=True,
        known_limitations=["Message passing overhead not modeled."],
        keywords=["#import", "@interface", "@implementation", "NSLog("],
    ),
    LanguageDefinition(
        identifier="erlang",
        display_name="Erlang",
        extensions=["erl", "hrl"],
        pygments_lexer="ErlangLexer",
        parser_available=False,
        static_analysis=True,
        known_limitations=["Actor model concurrency not modeled."],
        keywords=["-module(", "-export(", "io:format(", "fun "],
    ),
    LanguageDefinition(
        identifier="generic",
        display_name="Generic / Unknown",
        extensions=[],
        pygments_lexer=None,
        parser_available=False,
        static_analysis=True,
        known_limitations=[
            "Language could not be determined; generic heuristics applied.",
            "Results are less reliable without language-specific parsing.",
        ],
        keywords=[],
    ),
]


# ---------------------------------------------------------------------------
# Registry helpers
# ---------------------------------------------------------------------------

def _build_registry() -> Dict[str, LanguageDefinition]:
    return {lang.identifier: lang for lang in _DEFINITIONS}


_REGISTRY: Dict[str, LanguageDefinition] = _build_registry()

# Extension → identifier mapping (first match wins)
_EXTENSION_MAP: Dict[str, str] = {}
for _lang in _DEFINITIONS:
    for _ext in _lang.extensions:
        if _ext not in _EXTENSION_MAP:
            _EXTENSION_MAP[_ext] = _lang.identifier


def get_language(identifier: str) -> Optional[LanguageDefinition]:
    """Return the LanguageDefinition for the given identifier, or None."""
    return _REGISTRY.get(identifier.lower())


def get_language_by_extension(extension: str) -> Optional[LanguageDefinition]:
    """Return the LanguageDefinition for the given file extension."""
    ext = extension.lower().lstrip(".")
    identifier = _EXTENSION_MAP.get(ext)
    return _REGISTRY.get(identifier) if identifier else None


def all_languages() -> List[LanguageDefinition]:
    """Return all registered language definitions."""
    return list(_DEFINITIONS)


def is_supported(identifier: str) -> bool:
    return identifier.lower() in _REGISTRY
