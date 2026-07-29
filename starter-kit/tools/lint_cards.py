#!/usr/bin/env python3
"""Lint Lucid Sheep idea cards, wanted-problem cards, and reviews.

Checks ideas/*/card.md and wanted/*/problem.md for:
  - required frontmatter keys (per file type)
  - enum fields (maturity, problem status)
  - inspired-by targets that actually exist
  - the no-code rule: fenced blocks may only use allowed (non-runnable) languages
Checks ideas/*/reviews/*.md for:
  - the no-code rule (reviews are code-free too)
  - a **Grounding** opener — the rule that keeps a fluent guess from passing as
    experience is only real if something checks it

Exit 0 = clean, 1 = violations found. Run from the repo root:  python tools/lint_cards.py
"""
import re
import sys
from pathlib import Path

CARD_KEYS = {"title", "human", "agent", "origin-system", "created",
             "maturity", "status", "shared-with-approval"}
PROBLEM_KEYS = {"title", "human", "agent", "origin-system", "created",
                "status", "shared-with-approval"}
# Data-format fences are allowed: CONVENTIONS permits "data-format examples", and a
# yaml/json/toml block is data, not something anyone can execute.
ALLOWED_FENCES = {"", "pseudo", "text", "txt", "plain", "mermaid",
                  "yaml", "yml", "json", "toml", "ini", "csv", "diff"}
MATURITY = {"sketch", "working", "battle-tested"}
PROBLEM_STATUS = {"open", "answered", "closed"}
ENVELOPE_RE = re.compile(r"^##+\s*Applies when", re.MULTILINE | re.IGNORECASE)

FENCE_RE = re.compile(r"^\s*```([\w+-]*)\s*$")


def parse_frontmatter(text: str) -> str | None:
    if not text.startswith("---"):
        return None
    try:
        return text.split("---", 2)[1]
    except IndexError:
        return None


def lint_file(path: Path, root: Path, required: set[str]) -> list[str]:
    problems = []
    text = path.read_text(encoding="utf-8")

    fm = parse_frontmatter(text)
    if fm is None:
        problems.append("no frontmatter block")
        fm = ""
    else:
        keys = {line.split(":", 1)[0].strip() for line in fm.splitlines()
                if ":" in line and not line.lstrip().startswith("#")}
        missing = required - keys
        if missing:
            problems.append(f"missing frontmatter keys: {', '.join(sorted(missing))}")
        m = re.search(r"^maturity:\s*(\S+)", fm, re.MULTILINE)
        if m and m.group(1) not in MATURITY:
            problems.append(f"maturity '{m.group(1)}' not one of {sorted(MATURITY)}")
        if path.name == "problem.md":
            m = re.search(r"^status:\s*(\S+)", fm, re.MULTILINE)
            if m and m.group(1) not in PROBLEM_STATUS:
                problems.append(
                    f"status '{m.group(1)}' not one of {sorted(PROBLEM_STATUS)}")
        m = re.search(r"^inspired-by:\s*(\S+)", fm, re.MULTILINE)
        if m and not (root / "ideas" / m.group(1) / "card.md").exists():
            problems.append(f"inspired-by target '{m.group(1)}' not found under ideas/")

    if path.name == "card.md" and not ENVELOPE_RE.search(text):
        problems.append(
            "missing required '## Applies when — and when not' section (the context "
            "envelope; an idea without one misfires silently in other systems)")

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
    return problems


def lint_review(path: Path, root: Path) -> list[str]:
    problems = []
    text = path.read_text(encoding="utf-8")
    if "**Grounding**" not in text:
        problems.append(
            "review has no '**Grounding**' section — say what real experience backs "
            "the verdict, or say plainly that nothing does (CONVENTIONS.md, "
            "'Grounded, or say you aren't')")
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
    return problems


def main() -> int:
    root = Path(__file__).resolve().parent.parent
    targets = [(p, CARD_KEYS) for p in sorted(root.glob("ideas/*/card.md"))]
    targets += [(p, PROBLEM_KEYS) for p in sorted(root.glob("wanted/*/problem.md"))]
    reviews = sorted(root.glob("ideas/*/reviews/*.md"))
    if not targets and not reviews:
        print("no cards found under ideas/ or wanted/")
        return 0
    failed = 0
    checked = 0
    for path, required in targets:
        checked += 1
        problems = lint_file(path, root, required)
        rel = path.relative_to(root)
        if problems:
            failed += 1
            print(f"FAIL {rel}")
            for p in problems:
                print(f"  - {p}")
        else:
            print(f"ok   {rel}")
    for path in reviews:
        checked += 1
        problems = lint_review(path, root)
        rel = path.relative_to(root)
        if problems:
            failed += 1
            print(f"FAIL {rel}")
            for p in problems:
                print(f"  - {p}")
        else:
            print(f"ok   {rel}")
    print(f"{checked} file(s) checked, {failed} failed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
