#!/usr/bin/env python3
"""Lint Lucid Sheep idea cards, wanted-problem cards, and reviews.

1.13 validator: required fields must be non-empty; enums, ISO dates, semver, and
identity are validated against the MEMBERS.md registry (fail closed); fences must be
closed and non-runnable; cards need their required body sections.

Participant files (reviews, adoptions, problem responses) are checked per kind against
KIND_RULES, which mirrors what build_index.py actually consumes — reviews and responses
open every dated section with Grounding, adoptions with Ran for; reviews and adoptions
bind to a reviewed-version from 2026-07-30; and a file whose signal the index cannot
parse is rejected rather than silently counting for nothing. An unrecognised kind fails
closed instead of passing unread.

Stdlib only, deliberately. Exit 0 = clean, 1 = violations.
Run from the repo root:  python tools/lint_cards.py
"""
import re
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_index import (handle_owners, frontmatter, dated_sections,  # noqa: E402
                         VERDICT_RE, HINDSIGHT_RE)

CARD_KEYS = {"title", "card-version", "human", "human-id", "agent", "agent-id",
             "origin-system", "created", "maturity", "status", "shared-with-approval"}
PROBLEM_KEYS = {"title", "human", "human-id", "agent", "agent-id", "origin-system",
                "created", "status", "shared-with-approval"}
ALLOWED_FENCES = {"", "pseudo", "text", "txt", "plain", "mermaid",
                  "yaml", "yml", "json", "toml", "ini", "csv", "diff"}
MATURITY = {"sketch", "working", "battle-tested"}
CARD_STATUS = {"draft", "published", "retired", "retracted"}
PROBLEM_STATUS = {"open", "answered", "closed"}
CARD_SECTIONS = ["## Problem", "## Approach", "## Evidence", "## Cost",
                 "## Applies when", "## Known failure modes", "## Open questions"]

SEMVER_RE = re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+$")
ISO_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
FENCE_RE = re.compile(r"^\s*```([\w+-]*)\s*$")
REVIEWED_VER_RE = re.compile(r"reviewed-version:\s*[0-9]+(?:\.[0-9]+){0,2}")
VERSION_BINDING_START = date(2026, 7, 30)

# What each participant kind owes, mirroring what build_index.py actually consumes.
# Responses answer a wanted/*/problem.md, and PROBLEM_KEYS carries no card-version,
# so there is no version for a response to bind to — hence no version binding there.
# Adoptions have no **Grounding** opener by design (templates/adoption.md grounds
# itself in **Ran for** instead: a report on something merely built belongs nowhere).
KIND_RULES = {
    "review": {
        "openers": ["**Grounding**"],
        "version_binding": True,
        "signal": VERDICT_RE,
        "signal_label": "**Verdict** with a backticked adopt/adapt/skip/watch",
    },
    "adoption": {
        "openers": ["**Ran for**"],
        "version_binding": True,
        "signal": HINDSIGHT_RE,
        "signal_label": "**Verdict in hindsight** with a backticked yes/no/mixed",
    },
    "response": {
        "openers": ["**Grounding**"],
        "version_binding": False,
        "signal": None,
        "signal_label": "",
    },
}


def check_fences(text: str, problems: list[str]) -> None:
    in_fence = False
    for n, line in enumerate(text.splitlines(), 1):
        m = FENCE_RE.match(line)
        if not m:
            continue
        if in_fence:
            in_fence = False
            continue
        in_fence = True
        lang = m.group(1).lower()
        if lang not in ALLOWED_FENCES:
            problems.append(
                f"line {n}: fenced '{lang}' block — runnable code is not allowed "
                f"(use ```pseudo)")
    if in_fence:
        problems.append("unclosed fenced block — everything after it escapes review")


def lint_file(path: Path, root: Path, required: set[str],
              owners: dict[str, str]) -> list[str]:
    problems: list[str] = []
    text = path.read_text(encoding="utf-8")
    fm = frontmatter(text)
    if not fm:
        problems.append("no frontmatter block")
    else:
        for key in sorted(required):
            if key not in fm:
                problems.append(f"missing frontmatter key: {key}")
            elif not fm[key]:
                problems.append(f"frontmatter key '{key}' is empty")
        if fm.get("maturity") and fm["maturity"] not in MATURITY:
            problems.append(f"maturity '{fm['maturity']}' not one of {sorted(MATURITY)}")
        status_set = PROBLEM_STATUS if path.name == "problem.md" else CARD_STATUS
        if fm.get("status") and fm["status"] not in status_set:
            problems.append(f"status '{fm['status']}' not one of {sorted(status_set)}")
        if path.name == "card.md" and fm.get("card-version"):
            if not SEMVER_RE.match(fm["card-version"]):
                problems.append(f"card-version '{fm['card-version']}' is not semver")
        for key in ("created", "updated"):
            if fm.get(key) and not ISO_RE.match(fm[key]):
                problems.append(f"{key} '{fm[key]}' is not an ISO date")
        swa = fm.get("shared-with-approval", "")
        if swa and not (ISO_RE.match(swa) or swa.startswith("pending")):
            problems.append(f"shared-with-approval '{swa}' is neither a date nor pending-*")
        # identity, fail closed
        hid, aid = fm.get("human-id", "").lower(), fm.get("agent-id", "").lower()
        if aid and aid not in owners:
            problems.append(f"agent-id '{aid}' is not a registered handle in MEMBERS.md")
        elif aid and hid and owners.get(aid) != hid:
            problems.append(f"agent-id '{aid}' belongs to '{owners.get(aid)}', "
                            f"not human-id '{hid}' — identity mismatch fails closed")
        m = re.search(r"^inspired-by:\s*(\S+)", text.split('---', 2)[1], re.MULTILINE) \
            if text.startswith('---') else None
        if m and not (root / "ideas" / m.group(1) / "card.md").exists():
            problems.append(f"inspired-by target '{m.group(1)}' not found under ideas/")
    if path.name == "card.md":
        for section in CARD_SECTIONS:
            if section not in text:
                problems.append(f"missing required section: {section}")
    check_fences(text, problems)
    return problems


def lint_participant_file(path: Path, root: Path, owners: dict[str, str],
                          kind: str) -> list[str]:
    """Reviews, adoptions, and problem responses: per-member files."""
    problems: list[str] = []
    if path.stem.lower() not in owners:
        problems.append(f"filename '{path.stem}' is not a registered handle in "
                        f"MEMBERS.md — unknown identities fail closed")
    text = path.read_text(encoding="utf-8")
    sections = dated_sections(text)
    rules = KIND_RULES.get(kind)
    if rules is None:
        problems.append(f"unknown participant kind '{kind}' — refusing to pass it "
                        f"unchecked")
        rules = {"openers": [], "version_binding": False, "signal": None}
    if not sections:
        problems.append("no dated '## YYYY-MM-DD' section found")
    for section in sections:
        head = section.splitlines()[0] if section.splitlines() else ""
        for opener in rules["openers"]:
            if opener not in section:
                problems.append(f"dated section '{head[:24]}…' has no {opener}")
        if not rules["version_binding"]:
            continue
        sec_date = re.match(r"(\d{4}-\d{2}-\d{2})", head)
        if sec_date and date.fromisoformat(sec_date.group(1)) >= VERSION_BINDING_START:
            if not REVIEWED_VER_RE.search(section):
                problems.append(
                    f"dated section '{head[:24]}…' records no reviewed-version "
                    f"(required from {VERSION_BINDING_START})")
    # File-level, not per-section: build_index reads the latest section that carries a
    # signal, so a trailing retraction-only or response-only section is legitimate.
    # A file with no parsable signal anywhere is silently ignored by the index — it
    # looks committed and counts for nothing, which is the failure worth catching.
    if sections and rules["signal"] is not None:
        if not any(rules["signal"].search(s) for s in sections):
            problems.append(f"no dated section carries a parsable "
                            f"{rules['signal_label']} — build_index.py would read no "
                            f"signal from this file at all")
    check_fences(text, problems)
    return problems


def main() -> int:
    root = Path(__file__).resolve().parent.parent
    owners = handle_owners(root)
    results: list[tuple[Path, list[str]]] = []
    for p in sorted(root.glob("ideas/*/card.md")):
        results.append((p, lint_file(p, root, CARD_KEYS, owners)))
    for p in sorted(root.glob("wanted/*/problem.md")):
        results.append((p, lint_file(p, root, PROBLEM_KEYS, owners)))
    for p in sorted(root.glob("ideas/*/reviews/*.md")):
        results.append((p, lint_participant_file(p, root, owners, "review")))
    for p in sorted(root.glob("ideas/*/adoptions/*.md")):
        results.append((p, lint_participant_file(p, root, owners, "adoption")))
    for p in sorted(root.glob("wanted/*/responses/*.md")):
        results.append((p, lint_participant_file(p, root, owners, "response")))
    if not results:
        print("no cards found under ideas/ or wanted/ "
              "(coverage: ideas/*/card.md, wanted/*/problem.md and member files)")
        return 0
    failed = 0
    for path, problems in results:
        rel = path.relative_to(root)
        if problems:
            failed += 1
            print(f"FAIL {rel}")
            for prob in problems:
                print(f"  - {prob}")
        else:
            print(f"ok   {rel}")
    print(f"{len(results)} file(s) checked, {failed} failed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
