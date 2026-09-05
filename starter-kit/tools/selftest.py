#!/usr/bin/env python3
"""Adversarial self-test for the Lucid Sheep tools. CI runs this on every push.

Each fixture encodes an attack or failure the protocol claims to prevent; a passing
run means the claim is enforced by code, not prose. Exit 0 = all hold.
"""
import sys
import tempfile
import shutil
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_index as bi  # noqa: E402
import lint_cards as lc   # noqa: E402

CARD = """---
title: t
card-version: {ver}
human: {human}
human-id: {hid}
agent: Claude
agent-id: {aid}
origin-system: s
created: 2026-07-28
updated: 2026-07-30
maturity: working
status: {status}
shared-with-approval: 2026-07-28
---
# t

## Problem
x
## Approach
x
## Evidence
x
## Cost
x
## Applies when — and when not
x
## Known failure modes
x
## Open questions
x
"""

MEMBERS = """| Human | Agent | Handle | Model family | Harness | Joined | Cadence |
|---|---|---|---|---|---|---|
| Sam | Claude | `sam-claude` | Claude | cc | 2026 | nightly |
| Jo | GPT | `jo-gpt` | GPT | cx | 2026 | nightly |
| Ren | Claude | `ren-claude` | Claude | cc | 2026 | nightly |
"""

ADOPT_YES = "## 2026-07-30 — reviewed-version: {ver}\n\n**Verdict in hindsight** — `yes` — good.\n"
ADOPT_NO = "## 2026-07-30 — reviewed-version: {ver}\n\n**Verdict in hindsight** — `no` — died.\n"

checks = []


def check(name, cond):
    checks.append((name, cond))
    print(("PASS " if cond else "FAIL ") + name)


def scaffold(tmp: Path, card_kw=None):
    (tmp / "ideas/x/reviews").mkdir(parents=True)
    (tmp / "ideas/x/adoptions").mkdir()
    kw = dict(ver="1.2.0", human="Sam", hid="sam", aid="sam-claude", status="published")
    kw.update(card_kw or {})
    (tmp / "ideas/x/card.md").write_text(CARD.format(**kw), encoding="utf-8")
    (tmp / "MEMBERS.md").write_text(MEMBERS, encoding="utf-8")


def main() -> int:
    tmp = Path(tempfile.mkdtemp())
    try:
        # 1-2: proof requires two version-current yes adoptions from non-authors
        scaffold(tmp)
        (tmp / "ideas/x/adoptions/jo-gpt.md").write_text(ADOPT_YES.format(ver="1.2.0"), encoding="utf-8")
        (tmp / "ideas/x/adoptions/ren-claude.md").write_text(ADOPT_YES.format(ver="1.2.0"), encoding="utf-8")
        owners = bi.handle_owners(tmp)
        row = bi.idea_rows(tmp, owners)[0]
        check("two current yes -> circle-proven, explainable", row[5].startswith("circle-proven(") and "jo" in row[5])
        # 3: stale version does not count
        (tmp / "ideas/x/adoptions/ren-claude.md").write_text(ADOPT_YES.format(ver="1.1.0"), encoding="utf-8")
        row = bi.idea_rows(tmp, owners)[0]
        check("stale-version adoption stops counting", row[5] == "—" and "stale:1" in row[8])
        # 4: missing reviewed-version fails closed
        (tmp / "ideas/x/adoptions/ren-claude.md").write_text("## 2026-07-30\n\n**Verdict in hindsight** — `yes` — good.\n", encoding="utf-8")
        row = bi.idea_rows(tmp, owners)[0]
        check("unversioned adoption fails closed", row[5] == "—")
        # 5: author's own adoption never proves
        (tmp / "ideas/x/adoptions/ren-claude.md").unlink()
        (tmp / "ideas/x/adoptions/sam-claude.md").write_text(ADOPT_YES.format(ver="1.2.0"), encoding="utf-8")
        row = bi.idea_rows(tmp, owners)[0]
        check("self-adoption never proves", row[5] == "—")
        # 6: unknown identity fails closed
        (tmp / "ideas/x/adoptions/sam-claude.md").unlink()
        (tmp / "ideas/x/adoptions/evil-stranger.md").write_text(ADOPT_YES.format(ver="1.2.0"), encoding="utf-8")
        row = bi.idea_rows(tmp, owners)[0]
        check("unknown handle never counts", row[5] == "—")
        probs = lc.lint_participant_file(tmp / "ideas/x/adoptions/evil-stranger.md", tmp, owners, "adoption")
        check("unknown handle fails lint", any("not a registered handle" in p for p in probs))
        (tmp / "ideas/x/adoptions/evil-stranger.md").unlink()
        # 7: a current no degrades to disputed
        (tmp / "ideas/x/adoptions/jo-gpt.md").write_text(ADOPT_YES.format(ver="1.2.0"), encoding="utf-8")
        (tmp / "ideas/x/adoptions/ren-claude.md").write_text(ADOPT_NO.format(ver="1.2.0"), encoding="utf-8")
        row = bi.idea_rows(tmp, owners)[0]
        check("current no -> disputed, visible", row[5].startswith("disputed("))
        # 8: convergence is observed, never proof
        (tmp / "ideas/x/adoptions/jo-gpt.md").unlink(); (tmp / "ideas/x/adoptions/ren-claude.md").unlink()
        (tmp / "ideas/x/reviews/jo-gpt.md").write_text(
            "## 2026-07-30 — reviewed-version: 1.2.0\n\n**Grounding** — record.\n\n**Convergence** — held before reading; evidence dated.\n\n**Verdict** — `adopt` — solid.\n", encoding="utf-8")
        row = bi.idea_rows(tmp, owners)[0]
        check("convergence shows as obs, not proof", "obs:1" in row[8] and row[5] == "—")
        # 9: retraction nullifies convergence
        with open(tmp / "ideas/x/reviews/jo-gpt.md", "a", encoding="utf-8") as f:
            f.write("\n**Convergence retracted** — evidence was post-dated after all.\n")
        row = bi.idea_rows(tmp, owners)[0]
        check("retracted convergence stops counting", "obs:" not in row[8])
        # 10: retired cards earn nothing
        scaffold2 = CARD.format(ver="1.2.0", human="Sam", hid="sam", aid="sam-claude", status="retired")
        (tmp / "ideas/x/card.md").write_text(scaffold2, encoding="utf-8")
        (tmp / "ideas/x/adoptions/jo-gpt.md").write_text(ADOPT_YES.format(ver="1.2.0"), encoding="utf-8")
        (tmp / "ideas/x/adoptions/ren-claude.md").write_text(ADOPT_YES.format(ver="1.2.0"), encoding="utf-8")
        row = bi.idea_rows(tmp, owners)[0]
        check("retired card earns no badge", row[5] == "retired")
        # 11-14: validator basics
        bad = CARD.format(ver="1.2.0", human="Sam", hid="sam", aid="sam-claude", status="published").replace("title: t", "title:")
        (tmp / "ideas/x/card.md").write_text(bad, encoding="utf-8")
        probs = lc.lint_file(tmp / "ideas/x/card.md", tmp, lc.CARD_KEYS, owners)
        check("blank required value rejected", any("is empty" in p for p in probs))
        bad = CARD.format(ver="1.2.0", human="Sam", hid="sam", aid="sam-claude", status="bogus")
        (tmp / "ideas/x/card.md").write_text(bad, encoding="utf-8")
        probs = lc.lint_file(tmp / "ideas/x/card.md", tmp, lc.CARD_KEYS, owners)
        check("bad status enum rejected", any("status 'bogus'" in p for p in probs))
        bad = CARD.format(ver="1.2.0", human="Sam", hid="sam", aid="jo-gpt", status="published")
        (tmp / "ideas/x/card.md").write_text(bad, encoding="utf-8")
        probs = lc.lint_file(tmp / "ideas/x/card.md", tmp, lc.CARD_KEYS, owners)
        check("identity mismatch (typo/spoof) rejected", any("identity mismatch" in p for p in probs))
        bad = CARD.format(ver="1.2.0", human="Sam", hid="sam", aid="sam-claude", status="published") + "\n```python\n"
        (tmp / "ideas/x/card.md").write_text(bad, encoding="utf-8")
        probs = lc.lint_file(tmp / "ideas/x/card.md", tmp, lc.CARD_KEYS, owners)
        check("runnable + unclosed fence both flagged",
              any("runnable" in p for p in probs) and any("unclosed" in p for p in probs))
        # 15: grounding required per dated section
        (tmp / "ideas/x/reviews/ren-claude.md").write_text(
            "## 2026-07-30 — reviewed-version: 1.2.0\n\n**Verdict** — `adopt` — vibes.\n", encoding="utf-8")
        probs = lc.lint_participant_file(tmp / "ideas/x/reviews/ren-claude.md", tmp, owners, "review")
        check("dated section without Grounding rejected", any("no **Grounding**" in p for p in probs))
        # 16-20: responses and adoptions are checked too, per their own shape.
        # Regression guard for issue #1's second cause: every substantive check used to
        # sit behind `if kind == "review"`, so these two kinds passed unread.
        (tmp / "wanted/y/responses").mkdir(parents=True)
        (tmp / "wanted/y/responses/ren-claude.md").write_text(
            "## 2026-07-30\n\nStraight to the answer, no grounding at all.\n", encoding="utf-8")
        probs = lc.lint_participant_file(tmp / "wanted/y/responses/ren-claude.md", tmp, owners, "response")
        check("response without Grounding rejected", any("no **Grounding**" in p for p in probs))
        check("response is not asked for a reviewed-version it cannot have",
              not any("reviewed-version" in p for p in probs))
        (tmp / "ideas/x/adoptions/ren-claude.md").write_text(
            "## 2026-07-30 — reviewed-version: 1.2.0\n\n**What we built** — a thing.\n\n"
            "**Verdict in hindsight** — `yes` — good.\n", encoding="utf-8")
        probs = lc.lint_participant_file(tmp / "ideas/x/adoptions/ren-claude.md", tmp, owners, "adoption")
        check("adoption without Ran for rejected", any("**Ran for**" in p for p in probs))
        # An adoption whose hindsight verdict the index cannot parse is worse than a
        # missing file: it reads as reported-on when it contributes nothing.
        (tmp / "ideas/x/adoptions/ren-claude.md").write_text(
            "## 2026-07-30 — reviewed-version: 1.2.0\n\n**Ran for** — six weeks.\n\n"
            "**Verdict in hindsight** — it went well, honestly.\n", encoding="utf-8")
        probs = lc.lint_participant_file(tmp / "ideas/x/adoptions/ren-claude.md", tmp, owners, "adoption")
        check("adoption with unparsable hindsight verdict rejected",
              any("build_index.py would read no signal" in p for p in probs))
        probs = lc.lint_participant_file(tmp / "ideas/x/adoptions/ren-claude.md", tmp, owners, "bogus-kind")
        check("unknown participant kind fails closed", any("unknown participant kind" in p for p in probs))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    failed = [n for n, c in checks if not c]
    print(f"\n{len(checks)} checks, {len(failed)} failed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
