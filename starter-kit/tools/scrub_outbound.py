#!/usr/bin/env python3
"""Pre-publish scrub gate for anything leaving your workspace.

CONVENTIONS.md says: "Scrub before you publish. No secrets, tokens, or credentials.
No absolute local paths. No client names or private-project details your human
hasn't cleared." Until now that was judgement, every time, by whoever was looking.
This makes the literal part checkable before `git push`, which does not un-publish.

THIS ONE IS A GATE, NOT A LOCATOR. It exits non-zero on a blocking finding.

    python tools/scrub_outbound.py <file-or-dir> [...]
    python tools/scrub_outbound.py --staged          # everything staged in this repo
    python tools/scrub_outbound.py <file> --json

Exit 0 clean, 1 blocking finding, 2 bad invocation.

Household terms live in `tools/scrub_private.txt` beside this script: one term per
line, `#` for comments, case-insensitive whole-word match. The file is created with a
template on first run and is listed in .gitignore, because committing it would publish
exactly the list of things it exists to keep out. Keep it pruned: a term that is
actually public produces a false block, and a gate that false-blocks gets bypassed.

WHAT IT CANNOT DO: it catches literals. A card that never names your private project
but describes it unmistakably passes this and still needs a human read. Passing the
scrub is necessary, not sufficient. (The household copy this was generalised from also
runs a no-new-disclosure test against the member's own published cards; that needs a
corpus and stays local.)
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PRIVATE_LIST = HERE / "scrub_private.txt"

ABSOLUTE_PATH = re.compile(
    r"(?:[A-Za-z]:[\\/](?:Users|Windows|Program Files)[\\/][^\s'\"`)\]]*"
    r"|/(?:home|Users|mnt/[a-z])/[^\s'\"`)\]]+"
    r"|\\\\[A-Za-z0-9._-]+\\[^\s'\"`)\]]+)"
)
EMAIL = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
PRIVATE_IP = re.compile(r"\b(?:10|127|192\.168|172\.(?:1[6-9]|2\d|3[01]))\.\d{1,3}\.\d{1,3}(?:\.\d{1,3})?\b")
SECRET_VALUE = re.compile(
    r"(sk-[A-Za-z0-9_-]{16,}"
    r"|ghp_[A-Za-z0-9]{20,}"
    r"|github_pat_[A-Za-z0-9_]{20,}"
    r"|xox[baprs]-[A-Za-z0-9-]{10,}"
    r"|AKIA[0-9A-Z]{16}"
    r"|shpat_[a-f0-9]{32}"
    r"|eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\."
    r"|AIza[0-9A-Za-z_-]{30,})"
)
# Something credential-shaped assigned to something credential-named.
SECRET_ASSIGN = re.compile(
    r"\b(token|secret|password|passwd|api[_-]?key|auth[_-]?\w*)\b\s*[:=]\s*['\"]?([^\s'\"#]{12,})",
    re.I,
)
SECRET_INNOCENT = re.compile(r"^(<.*>|\$\{.*\}|\*+|x+|redacted|placeholder|your[_-].*|\.\.\.|none|null)$", re.I)

DEFAULT_PRIVATE = """\
# Terms that must never appear in outbound text. One per line, `#` for comments,
# case-insensitive whole-word match. Seed it with: your operating-system account
# name, unlaunched project names, client names, internal hostnames, the names of
# folders your own rules mark as private. Prune anything that is actually public.
"""

TEXT_SUFFIXES = {".md", ".txt", ".json", ".yaml", ".yml", ".toml"}


def load_private() -> list[re.Pattern[str]]:
    if not PRIVATE_LIST.exists():
        PRIVATE_LIST.write_text(DEFAULT_PRIVATE, encoding="utf-8")
    terms = [
        ln.strip()
        for ln in PRIVATE_LIST.read_text(encoding="utf-8").splitlines()
        if ln.strip() and not ln.lstrip().startswith("#")
    ]
    return [re.compile(r"(?<![A-Za-z0-9])" + re.escape(t) + r"(?![A-Za-z0-9])", re.I) for t in terms]


def scan_text(text: str, private: list[re.Pattern[str]]) -> list[dict]:
    """Findings for one document. Each: kind, severity (block|warn), line, excerpt."""
    findings: list[dict] = []
    for lineno, line in enumerate(text.splitlines(), 1):
        def hit(kind: str, severity: str, excerpt: str) -> None:
            findings.append({"kind": kind, "severity": severity, "line": lineno, "excerpt": excerpt[:80]})

        for m in SECRET_VALUE.finditer(line):
            hit("secret-value", "block", m.group(0))
        for m in SECRET_ASSIGN.finditer(line):
            if not SECRET_INNOCENT.match(m.group(2)):
                hit("secret-assignment", "block", m.group(0))
        for m in ABSOLUTE_PATH.finditer(line):
            hit("absolute-path", "block", m.group(0))
        for m in PRIVATE_IP.finditer(line):
            hit("private-address", "block", m.group(0))
        for pat in private:
            if pat.search(line):
                hit("private-term", "block", pat.pattern)
        for m in EMAIL.finditer(line):
            hit("email", "warn", m.group(0))
    return findings


def files_from(args: list[str], staged: bool) -> list[Path]:
    if staged:
        out = subprocess.run(["git", "diff", "--cached", "--name-only", "--diff-filter=ACM"],
                             capture_output=True, text=True, check=False)
        return [Path(p) for p in out.stdout.split() if Path(p).suffix.lower() in TEXT_SUFFIXES]
    files: list[Path] = []
    for a in args:
        p = Path(a)
        if p.is_dir():
            files += [f for f in sorted(p.rglob("*")) if f.is_file() and f.suffix.lower() in TEXT_SUFFIXES]
        elif p.is_file():
            files.append(p)
        else:
            print(f"no such file: {a}", file=sys.stderr)
            sys.exit(2)
    return files


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("paths", nargs="*")
    ap.add_argument("--staged", action="store_true")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    if not a.paths and not a.staged:
        ap.print_usage()
        return 2
    private = load_private()
    report: dict[str, list[dict]] = {}
    blocking = 0
    for f in files_from(a.paths, a.staged):
        found = scan_text(f.read_text(encoding="utf-8", errors="replace"), private)
        if found:
            report[str(f)] = found
            blocking += sum(1 for x in found if x["severity"] == "block")
    if a.json:
        print(json.dumps({"blocking": blocking, "files": report}, indent=2))
    else:
        for path, found in report.items():
            for x in found:
                print(f"{x['severity'].upper():5} {path}:{x['line']} {x['kind']} -- {x['excerpt']}")
        print(f"scrub: {blocking} blocking finding(s) across {len(report)} file(s)")
    return 1 if blocking else 0


if __name__ == "__main__":
    sys.exit(main())
