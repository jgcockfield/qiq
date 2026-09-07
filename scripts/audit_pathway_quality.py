#!/usr/bin/env python
"""Global QIQ pathway quality-audit tool.

Statically audits every file-based QIQ pathway (app/engine/pathways/*/ that
contains a questions.json) for question-flow quality, rule-layer consistency,
and alignment with the Costa Rica DNV UX benchmark.

This script is READ-ONLY with respect to pathway source files: it never
writes to app/engine/pathways/**, and it never imports or executes a
pathway's rules.py (which would require a working Python environment and
could have import side effects). All analysis is done by parsing JSON and by
static AST inspection of rules.py source.

Usage:
    python scripts/audit_pathway_quality.py                  # audit all pathways
    python scripts/audit_pathway_quality.py --pathway italy_dnv
    python scripts/audit_pathway_quality.py --json
    python scripts/audit_pathway_quality.py --strict         # warnings also fail exit code

Exit code:
    0 if no pathway has a FAIL-severity finding (or, with --strict, no
      FAIL/WARN findings at all)
    1 otherwise
"""

from __future__ import annotations

import argparse
import ast
import json
import re
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

REPO_ROOT = Path(__file__).resolve().parents[1]
PATHWAYS_DIR = REPO_ROOT / "app" / "engine" / "pathways"
REPORT_DIR = REPO_ROOT / "docs" / "pathway_quality_audit"

# Costa Rica DNV is the hardcoded UX/eligibility-flow benchmark. It has no
# file-based questions.json under app/engine/pathways/, so it is never a
# directory-discovered audit target -- it's referenced only as a numeric
# benchmark (see FLOW_SIZE_BENCHMARK below).
BENCHMARK_PATHWAY_NAME = "costa_rica_dnv"
FLOW_SIZE_BENCHMARK_QUESTIONS = 11

# ---------------------------------------------------------------------------
# Policy vocabularies
# ---------------------------------------------------------------------------

ESCAPE_CHOICE_RE = re.compile(
    r"(not[_\s\-]?sure|not[_\s\-]?ready|unsure|unknown|maybe)", re.IGNORECASE
)

# Contact / sales / consent key-name tokens. Matched against dotted-key path
# segments (word-level) plus a couple of known multi-word phrases matched as
# substrings of the underscore-joined key.
CONTACT_SALES_SINGLE_WORD_TOKENS = {
    "phone",
    "email",
    "consent",
    "terms",
    "privacy",
    "marketing",
    "scheduler",
    "sales",
}
CONTACT_SALES_PHRASE_TOKENS = {
    "first_name",
    "last_name",
    "service_interest",
}

# Pathway-specific allowlist for contact/sales/consent keys that are
# intentionally retained. Empty by default -- add entries as
# {"pathway_name": {"dotted.key", ...}} if a documented exception is needed.
CONTACT_SALES_ALLOWLIST: Dict[str, Set[str]] = {}

# Acknowledgement / process-question wording patterns (FLAG only).
ACKNOWLEDGEMENT_PATTERNS = [
    re.compile(r"acknowledg", re.IGNORECASE),
    re.compile(r"do you understand", re.IGNORECASE),
    re.compile(r"are you aware", re.IGNORECASE),
    re.compile(r"will you comply", re.IGNORECASE),
    re.compile(r"\bportal\b", re.IGNORECASE),
    re.compile(r"\brenewal\b", re.IGNORECASE),
    re.compile(r"\bappointment\b", re.IGNORECASE),
    re.compile(r"post[-\s]?arrival", re.IGNORECASE),
    re.compile(r"register(ed)? after approval", re.IGNORECASE),
    re.compile(r"(file|request)\b.{0,20}\bform\b", re.IGNORECASE),
    re.compile(r"additional documents may be requested", re.IGNORECASE),
]

# Hard-failure name/pattern heuristics suggesting the failure is really just
# document/checklist/acknowledgement readiness rather than a genuine
# eligibility failure (FLAG only -- severity is never auto-changed).
HARD_FAILURE_SEVERITY_PATTERNS = [
    re.compile(r"document.*(unavailable|missing)", re.IGNORECASE),
    re.compile(r"(civil_documents|apostille|translation)", re.IGNORECASE),
    re.compile(r"passport_copy", re.IGNORECASE),
    re.compile(r"passport_(blank_pages|photos)", re.IGNORECASE),
    re.compile(r"(photos?|forms?|fees?)_(unavailable|not_ready|missing)", re.IGNORECASE),
    re.compile(r"acknowledg", re.IGNORECASE),
    re.compile(r"(renewal|compliance)_acknowledg", re.IGNORECASE),
    re.compile(r"post[_\s]?arrival", re.IGNORECASE),
    re.compile(r"register(ed|ation)?_after_approval", re.IGNORECASE),
    re.compile(r"checklist", re.IGNORECASE),
]

# Legal / bureaucratic jargon terms (FLAG only). Matched case-insensitively
# as substrings against label + description + choice tokens (with choice
# tokens' underscores turned into spaces first).
JARGON_TERMS = [
    "AIMA",
    "ARI",
    "SII",
    "UCFE",
    "DGME",
    "filiacion",
    "filiación",
    "Partita IVA",
    "Art.",
    "Article ",
    "regulated profession",
    "permesso di soggiorno",
    "responsible declaration",
]
# Common short acronyms that are NOT considered jargon on their own --
# currency codes, generic tech/geo abbreviations, and QIQ's own house
# shorthand for visa-type names (these are internal product vocabulary,
# not unexplained government/legal jargon).
JARGON_ACRONYM_ALLOWLIST = {
    "EU",
    "EEA",
    "USA",
    "VAT",
    "ID",
    "IT",
    "US",
    "UK",
    "OK",
    "CV",
    "EUR",
    "USD",
    "GBP",
    "DNV",
    "NLV",
    "QIQ",
    "D7",
}

LABEL_LENGTH_THRESHOLD = 140
DESCRIPTION_LENGTH_THRESHOLD = 240

# Default allowlist of "unused question key" categories -- matched as a
# regex against the full dotted key. Fields matching these patterns are
# reported (never silently dropped) but are not treated as unexpected.
DEFAULT_UNUSED_KEY_ALLOWLIST_PATTERNS = [
    re.compile(r"\bnationality$", re.IGNORECASE),
    re.compile(r"\badditional_information$", re.IGNORECASE),
]

SUPPORTED_APPLIES_WHEN_OPERATORS = {"equals", "not_equals", "contains", "not_contains"}

GETTER_FUNCTION_NAMES = {"_get_dotted", "_get_role_value"}


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------


@dataclass
class Finding:
    rule: str
    severity: str  # "FAIL" or "WARN"
    message: str
    location: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "rule": self.rule,
            "severity": self.severity,
            "message": self.message,
            "location": self.location,
        }


@dataclass
class PathwayAudit:
    pathway: str
    directory: Path
    findings: List[Finding] = field(default_factory=list)
    metrics: Dict[str, Any] = field(default_factory=dict)
    scores: Dict[str, float] = field(default_factory=dict)
    status: str = "PASS"
    limitations: List[str] = field(default_factory=list)

    def add(self, rule: str, severity: str, message: str, location: str = "") -> None:
        self.findings.append(Finding(rule=rule, severity=severity, message=message, location=location))

    def fails(self) -> List[Finding]:
        return [f for f in self.findings if f.severity == "FAIL"]

    def warnings(self) -> List[Finding]:
        return [f for f in self.findings if f.severity == "WARN"]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "pathway": self.pathway,
            "status": self.status,
            "scores": self.scores,
            "metrics": self.metrics,
            "findings": [f.to_dict() for f in self.findings],
            "limitations": self.limitations,
        }


# ---------------------------------------------------------------------------
# Loading helpers (read-only)
# ---------------------------------------------------------------------------


def discover_pathways() -> List[str]:
    if not PATHWAYS_DIR.exists():
        return []
    names = []
    for entry in sorted(PATHWAYS_DIR.iterdir()):
        if not entry.is_dir():
            continue
        if entry.name == BENCHMARK_PATHWAY_NAME:
            continue
        if (entry / "questions.json").exists():
            names.append(entry.name)
    return names


def load_json_file(path: Path) -> Tuple[Optional[Any], Optional[str]]:
    if not path.exists():
        return None, None
    try:
        return json.loads(path.read_text(encoding="utf-8")), None
    except Exception as exc:  # noqa: BLE001
        return None, f"Failed to parse {path.name}: {exc}"


def parse_rules_ast(path: Path) -> Tuple[Optional[ast.Module], Optional[str], str]:
    if not path.exists():
        return None, f"{path.name} does not exist", ""
    try:
        source = path.read_text(encoding="utf-8")
        return ast.parse(source, filename=str(path)), None, source
    except SyntaxError as exc:  # noqa: BLE001
        return None, f"Failed to parse rules.py: {exc}", ""


# ---------------------------------------------------------------------------
# rules.py static analysis
# ---------------------------------------------------------------------------


def _literal_str(node: ast.AST) -> Optional[str]:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return None


def _fstring_pattern(node: ast.AST) -> Optional[str]:
    """Turn an f-string AST node into a wildcard pattern, e.g.
    f"role.{role_prefix}.foo" -> "role.*.foo". Returns None if the node
    isn't a JoinedStr (f-string)."""
    if not isinstance(node, ast.JoinedStr):
        return None
    parts = []
    for value in node.values:
        if isinstance(value, ast.Constant) and isinstance(value.value, str):
            parts.append(value.value)
        elif isinstance(value, ast.FormattedValue):
            parts.append("*")
        else:
            parts.append("*")
    return "".join(parts)


def _pattern_to_regex(pattern: str) -> re.Pattern:
    escaped = re.escape(pattern).replace(r"\*", "[^.]+")
    return re.compile(f"^{escaped}$")


class _FunctionInfo:
    __slots__ = ("node", "param_names", "kwonly_names")

    def __init__(self, node: ast.FunctionDef):
        self.node = node
        # Positional-or-keyword params keep their positional index; keyword-
        # only params (after a bare `*` in the signature) have no positional
        # index and can only be matched by keyword at the call site.
        self.param_names = [a.arg for a in node.args.args]
        self.kwonly_names = [a.arg for a in node.args.kwonlyargs]


class RulesAnalysis:
    """Static analysis of a pathway's rules.py.

    Extracts (best-effort, heuristic where noted):
      - hard_failures: contents of the module-level HARD_FAILURES set/list
      - direct_reads: dotted answer keys read via a literal string argument
        to a getter function (_get_dotted / _get_role_value), resolved
        through up to one level of local-helper indirection
      - dynamic_read_patterns: wildcard patterns (e.g. "role.*.foo") for
        keys read via an f-string, resolved through indirection the same way
      - emitted_codes: string literals passed to `<list>.append(...)`,
        resolved the same way
      - unresolved_appends / unresolved_reads: counts of call sites that
        could not be statically resolved (reported as a limitation, not
        silently dropped)
    """

    def __init__(self, tree: ast.Module):
        self.tree = tree
        self.functions: Dict[str, _FunctionInfo] = {}
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                self.functions[node.name] = _FunctionInfo(node)

        self.hard_failures: Set[str] = set()
        self.direct_reads: Set[str] = set()
        self.dynamic_read_patterns: Set[str] = set()
        self.emitted_codes: Set[str] = set()
        self.unresolved_appends = 0
        self.unresolved_reads = 0

        # function_name -> set of param names that feed into a getter call
        self._read_param_feeds: Dict[str, Set[int]] = defaultdict(set)
        self._read_param_feeds_dynamic: Dict[str, Set[int]] = defaultdict(set)
        # function_name -> set of param indexes that feed into .append(...)
        self._append_param_feeds: Dict[str, Set[int]] = defaultdict(set)
        # module-level `NAME = {"a": "x", "b": "y"}` dict literals (all
        # string values) -- used to resolve `SOME_DICT.get(key, "default")`
        # arguments to `.append(...)`.
        self._module_str_dicts: Dict[str, List[str]] = {}

        self._extract_hard_failures()
        self._extract_module_str_dicts()
        self._analyze_functions()
        self._resolve_call_sites()

    # -- HARD_FAILURES -----------------------------------------------------

    def _extract_hard_failures(self) -> None:
        for node in ast.walk(self.tree):
            if isinstance(node, ast.Assign) and len(node.targets) == 1:
                target = node.targets[0]
                if isinstance(target, ast.Name) and target.id == "HARD_FAILURES":
                    if isinstance(node.value, (ast.Set, ast.List, ast.Tuple)):
                        for elt in node.value.elts:
                            lit = _literal_str(elt)
                            if lit:
                                self.hard_failures.add(lit)

    def _extract_module_str_dicts(self) -> None:
        for node in ast.walk(self.tree):
            if isinstance(node, ast.Assign) and len(node.targets) == 1:
                target = node.targets[0]
                if isinstance(target, ast.Name) and isinstance(node.value, ast.Dict):
                    values = [_literal_str(v) for v in node.value.values]
                    if values and all(v is not None for v in values):
                        self._module_str_dicts[target.id] = values  # type: ignore[assignment]

    # -- per-function pass ---------------------------------------------------

    def _param_key(self, fname: str, param_name: str):
        """Return a key identifying this parameter for cross-call-site
        resolution: an int positional index for a normal positional-or-
        keyword parameter, the parameter's own name (str) for a keyword-only
        parameter, or None if `param_name` isn't a parameter of `fname`."""
        info = self.functions.get(fname)
        if not info:
            return None
        if param_name in info.param_names:
            return info.param_names.index(param_name)
        if param_name in info.kwonly_names:
            return param_name
        return None

    def _analyze_functions(self) -> None:
        for fname, info in self.functions.items():
            local_str_vars: Dict[str, str] = {}
            # simple single-assignment constant propagation
            for node in ast.walk(info.node):
                if isinstance(node, ast.Assign) and len(node.targets) == 1:
                    target = node.targets[0]
                    if isinstance(target, ast.Name):
                        lit = _literal_str(node.value)
                        if lit is not None:
                            local_str_vars[target.id] = lit
                        elif target.id in local_str_vars:
                            del local_str_vars[target.id]

            for node in ast.walk(info.node):
                if not isinstance(node, ast.Call):
                    continue

                callee_name = self._callee_name(node.func)

                # `<list>.append(X)`
                if isinstance(node.func, ast.Attribute) and node.func.attr == "append":
                    if node.args:
                        self._resolve_and_record_append(node.args[0], fname, info, local_str_vars)

                # getter calls
                elif callee_name in GETTER_FUNCTION_NAMES:
                    key_arg = self._get_key_argument(node, callee_name)
                    if key_arg is not None:
                        self._resolve_and_record_read(key_arg, fname, info, local_str_vars)

    def _callee_name(self, func_node: ast.AST) -> Optional[str]:
        if isinstance(func_node, ast.Name):
            return func_node.id
        if isinstance(func_node, ast.Attribute):
            return func_node.attr
        return None

    def _get_key_argument(self, call: ast.Call, callee_name: str) -> Optional[ast.AST]:
        # _get_dotted(payload, key, default=None) -> positional index 1
        # _get_role_value(payload, work_type, field_name) -> the dotted key
        #   is synthesized inside the function; treat field_name (index 2)
        #   as the resolvable fragment, tagged specially below.
        if callee_name == "_get_dotted":
            for kw in call.keywords:
                if kw.arg in ("key", "dotted_key"):
                    return kw.arg, kw.value  # type: ignore[return-value]
            if len(call.args) >= 2:
                return "key", call.args[1]  # type: ignore[return-value]
        elif callee_name == "_get_role_value":
            for kw in call.keywords:
                if kw.arg == "field_name":
                    return "field_name", kw.value  # type: ignore[return-value]
            if len(call.args) >= 3:
                return "field_name", call.args[2]  # type: ignore[return-value]
        return None

    def _resolve_and_record_read(self, tagged_arg, fname: str, info: _FunctionInfo, local_str_vars: Dict[str, str]) -> None:
        tag, arg_node = tagged_arg
        lit = _literal_str(arg_node)
        if lit is not None:
            if tag == "field_name":
                # _get_role_value's field_name: known role prefixes observed
                # in this codebase; record as a wildcard pattern.
                self.dynamic_read_patterns.add(f"role.*.{lit}")
            else:
                self.direct_reads.add(lit)
            return

        pattern = _fstring_pattern(arg_node)
        if pattern is not None:
            self.dynamic_read_patterns.add(pattern)
            return

        if isinstance(arg_node, ast.Name):
            if arg_node.id in local_str_vars:
                self.direct_reads.add(local_str_vars[arg_node.id])
                return
            param_key = self._param_key(fname, arg_node.id)
            if param_key is not None:
                self._read_param_feeds[fname].add(param_key)
                return

        self.unresolved_reads += 1

    def _resolve_and_record_append(self, arg_node: ast.AST, fname: str, info: _FunctionInfo, local_str_vars: Dict[str, str]) -> None:
        lit = _literal_str(arg_node)
        if lit is not None:
            self.emitted_codes.add(lit)
            return

        if isinstance(arg_node, ast.Name):
            if arg_node.id in local_str_vars:
                self.emitted_codes.add(local_str_vars[arg_node.id])
                return
            param_key = self._param_key(fname, arg_node.id)
            if param_key is not None:
                self._append_param_feeds[fname].add(param_key)
                return

        # `SOME_DICT.get(key, "default")` where SOME_DICT is a module-level
        # dict literal of string values: every possible value the .get()
        # could return is a possible emitted code.
        if (
            isinstance(arg_node, ast.Call)
            and isinstance(arg_node.func, ast.Attribute)
            and arg_node.func.attr == "get"
            and isinstance(arg_node.func.value, ast.Name)
            and arg_node.func.value.id in self._module_str_dicts
        ):
            self.emitted_codes.update(self._module_str_dicts[arg_node.func.value.id])
            default_node = None
            if len(arg_node.args) >= 2:
                default_node = arg_node.args[1]
            for kw in arg_node.keywords:
                if kw.arg == "default":
                    default_node = kw.value
            if default_node is not None:
                default_lit = _literal_str(default_node)
                if default_lit is not None:
                    self.emitted_codes.add(default_lit)
            return

        self.unresolved_appends += 1

    # -- call-site resolution (one hop of indirection) -----------------------

    def _resolve_call_sites(self) -> None:
        if not self._read_param_feeds and not self._append_param_feeds:
            return

        for node in ast.walk(self.tree):
            if not isinstance(node, ast.Call):
                continue
            callee_name = self._callee_name(node.func)
            if callee_name not in self.functions:
                continue

            info = self.functions[callee_name]
            positional_by_index: Dict[int, ast.AST] = dict(enumerate(node.args))
            keyword_by_name: Dict[str, ast.AST] = {
                kw.arg: kw.value for kw in node.keywords if kw.arg is not None
            }

            def _resolve_arg(param_key):
                # int -> positional-or-keyword param: check positional first,
                # then fall back to being passed by keyword at this call site.
                # str -> keyword-only param: only resolvable by keyword.
                if isinstance(param_key, int):
                    if param_key in positional_by_index:
                        return positional_by_index[param_key]
                    if param_key < len(info.param_names):
                        return keyword_by_name.get(info.param_names[param_key])
                    return None
                return keyword_by_name.get(param_key)

            for param_key in self._read_param_feeds.get(callee_name, set()):
                arg_node = _resolve_arg(param_key)
                if arg_node is None:
                    self.unresolved_reads += 1
                    continue
                lit = _literal_str(arg_node)
                if lit is not None:
                    self.direct_reads.add(lit)
                    continue
                pattern = _fstring_pattern(arg_node)
                if pattern is not None:
                    self.dynamic_read_patterns.add(pattern)
                    continue
                self.unresolved_reads += 1

            for param_key in self._append_param_feeds.get(callee_name, set()):
                arg_node = _resolve_arg(param_key)
                if arg_node is None:
                    self.unresolved_appends += 1
                    continue
                lit = _literal_str(arg_node)
                if lit is not None:
                    self.emitted_codes.add(lit)
                else:
                    self.unresolved_appends += 1

    # -- convenience ---------------------------------------------------------

    def key_is_read(self, key: str, allow_dynamic: bool = True) -> bool:
        if key in self.direct_reads:
            return True
        if allow_dynamic:
            for pattern in self.dynamic_read_patterns:
                if _pattern_to_regex(pattern).match(key):
                    return True
        return False


# ---------------------------------------------------------------------------
# questions.json helpers
# ---------------------------------------------------------------------------


def get_taxonomy_fields(questions_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    fields = questions_data.get("taxonomy_fields")
    if not isinstance(fields, list):
        return []
    return [f for f in fields if isinstance(f, dict)]


def get_checklist_fields(questions_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    checklist = questions_data.get("post_eligibility_checklist")
    if not isinstance(checklist, dict):
        return []
    fields = checklist.get("fields")
    if not isinstance(fields, list):
        return []
    return [f for f in fields if isinstance(f, dict)]


def field_is_required(f: Dict[str, Any]) -> bool:
    return f.get("required", True) is not False


def readable_choice(token: str) -> str:
    return str(token).replace("_", " ")


# ---------------------------------------------------------------------------
# Individual audit rules
# ---------------------------------------------------------------------------


def check_schema(audit: PathwayAudit, questions_data: Any) -> bool:
    """Returns True if the schema is sound enough to keep auditing field-by-field."""
    if not isinstance(questions_data, dict):
        audit.add("schema", "FAIL", "questions.json root is not a JSON object")
        return False

    fields = questions_data.get("taxonomy_fields")
    if not isinstance(fields, list) or not fields:
        audit.add("schema", "FAIL", "questions.json has no non-empty 'taxonomy_fields' array")
        return False

    ok = True
    seen_keys: Set[str] = set()
    for idx, f in enumerate(fields):
        if not isinstance(f, dict):
            audit.add("schema", "FAIL", f"taxonomy_fields[{idx}] is not an object")
            ok = False
            continue
        key = f.get("key")
        if not isinstance(key, str) or not key:
            audit.add("schema", "FAIL", f"taxonomy_fields[{idx}] has no valid 'key'")
            ok = False
            continue
        if key in seen_keys:
            audit.add("schema", "FAIL", f"duplicate question key '{key}'", location=key)
        seen_keys.add(key)
        input_type = f.get("input_type")
        if not isinstance(input_type, str) or not input_type:
            audit.add("schema", "FAIL", f"question '{key}' has no valid 'input_type'", location=key)
            ok = False
        if input_type in ("choice", "multi_choice"):
            choices = f.get("choices")
            if not isinstance(choices, list) or not choices:
                audit.add(
                    "schema",
                    "FAIL",
                    f"question '{key}' has input_type '{input_type}' but no non-empty 'choices'",
                    location=key,
                )
                ok = False
    return ok


def check_escape_choices(audit: PathwayAudit, live_fields: List[Dict[str, Any]]) -> None:
    for f in live_fields:
        key = f.get("key", "?")
        choices = f.get("choices") or []
        for choice in choices:
            if isinstance(choice, str) and ESCAPE_CHOICE_RE.search(choice):
                audit.add(
                    "escape_choices",
                    "FAIL",
                    f"choice '{choice}' on question '{key}' is an escape/uncertainty token",
                    location=key,
                )


def check_acknowledgement_process_questions(audit: PathwayAudit, live_fields: List[Dict[str, Any]]) -> None:
    for f in live_fields:
        key = f.get("key", "?")
        text = " ".join(
            str(f.get(part) or "") for part in ("label", "description", "key")
        )
        matched = [p.pattern for p in ACKNOWLEDGEMENT_PATTERNS if p.search(text)]
        if matched:
            audit.add(
                "acknowledgement_process",
                "WARN",
                f"question '{key}' looks like an acknowledgement/process question, not a factual eligibility question "
                f"(matched: {', '.join(matched)}) -- manual review recommended",
                location=key,
            )


def check_contact_sales_consent(audit: PathwayAudit, live_fields: List[Dict[str, Any]], pathway: str) -> None:
    allowlist = CONTACT_SALES_ALLOWLIST.get(pathway, set())
    for f in live_fields:
        key = f.get("key", "?")
        if key in allowlist:
            continue
        normalized = key.lower()
        segments = re.split(r"[.\_]", normalized)
        hit = None
        for token in CONTACT_SALES_SINGLE_WORD_TOKENS:
            if token in segments:
                hit = token
                break
        if not hit:
            for phrase in CONTACT_SALES_PHRASE_TOKENS:
                if phrase in normalized:
                    hit = phrase
                    break
        if hit:
            audit.add(
                "contact_sales_consent",
                "FAIL",
                f"question '{key}' looks like a contact/sales/consent field ('{hit}'), "
                "which does not belong in a lean eligibility flow",
                location=key,
            )


def check_unused_question_keys(
    audit: PathwayAudit,
    live_fields: List[Dict[str, Any]],
    analysis: RulesAnalysis,
) -> None:
    for f in live_fields:
        if not field_is_required(f):
            continue
        key = f.get("key", "?")
        if analysis.key_is_read(key):
            continue
        allowlisted = any(p.search(key) for p in DEFAULT_UNUSED_KEY_ALLOWLIST_PATTERNS)
        note = " (allowlisted category -- reported, not treated as unexpected)" if allowlisted else ""
        audit.add(
            "unused_question_key",
            "WARN",
            f"required question '{key}' does not appear to be referenced by rules.py{note}",
            location=key,
        )


def check_phantom_rule_keys(
    audit: PathwayAudit,
    known_keys: Set[str],
    analysis: RulesAnalysis,
) -> None:
    for key in sorted(analysis.direct_reads):
        if key not in known_keys:
            audit.add(
                "phantom_rule_key",
                "FAIL",
                f"rules.py reads answer field '{key}' which does not exist in questions.json",
                location=key,
            )
    # Dynamic patterns that match nothing at all are lower-confidence --
    # surface as a warning rather than a fail.
    for pattern in sorted(analysis.dynamic_read_patterns):
        regex = _pattern_to_regex(pattern)
        if not any(regex.match(k) for k in known_keys):
            audit.add(
                "phantom_rule_key",
                "WARN",
                f"rules.py reads a dynamically-built field matching pattern '{pattern}', "
                "which does not match any question in questions.json",
                location=pattern,
            )


def check_dead_requirement_codes(
    audit: PathwayAudit,
    analysis: RulesAnalysis,
    clarifications_data: Optional[Dict[str, Any]],
    output_data: Optional[Dict[str, Any]],
) -> None:
    emitted = analysis.emitted_codes | analysis.hard_failures

    clarification_entries = []
    if isinstance(clarifications_data, dict):
        clarification_entries = [
            c for c in clarifications_data.get("clarifications", []) if isinstance(c, dict)
        ]
    clarification_codes = {c.get("requirement") for c in clarification_entries if c.get("requirement")}
    documented_stage_codes = {
        c.get("requirement") for c in clarification_entries if c.get("requirement") and c.get("stage")
    }

    output_codes: Set[str] = set()
    documented_output_stage_codes: Set[str] = set()
    if isinstance(output_data, dict):
        for section_key in ("summary_statement", "next_steps_cta"):
            section = output_data.get(section_key)
            if not isinstance(section, dict):
                continue
            variants = section.get("requirement_variants")
            if not isinstance(variants, dict):
                continue
            for code, variant in variants.items():
                output_codes.add(code)
                if isinstance(variant, dict) and variant.get("stage"):
                    documented_output_stage_codes.add(code)

    # needs_manual_review is a generic fallback clarification that
    # output_builder.py substitutes in whenever status == "needs_review" and
    # no requirement-specific clarification matched -- it is never itself
    # a literal code in failed_requirements, so it would always appear
    # "dead" under a naive emitted-vs-declared comparison. Exclude it.
    dead_clarifications = (clarification_codes - emitted) - {"needs_manual_review"}
    for code in sorted(dead_clarifications):
        if code in documented_stage_codes:
            audit.add(
                "dead_requirement_code",
                "WARN",
                f"clarification '{code}' is never emitted by rules.py, but is explicitly documented "
                "as preserved (stage annotation present) -- likely intentional",
                location=code,
            )
        else:
            audit.add(
                "dead_requirement_code",
                "WARN",
                f"clarification '{code}' is never emitted by rules.py (dead entry)",
                location=code,
            )

    dead_outputs = output_codes - emitted
    for code in sorted(dead_outputs):
        if code in documented_output_stage_codes:
            audit.add(
                "dead_requirement_code",
                "WARN",
                f"output.json requirement_variant '{code}' is never emitted by rules.py, but is explicitly "
                "documented as preserved (stage annotation present) -- likely intentional",
                location=code,
            )
        else:
            audit.add(
                "dead_requirement_code",
                "WARN",
                f"output.json requirement_variant '{code}' is never emitted by rules.py (dead entry)",
                location=code,
            )

    unmapped = emitted - clarification_codes
    # needs_manual_review is an intentional generic fallback used by
    # output_builder.py when no specific clarification matches -- excluding
    # this exact code from the "unmapped" flag avoids a permanent false
    # positive on every pathway that (correctly) doesn't define a
    # requirement literally named that.
    unmapped = {c for c in unmapped if c != "needs_manual_review"}
    for code in sorted(unmapped):
        audit.add(
            "dead_requirement_code",
            "WARN",
            f"requirement code '{code}' can be emitted by rules.py but has no clarifications.json entry",
            location=code,
        )


def check_hard_failure_severity(audit: PathwayAudit, analysis: RulesAnalysis) -> None:
    for code in sorted(analysis.hard_failures):
        matched = [p.pattern for p in HARD_FAILURE_SEVERITY_PATTERNS if p.search(code)]
        if matched:
            audit.add(
                "hard_failure_severity",
                "WARN",
                f"HARD_FAILURES entry '{code}' looks like it may be document/checklist/acknowledgement "
                f"readiness rather than a genuine eligibility failure (matched: {', '.join(matched)}) "
                "-- consider softening to needs_review",
                location=code,
            )


def _field_text_for_jargon(f: Dict[str, Any]) -> str:
    parts = [str(f.get("label") or ""), str(f.get("description") or "")]
    for choice in f.get("choices") or []:
        if isinstance(choice, str):
            parts.append(readable_choice(choice))
    return " ".join(parts)


def _jargon_term_matches(term: str, text: str) -> bool:
    # Short, all-caps, acronym-shaped terms (AIMA, ARI, SII, ...) risk
    # colliding with ordinary substrings ("ARI" inside "arise"), so match
    # those on word boundaries; longer/phrase-like terms ("regulated
    # profession", "Partita IVA") are safe to match as plain substrings.
    stripped = term.strip()
    if stripped.isupper() and len(stripped) <= 6 and " " not in stripped:
        return re.search(rf"\b{re.escape(stripped)}\b", text, re.IGNORECASE) is not None
    return stripped.lower() in text.lower()


def check_legal_jargon(audit: PathwayAudit, live_fields: List[Dict[str, Any]]) -> None:
    for f in live_fields:
        key = f.get("key", "?")
        text = _field_text_for_jargon(f)
        matched_terms = [term for term in JARGON_TERMS if _jargon_term_matches(term, text)]

        acronym_hits = set(re.findall(r"\b[A-Z]{2,6}\b", text)) - JARGON_ACRONYM_ALLOWLIST
        # Only count acronyms not already covered by the explicit term list.
        acronym_hits = {a for a in acronym_hits if a.lower() not in {t.lower() for t in matched_terms}}

        if matched_terms:
            audit.add(
                "legal_jargon",
                "WARN",
                f"question '{key}' contains legal/bureaucratic jargon: {', '.join(sorted(set(matched_terms)))}",
                location=key,
            )
        if acronym_hits:
            audit.add(
                "legal_jargon",
                "WARN",
                f"question '{key}' contains unexplained acronym(s): {', '.join(sorted(acronym_hits))}",
                location=key,
            )


def check_length_and_complexity(audit: PathwayAudit, live_fields: List[Dict[str, Any]]) -> None:
    for f in live_fields:
        key = f.get("key", "?")
        label = str(f.get("label") or "")
        description = str(f.get("description") or "")

        if len(label) > LABEL_LENGTH_THRESHOLD:
            audit.add(
                "question_length",
                "WARN",
                f"question '{key}' label is {len(label)} chars (> {LABEL_LENGTH_THRESHOLD})",
                location=key,
            )
        if len(description) > DESCRIPTION_LENGTH_THRESHOLD:
            audit.add(
                "question_length",
                "WARN",
                f"question '{key}' description is {len(description)} chars (> {DESCRIPTION_LENGTH_THRESHOLD})",
                location=key,
            )

        # Compound-question heuristic: multiple "and"/"or" joining distinct
        # factual clauses. A single "and"/"or" inside a normal sentence is
        # common and not flagged; 2+ occurrences is the signal used here.
        and_or_count = len(re.findall(r"\band\b|\bor\b", label, re.IGNORECASE))
        if and_or_count >= 2:
            audit.add(
                "question_complexity",
                "WARN",
                f"question '{key}' label may bundle multiple factual checks into one question "
                f"({and_or_count} and/or joins)",
                location=key,
            )


def check_poor_choice_design(audit: PathwayAudit, live_fields: List[Dict[str, Any]]) -> None:
    band_re = re.compile(
        r"^(less_than_|at_least_|between_|eur_|usd_|\d+_to_\d+|\d+plus|\d+_or_more|under_|over_)",
        re.IGNORECASE,
    )
    for f in live_fields:
        key = f.get("key", "?")
        input_type = f.get("input_type")
        choices = f.get("choices") or []
        if input_type != "choice" or not choices:
            continue
        if not all(isinstance(c, str) for c in choices):
            continue

        # raw internal tokens that would render poorly (camelCase, all caps
        # with underscores that look like enum constants, or containing raw
        # separators the UI wouldn't format well).
        for choice in choices:
            if re.search(r"[A-Z]{2,}", choice) or choice.strip() != choice:
                audit.add(
                    "poor_choice_design",
                    "WARN",
                    f"choice '{choice}' on question '{key}' may render poorly as raw UI text",
                    location=key,
                )

        # numeric band choices where a direct numeric value could be asked.
        # Only flag when a clear MAJORITY of choices are band-shaped -- a
        # categorical choice set that merely mentions a number in one or two
        # options (e.g. "at_least_5_years_experience" alongside
        # "university_degree", "none_of_these") is not a band ladder and
        # should not be pushed toward a numeric input.
        band_like = [c for c in choices if band_re.search(c) or re.search(r"\d", c)]
        if len(choices) >= 2 and len(band_like) / len(choices) >= 0.6:
            audit.add(
                "poor_choice_design",
                "WARN",
                f"question '{key}' uses banded/threshold choices ({choices}); "
                "a direct numeric input may be more precise",
                location=key,
            )


# -- conditional logic consistency (#11) + ordering (#12) -------------------


def _validate_applies_when(
    audit: PathwayAudit,
    f: Dict[str, Any],
    known_keys: Set[str],
    key_to_choices: Dict[str, List[str]],
) -> None:
    key = f.get("key", "?")
    condition = f.get("applies_when")
    if condition is None:
        return
    if not isinstance(condition, dict) or not condition:
        audit.add(
            "conditional_logic",
            "FAIL",
            f"question '{key}' has a malformed 'applies_when' (not a non-empty object)",
            location=key,
        )
        return

    operator_keys = [k for k in condition.keys() if k in SUPPORTED_APPLIES_WHEN_OPERATORS]
    unsupported_keys = [k for k in condition.keys() if k not in SUPPORTED_APPLIES_WHEN_OPERATORS]

    if unsupported_keys:
        audit.add(
            "conditional_logic",
            "FAIL",
            f"question '{key}' has 'applies_when' with unsupported operator(s): {unsupported_keys}",
            location=key,
        )
    if not operator_keys:
        return
    if len(operator_keys) > 1:
        audit.add(
            "conditional_logic",
            "WARN",
            f"question '{key}' has 'applies_when' with multiple operators {operator_keys}; "
            "only the first (in evaluator priority order) is ever evaluated",
            location=key,
        )

    operator = operator_keys[0]
    value = condition[operator]
    if not (isinstance(value, (list, tuple)) and len(value) == 2 and isinstance(value[0], str)):
        audit.add(
            "conditional_logic",
            "FAIL",
            f"question '{key}' has 'applies_when.{operator}' that is not a [key, expected_value] pair",
            location=key,
        )
        return

    ref_key, expected = value
    if ref_key not in known_keys:
        audit.add(
            "conditional_logic",
            "FAIL",
            f"question '{key}' has 'applies_when' referencing unknown key '{ref_key}'",
            location=key,
        )
        return

    choices = key_to_choices.get(ref_key)
    if operator in ("equals", "not_equals") and choices and isinstance(expected, str):
        if expected not in choices:
            audit.add(
                "conditional_logic",
                "WARN",
                f"question '{key}' has 'applies_when' expecting '{ref_key}' == '{expected}', "
                f"but '{expected}' is not among {ref_key}'s declared choices {choices}",
                location=key,
            )


def check_conditional_logic(audit: PathwayAudit, live_fields: List[Dict[str, Any]], known_keys: Set[str]) -> None:
    key_to_choices = {
        f.get("key"): f.get("choices")
        for f in live_fields
        if isinstance(f.get("key"), str) and isinstance(f.get("choices"), list)
    }
    for f in live_fields:
        key = f.get("key", "?")
        depends_on = f.get("depends_on")
        if depends_on is None:
            continue
        if not isinstance(depends_on, list):
            audit.add(
                "conditional_logic",
                "FAIL",
                f"question '{key}' has a malformed 'depends_on' (not a list)",
                location=key,
            )
        else:
            for dep in depends_on:
                if isinstance(dep, str) and dep not in known_keys:
                    audit.add(
                        "conditional_logic",
                        "WARN",
                        f"question '{key}' has depends_on referencing unknown key '{dep}' "
                        "(depends_on is documentation-only, so this does not affect runtime behavior)",
                        location=key,
                    )

        _validate_applies_when(audit, f, known_keys, key_to_choices)


def check_question_order(audit: PathwayAudit, live_fields: List[Dict[str, Any]]) -> None:
    index_of = {f.get("key"): i for i, f in enumerate(live_fields) if isinstance(f.get("key"), str)}

    for i, f in enumerate(live_fields):
        key = f.get("key", "?")
        depends_on = f.get("depends_on")
        if isinstance(depends_on, list):
            for dep in depends_on:
                dep_index = index_of.get(dep)
                if dep_index is not None and dep_index >= i:
                    audit.add(
                        "question_order",
                        "WARN",
                        f"question '{key}' depends_on '{dep}', which appears at or after its own position "
                        f"in the array (index {dep_index} >= {i})",
                        location=key,
                    )

        condition = f.get("applies_when")
        if isinstance(condition, dict):
            for op in SUPPORTED_APPLIES_WHEN_OPERATORS:
                if op in condition and isinstance(condition[op], (list, tuple)) and condition[op]:
                    ref_key = condition[op][0]
                    ref_index = index_of.get(ref_key)
                    if ref_index is not None and ref_index > i:
                        audit.add(
                            "question_order",
                            "WARN",
                            f"question '{key}' has applies_when referencing '{ref_key}', which appears "
                            f"LATER in the array (index {ref_index} > {i}) -- likely unreachable branch",
                            location=key,
                        )

    # unconditional document/process questions appearing before the first
    # routing/role gate.
    first_gate_index = next(
        (i for i, f in enumerate(live_fields) if str(f.get("key", "")).startswith(("routing.", "role."))),
        None,
    )
    if first_gate_index is not None:
        for i, f in enumerate(live_fields[:first_gate_index]):
            key = str(f.get("key", ""))
            if key.startswith("documents.") or ACKNOWLEDGEMENT_PATTERNS[0].search(key):
                audit.add(
                    "question_order",
                    "WARN",
                    f"question '{key}' (document/process-looking) appears before the first "
                    "routing/role eligibility gate",
                    location=key,
                )


def _significant_words(text: str) -> Set[str]:
    stopwords = {
        "the", "a", "an", "is", "are", "do", "does", "you", "your", "of", "to", "for",
        "in", "on", "and", "or", "will", "can", "this", "that", "have", "has", "be",
        "would", "with", "from", "at", "as", "it", "if", "any",
    }
    words = re.findall(r"[a-z]+", text.lower())
    # A crude stem (first 6 chars) rather than exact words -- catches wording
    # variants of the same concept ("retired"/"retirement",
    # "employed"/"employment") without needing a real stemming library. This
    # is deliberately lightweight; see the module's Limitations section.
    return {w[:6] for w in words if w not in stopwords and len(w) > 2}


def _is_mirrored_branch_pair(key1: str, key2: str) -> bool:
    """True when key1/key2 look like the SAME leaf field name repeated once
    per work-type/role branch, e.g. role.employee.monthly_income_eur vs.
    role.contractor.monthly_income_eur -- intentional conditional branching
    (a Costa-Rica-DNV-style pattern used throughout these pathways), not
    redundancy. Matches on: same first segment, same last segment, at least
    3 segments, and a *different* second (branch/category) segment."""
    parts1 = key1.split(".")
    parts2 = key2.split(".")
    if len(parts1) < 3 or len(parts2) < 3:
        return False
    return (
        parts1[0] == parts2[0]
        and parts1[-1] == parts2[-1]
        and parts1[1] != parts2[1]
    )


def check_redundancy(audit: PathwayAudit, live_fields: List[Dict[str, Any]]) -> None:
    reported: Set[Tuple[str, str]] = set()
    for i, f1 in enumerate(live_fields):
        key1 = f1.get("key", "?")
        label1 = str(f1.get("label") or "")
        words1 = _significant_words(label1)
        if not words1:
            continue
        for f2 in live_fields[i + 1:]:
            key2 = f2.get("key", "?")
            if isinstance(key1, str) and isinstance(key2, str) and _is_mirrored_branch_pair(key1, key2):
                continue
            label2 = str(f2.get("label") or "")
            words2 = _significant_words(label2)
            if not words2:
                continue
            overlap = words1 & words2
            union = words1 | words2
            similarity = len(overlap) / len(union) if union else 0
            pair_key = tuple(sorted((key1, key2)))
            if similarity >= 0.6 and len(overlap) >= 2 and pair_key not in reported:
                reported.add(pair_key)
                audit.add(
                    "redundancy",
                    "WARN",
                    f"questions '{key1}' and '{key2}' have highly similar wording "
                    f"(similarity={similarity:.2f}) -- possible duplicate/near-duplicate",
                    location=f"{key1} / {key2}",
                )


def check_numeric_threshold_design(audit: PathwayAudit, live_fields: List[Dict[str, Any]], analysis: RulesAnalysis, source: str) -> None:
    field_by_key = {f.get("key"): f for f in live_fields if isinstance(f.get("key"), str)}

    # Find comparisons of the form `_as_int(_get_dotted(payload, "key")) <op> CONST`
    # by scanning source text for the pattern -- a source-text heuristic is
    # used here (rather than full AST comparison-tracing) because thresholds
    # are frequently compared against named module-level constants, and
    # matching by proximity in source text is simpler and sufficiently
    # reliable for this codebase's consistent style.
    numeric_compare_re = re.compile(
        r'_get_dotted\([^)]*?["\']([\w\.]+)["\'][^)]*\)\s*\)?\s*(?:<|<=|>|>=)\s*[A-Z_]+\w*'
    )
    keys_compared_numerically: Set[str] = set()
    for match in numeric_compare_re.finditer(source):
        keys_compared_numerically.add(match.group(1))

    for key in sorted(keys_compared_numerically):
        f = field_by_key.get(key)
        if not f:
            continue  # covered separately by phantom-key check
        input_type = f.get("input_type")
        if input_type != "number":
            audit.add(
                "numeric_threshold_design",
                "WARN",
                f"question '{key}' is compared against a numeric threshold in rules.py but uses "
                f"input_type '{input_type}' instead of 'number'",
                location=key,
            )


# ---------------------------------------------------------------------------
# Flow size metrics (#15) and requirements-reference cross-check (#16)
# ---------------------------------------------------------------------------


def compute_flow_metrics(live_fields: List[Dict[str, Any]]) -> Dict[str, Any]:
    total = len(live_fields)
    required = sum(1 for f in live_fields if field_is_required(f))
    optional = total - required
    conditional = sum(1 for f in live_fields if isinstance(f.get("applies_when"), dict))

    # Shortest branch: required fields with no applies_when (always asked) --
    # a reasonable static proxy for the shortest possible path length.
    always_asked = sum(1 for f in live_fields if field_is_required(f) and not f.get("applies_when"))

    return {
        "total_questions": total,
        "required_questions": required,
        "optional_questions": optional,
        "conditional_questions": conditional,
        "shortest_branch_estimate": always_asked,
        "longest_branch_estimate": required,
    }


def check_flow_size(audit: PathwayAudit, metrics: Dict[str, Any]) -> None:
    total = metrics["total_questions"]
    conditional = metrics["conditional_questions"]
    # A pathway is only flagged if it's meaningfully longer than the
    # benchmark AND a large share of the extra length isn't explained by
    # conditional branching (which is an accepted reason for extra length).
    if total > FLOW_SIZE_BENCHMARK_QUESTIONS * 1.5:
        conditional_ratio = conditional / total if total else 0
        if conditional_ratio < 0.35:
            audit.add(
                "flow_size",
                "WARN",
                f"pathway has {total} questions vs. the Costa Rica DNV benchmark of "
                f"~{FLOW_SIZE_BENCHMARK_QUESTIONS}, with only {conditional} conditional "
                f"({conditional_ratio:.0%}) -- length does not appear well justified by branching",
                location="",
            )
        else:
            audit.add(
                "flow_size",
                "WARN",
                f"pathway has {total} questions vs. the Costa Rica DNV benchmark of "
                f"~{FLOW_SIZE_BENCHMARK_QUESTIONS}, but {conditional} are conditional "
                f"({conditional_ratio:.0%}) -- likely justified by branching, review to confirm",
                location="",
            )


def check_requirements_reference(
    audit: PathwayAudit,
    pathway_dir: Path,
    live_fields: List[Dict[str, Any]],
    source: str,
) -> None:
    ref_path = pathway_dir / "requirements_reference.md"
    if not ref_path.exists():
        audit.limitations.append(
            "No requirements_reference.md found -- rule #16 cross-check skipped for this pathway."
        )
        return

    try:
        text = ref_path.read_text(encoding="utf-8")
    except Exception as exc:  # noqa: BLE001
        audit.limitations.append(f"Could not read requirements_reference.md: {exc}")
        return

    headings = re.findall(r"^#{1,4}\s+(.+)$", text, re.MULTILINE)
    bold_terms = re.findall(r"\*\*(.+?)\*\*", text)
    keywords = {h.strip().lower() for h in headings} | {b.strip().lower() for b in bold_terms}
    keywords = {k for k in keywords if len(k) >= 4}

    haystack = (source + " " + " ".join(_field_text_for_jargon(f) for f in live_fields)).lower()

    uncovered = []
    for kw in sorted(keywords):
        normalized = re.sub(r"[^a-z0-9]+", " ", kw).strip()
        if not normalized:
            continue
        significant = [w for w in normalized.split() if len(w) > 3]
        if not significant:
            continue
        if not any(w in haystack for w in significant):
            uncovered.append(kw)

    if uncovered:
        audit.add(
            "requirements_reference",
            "WARN",
            f"requirements_reference.md mentions topics with no apparent coverage in questions.json/rules.py: "
            f"{uncovered[:8]}{'...' if len(uncovered) > 8 else ''} (heuristic, manual review only)",
            location="",
        )


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------


def _clamp(value: float, lo: float = 0.0, hi: float = 10.0) -> float:
    return max(lo, min(hi, value))


STRUCTURAL_RULES = {
    "schema",
    "phantom_rule_key",
    "conditional_logic",
    "unused_question_key",
    "dead_requirement_code",
}
UX_RULES = {
    "escape_choices",
    "contact_sales_consent",
    "legal_jargon",
    "question_length",
    "question_complexity",
    "poor_choice_design",
    "acknowledgement_process",
}
DISCIPLINE_RULES = {
    "hard_failure_severity",
    "redundancy",
    "flow_size",
    "numeric_threshold_design",
    "question_order",
    "requirements_reference",
}


def compute_scores(audit: PathwayAudit) -> None:
    structural = 10.0
    ux = 10.0
    discipline = 10.0

    for finding in audit.findings:
        weight_fail = 3.0
        weight_warn = 0.4
        delta = weight_fail if finding.severity == "FAIL" else weight_warn

        if finding.rule in STRUCTURAL_RULES:
            structural -= delta
        if finding.rule in UX_RULES:
            ux -= delta if finding.severity == "FAIL" else 0.5
        if finding.rule in DISCIPLINE_RULES:
            discipline -= delta if finding.severity == "FAIL" else 0.6

    structural = _clamp(structural)
    ux = _clamp(ux)
    discipline = _clamp(discipline)
    overall = _clamp(round((structural + ux + discipline) / 3, 1))

    audit.scores = {
        "structural_correctness": round(structural, 1),
        "ux_alignment": round(ux, 1),
        "eligibility_flow_discipline": round(discipline, 1),
        "overall": overall,
    }


FAIL_STATUS_RULES = {
    "schema",
    "escape_choices",
    "contact_sales_consent",
    "phantom_rule_key",
    "conditional_logic",
}


def compute_status(audit: PathwayAudit) -> None:
    if any(f.severity == "FAIL" for f in audit.findings):
        audit.status = "FAIL"
    elif any(f.severity == "WARN" for f in audit.findings):
        audit.status = "PASS WITH WARNINGS"
    else:
        audit.status = "PASS"


# ---------------------------------------------------------------------------
# Top-level pathway audit
# ---------------------------------------------------------------------------


def audit_pathway(name: str) -> PathwayAudit:
    pathway_dir = PATHWAYS_DIR / name
    audit = PathwayAudit(pathway=name, directory=pathway_dir)

    try:
        questions_data, questions_err = load_json_file(pathway_dir / "questions.json")
        if questions_err:
            audit.add("schema", "FAIL", questions_err)
            questions_data = {}

        schema_ok = check_schema(audit, questions_data)
        live_fields = get_taxonomy_fields(questions_data) if isinstance(questions_data, dict) else []
        checklist_fields = get_checklist_fields(questions_data) if isinstance(questions_data, dict) else []

        known_keys = {f.get("key") for f in live_fields if isinstance(f.get("key"), str)}
        known_keys |= {f.get("key") for f in checklist_fields if isinstance(f.get("key"), str)}

        rules_path = pathway_dir / "rules.py"
        tree, rules_err, source = parse_rules_ast(rules_path)
        if rules_err:
            audit.add("schema", "FAIL", rules_err)

        analysis = RulesAnalysis(tree) if tree is not None else RulesAnalysis(ast.parse(""))

        clarifications_data, clar_err = load_json_file(pathway_dir / "clarifications.json")
        if clar_err:
            audit.add("schema", "WARN", clar_err)
        output_data, output_err = load_json_file(pathway_dir / "output.json")
        if output_err:
            audit.add("schema", "WARN", output_err)

        if schema_ok:
            check_escape_choices(audit, live_fields)
            check_acknowledgement_process_questions(audit, live_fields)
            check_contact_sales_consent(audit, live_fields, name)
            check_unused_question_keys(audit, live_fields, analysis)
            check_legal_jargon(audit, live_fields)
            check_length_and_complexity(audit, live_fields)
            check_poor_choice_design(audit, live_fields)
            check_conditional_logic(audit, live_fields, known_keys)
            check_question_order(audit, live_fields)
            check_redundancy(audit, live_fields)
            if tree is not None:
                check_numeric_threshold_design(audit, live_fields, analysis, source)

        check_phantom_rule_keys(audit, known_keys, analysis)
        check_dead_requirement_codes(audit, analysis, clarifications_data, output_data)
        check_hard_failure_severity(audit, analysis)

        metrics = compute_flow_metrics(live_fields)
        metrics["escape_choice_failures"] = sum(1 for f in audit.findings if f.rule == "escape_choices")
        metrics["unused_questions"] = sum(1 for f in audit.findings if f.rule == "unused_question_key")
        metrics["dead_codes"] = sum(1 for f in audit.findings if f.rule == "dead_requirement_code")
        metrics["hard_failure_concerns"] = sum(1 for f in audit.findings if f.rule == "hard_failure_severity")
        metrics["jargon_flags"] = sum(1 for f in audit.findings if f.rule == "legal_jargon")
        metrics["checklist_process_fields"] = len(checklist_fields)
        audit.metrics = metrics

        if schema_ok:
            check_flow_size(audit, metrics)
            check_requirements_reference(audit, pathway_dir, live_fields, source)

        if analysis.unresolved_reads:
            audit.limitations.append(
                f"{analysis.unresolved_reads} field read(s) in rules.py could not be statically resolved "
                "to a literal dotted key (dynamic construction beyond one level of indirection)."
            )
        if analysis.unresolved_appends:
            audit.limitations.append(
                f"{analysis.unresolved_appends} failed_requirements.append(...) call(s) in rules.py could not "
                "be statically resolved to a literal requirement code."
            )

    except Exception as exc:  # noqa: BLE001
        audit.add("audit_crash", "FAIL", f"audit tool raised an unexpected error auditing this pathway: {exc}")

    compute_scores(audit)
    compute_status(audit)
    return audit


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------


def render_console_table(audits: List[PathwayAudit]) -> str:
    headers = [
        "Pathway", "Status", "Questions", "Errors", "Warnings",
        "Escape", "Unused", "DeadCodes", "HardFail?", "Jargon", "Overall",
    ]
    rows = []
    for a in audits:
        rows.append([
            a.pathway,
            a.status,
            str(a.metrics.get("total_questions", "?")),
            str(len(a.fails())),
            str(len(a.warnings())),
            str(a.metrics.get("escape_choice_failures", 0)),
            str(a.metrics.get("unused_questions", 0)),
            str(a.metrics.get("dead_codes", 0)),
            str(a.metrics.get("hard_failure_concerns", 0)),
            str(a.metrics.get("jargon_flags", 0)),
            f"{a.scores.get('overall', 0):.1f}",
        ])

    widths = [max(len(h), *(len(r[i]) for r in rows)) if rows else len(h) for i, h in enumerate(headers)]
    lines = []
    lines.append(" | ".join(h.ljust(w) for h, w in zip(headers, widths)))
    lines.append("-+-".join("-" * w for w in widths))
    for r in rows:
        lines.append(" | ".join(c.ljust(w) for c, w in zip(r, widths)))
    return "\n".join(lines)


def _findings_by_severity(audit: PathwayAudit, severity: str) -> List[Finding]:
    return [f for f in audit.findings if f.severity == severity]


def render_pathway_markdown(audit: PathwayAudit) -> str:
    lines: List[str] = []
    lines.append(f"# {audit.pathway} -- Pathway Quality Audit")
    lines.append("")
    lines.append("## 1. Summary")
    lines.append("")
    lines.append(f"- **Status:** {audit.status}")
    lines.append(f"- **Structural correctness:** {audit.scores.get('structural_correctness')}/10")
    lines.append(f"- **UX alignment:** {audit.scores.get('ux_alignment')}/10")
    lines.append(f"- **Eligibility-flow discipline:** {audit.scores.get('eligibility_flow_discipline')}/10")
    lines.append(f"- **Overall:** {audit.scores.get('overall')}/10")
    lines.append(f"- **Errors (FAIL):** {len(audit.fails())}")
    lines.append(f"- **Warnings (FLAG):** {len(audit.warnings())}")
    lines.append("")

    lines.append("## 2. Errors")
    lines.append("")
    fails = _findings_by_severity(audit, "FAIL")
    if not fails:
        lines.append("_None._")
    else:
        for f in fails:
            loc = f" (`{f.location}`)" if f.location else ""
            lines.append(f"- **[{f.rule}]**{loc}: {f.message}")
    lines.append("")

    lines.append("## 3. Warnings")
    lines.append("")
    warns = _findings_by_severity(audit, "WARN")
    if not warns:
        lines.append("_None._")
    else:
        for f in warns:
            loc = f" (`{f.location}`)" if f.location else ""
            lines.append(f"- **[{f.rule}]**{loc}: {f.message}")
    lines.append("")

    lines.append("## 4. Question-by-Question Findings")
    lines.append("")
    question_rules = {
        "escape_choices", "acknowledgement_process", "contact_sales_consent",
        "unused_question_key", "legal_jargon", "question_length",
        "question_complexity", "poor_choice_design", "conditional_logic",
        "question_order",
    }
    by_location: Dict[str, List[Finding]] = defaultdict(list)
    for f in audit.findings:
        if f.rule in question_rules and f.location:
            by_location[f.location].append(f)
    if not by_location:
        lines.append("_No per-question findings._")
    else:
        for loc in sorted(by_location):
            lines.append(f"### `{loc}`")
            for f in by_location[loc]:
                lines.append(f"- **[{f.severity}/{f.rule}]** {f.message}")
            lines.append("")

    lines.append("## 5. Rule-Layer Findings")
    lines.append("")
    rule_layer_rules = {"phantom_rule_key", "hard_failure_severity", "numeric_threshold_design"}
    layer_findings = [f for f in audit.findings if f.rule in rule_layer_rules]
    if not layer_findings:
        lines.append("_None._")
    else:
        for f in layer_findings:
            loc = f" (`{f.location}`)" if f.location else ""
            lines.append(f"- **[{f.severity}/{f.rule}]**{loc}: {f.message}")
    lines.append("")

    lines.append("## 6. Dead Code Findings")
    lines.append("")
    dead = [f for f in audit.findings if f.rule == "dead_requirement_code"]
    if not dead:
        lines.append("_None._")
    else:
        for f in dead:
            lines.append(f"- `{f.location}`: {f.message}")
    lines.append("")

    lines.append("## 7. Flow Metrics")
    lines.append("")
    for k, v in audit.metrics.items():
        lines.append(f"- **{k}:** {v}")
    lines.append("")

    lines.append("## 8. Costa Rica DNV Alignment")
    lines.append("")
    total = audit.metrics.get("total_questions", 0)
    lines.append(
        f"- Costa Rica DNV benchmark: ~{FLOW_SIZE_BENCHMARK_QUESTIONS} questions for a typical individual flow."
    )
    lines.append(f"- This pathway: {total} live questions ({audit.metrics.get('conditional_questions', 0)} conditional).")
    flow_findings = [f for f in audit.findings if f.rule == "flow_size"]
    if flow_findings:
        for f in flow_findings:
            lines.append(f"- {f.message}")
    else:
        lines.append("- No flow-size concern flagged relative to the benchmark.")
    lines.append("")

    lines.append("## 9. Recommended Manual-Review Items")
    lines.append("")
    manual_review_rules = {"acknowledgement_process", "requirements_reference", "redundancy"}
    manual = [f for f in audit.findings if f.rule in manual_review_rules]
    if not manual:
        lines.append("_None._")
    else:
        for f in manual:
            loc = f" (`{f.location}`)" if f.location else ""
            lines.append(f"- **[{f.rule}]**{loc}: {f.message}")
    lines.append("")

    if audit.limitations:
        lines.append("## Limitations / Heuristics Applied")
        lines.append("")
        for note in audit.limitations:
            lines.append(f"- {note}")
        lines.append("")

    return "\n".join(lines)


def render_summary_markdown(audits: List[PathwayAudit]) -> str:
    ranked = sorted(audits, key=lambda a: a.scores.get("overall", 0), reverse=True)
    lines: List[str] = []
    lines.append("# QIQ Pathway Quality Audit -- Summary")
    lines.append("")
    lines.append(
        f"Benchmark: Costa Rica DNV (hardcoded, not file-based) -- lean eligibility-only flow, "
        f"~{FLOW_SIZE_BENCHMARK_QUESTIONS} questions for a typical individual flow."
    )
    lines.append("")
    lines.append("Ranked best to worst by overall score:")
    lines.append("")
    lines.append("| Rank | Pathway | Status | Overall | Structural | UX | Discipline | Errors | Warnings |")
    lines.append("|---|---|---|---|---|---|---|---|---|")
    for i, a in enumerate(ranked, start=1):
        lines.append(
            f"| {i} | {a.pathway} | {a.status} | {a.scores.get('overall')} | "
            f"{a.scores.get('structural_correctness')} | {a.scores.get('ux_alignment')} | "
            f"{a.scores.get('eligibility_flow_discipline')} | {len(a.fails())} | {len(a.warnings())} |"
        )
    lines.append("")
    lines.append("See `docs/pathway_quality_audit/<pathway>.md` for full detail on each pathway.")
    lines.append("")
    return "\n".join(lines)


def write_reports(audits: List[PathwayAudit]) -> None:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    for audit in audits:
        report_path = REPORT_DIR / f"{audit.pathway}.md"
        report_path.write_text(render_pathway_markdown(audit), encoding="utf-8")
    (REPORT_DIR / "summary.md").write_text(render_summary_markdown(audits), encoding="utf-8")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def run_audit(pathway: Optional[str] = None) -> List[PathwayAudit]:
    names = [pathway] if pathway else discover_pathways()
    return [audit_pathway(name) for name in names]


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Audit QIQ file-based pathways for question-flow quality.")
    parser.add_argument("--pathway", help="Audit a single pathway by directory name (e.g. italy_dnv).")
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON instead of a table.")
    parser.add_argument("--strict", action="store_true", help="Exit nonzero on warnings as well as failures.")
    parser.add_argument(
        "--no-reports",
        action="store_true",
        help="Skip writing docs/pathway_quality_audit/ markdown reports (still prints console/JSON output).",
    )
    args = parser.parse_args(argv)

    if args.pathway:
        pathway_dir = PATHWAYS_DIR / args.pathway
        if not (pathway_dir / "questions.json").exists():
            print(f"error: no questions.json found for pathway '{args.pathway}' under {PATHWAYS_DIR}", file=sys.stderr)
            return 2

    audits = run_audit(args.pathway)

    if not audits:
        print("error: no file-based pathways discovered", file=sys.stderr)
        return 2

    if not args.no_reports:
        write_reports(audits)

    if args.json:
        print(json.dumps([a.to_dict() for a in audits], indent=2))
    else:
        print(render_console_table(audits))
        print()
        for a in audits:
            if a.limitations:
                print(f"[{a.pathway}] limitations: {'; '.join(a.limitations)}")

    any_fail = any(a.status == "FAIL" for a in audits)
    any_warn = any(a.status == "PASS WITH WARNINGS" for a in audits)

    if any_fail:
        return 1
    if args.strict and any_warn:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
