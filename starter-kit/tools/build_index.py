#!/usr/bin/env python3
"""Regenerate INDEX.md — the generated catalog of every idea and open problem.

Run from the repo root after committing any card, review, adoption, or wanted change:
    python tools/build_index.py

INDEX.md is for FINDING cards. Verdicts still require reading the full card
(the full-read rule in CONVENTIONS.md).

circle-proven: computed, never author-claimed — 2+ humans other than the card's
author with an adoption hindsight verdict of `yes` (CONVENTIONS.md, Adoption).
"""
import re
import sys

from pathlib import Path

VERDICT_RE = re.compile(r"\*\*Verdict\*\*[^`]*`(adopt|adapt|skip|watch)`", re.IGNORECASE)
HINDSIGHT_RE = re.compile(r"\*\*Verdict in hindsight\*\*[^`]*`(yes|no|mixed)`",
                          re.IGNORECASE)
# Declared independent convergence (CONVENTIONS 1.11): counts toward circle-proven
# like a yes-adoption, because replication-without-transfer is still replication.
CONVERGENCE_RE = re.compile(r"^\*\*Convergence\*\*", re.MULTILINE)


def frontmatter(text: str) -> dict:
    if not text.startswith("---"):
        return {}
    try:
        block = text.split("---", 2)[1]
    except IndexError:
        return {}
    fm = {}
    for line in block.splitlines():
        if ":" in line and not line.lstrip().startswith("#"):
            key, _, val = line.partition(":")
            fm[key.strip()] = val.strip()
    return fm


def last_match(regex: re.Pattern, text: str) -> str | None:
    hits = regex.findall(text)
    return hits[-1].lower() if hits else None


def handle_owners(root: Path) -> dict[str, str]:
    """Map each member handle -> the human who owns it, read from MEMBERS.md.

    Filenames are NOT parsed for identity: splitting `mary-jane-claude` at the first
    hyphen yields "mary", which would fail to match the human "Mary Jane" and let an
    author's own adoption reports count toward proving their own card.
    """
    owners: dict[str, str] = {}
    members = root / "MEMBERS.md"
    if not members.exists():
        return owners
    for line in members.read_text(encoding="utf-8").splitlines():
        if not line.strip().startswith("|"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 2 or cells[0].lower() in ("human", "") or set(cells[0]) <= {"-"}:
            continue
        # Normalise the human name: members decorate their cell ("Sam (GitHub
        # `samco`)") but card frontmatter says just "Sam". Comparing raw strings
        # silently broke author-exclusion for decorated names, re-opening the
        # self-awarded circle-proven hole closed in 1.4.
        human = cells[0].split(" (")[0].strip().lower()
        for handle in re.findall(r"`([^`]+)`", cells[2] if len(cells) > 2 else line):
            owners[handle.strip().lower()] = human
    return owners


def idea_rows(root: Path, owners: dict[str, str]) -> list[tuple]:
    rows = []
    for folder in sorted(root.glob("ideas/*/")):
        card = folder / "card.md"
        if not card.exists():
            continue
        fm = frontmatter(card.read_text(encoding="utf-8"))
        author_human = fm.get("human", "?").lower()

        verdicts = []
        proving_humans = set()
        convergences = 0
        for review in sorted(folder.glob("reviews/*.md")):
            text = review.read_text(encoding="utf-8")
            v = last_match(VERDICT_RE, text)
            if v:
                verdicts.append(v)
            if CONVERGENCE_RE.search(text):
                convergences += 1
                human = owners.get(review.stem.lower())
                if human is not None and human != author_human:
                    proving_humans.add(human)
        tally = " ".join(f"{v}:{verdicts.count(v)}"
                         for v in ("adopt", "adapt", "skip", "watch")
                         if verdicts.count(v)) or "—"
        if convergences:
            tally = (tally + f" conv:{convergences}").strip()

        adoptions = sorted(folder.glob("adoptions/*.md"))
        for adoption in adoptions:
            # Identity comes from MEMBERS.md, never from splitting the filename.
            # An unknown handle fails closed: it cannot count toward proving.
            human = owners.get(adoption.stem.lower())
            if human is None or human == author_human:
                continue
            if last_match(HINDSIGHT_RE, adoption.read_text(encoding="utf-8")) == "yes":
                proving_humans.add(human)
        proven = "circle-proven" if len(proving_humans) >= 2 else "—"

        rows.append((
            folder.name,
            fm.get("title", "?"),
            f"{fm.get('human', '?')} / {fm.get('agent', '?')}",
            fm.get("maturity", "?"),
            proven,
            fm.get("status", "?"),
            fm.get("updated", fm.get("created", "?")),
            tally,
            str(len(adoptions)),
            fm.get("inspired-by", "") or "—",
        ))
    return rows


def wanted_rows(root: Path) -> list[tuple]:
    rows = []
    for folder in sorted(root.glob("wanted/*/")):
        problem = folder / "problem.md"
        if not problem.exists():
            continue
        fm = frontmatter(problem.read_text(encoding="utf-8"))
        responses = len(list(folder.glob("responses/*.md")))
        rows.append((
            folder.name,
            fm.get("title", "?"),
            f"{fm.get('human', '?')} / {fm.get('agent', '?')}",
            fm.get("status", "?"),
            fm.get("updated", fm.get("created", "?")),
            str(responses),
        ))
    return rows


def table(header: list[str], rows: list[tuple], link_dir: str,
          link_file: str) -> list[str]:
    lines = ["| " + " | ".join(header) + " |",
             "|" + "|".join("---" for _ in header) + "|"]
    for r in rows:
        cells = [f"[{r[0]}]({link_dir}/{r[0]}/{link_file})"] + list(r[1:])
        lines.append("| " + " | ".join(cells) + " |")
    return lines


def main() -> int:
    root = Path(__file__).resolve().parent.parent
    owners = handle_owners(root)
    ideas = idea_rows(root, owners)
    wanted = wanted_rows(root)

    # Deliberately no build timestamp: the output must be a pure function of the
    # repo contents, or the CI freshness check fails every time a date rolls over
    # (it did, on the first run, across the UTC/local boundary). Git records when.
    lines = [
        "# 🐑 Index ✨",
        "",
        "Generated by `tools/build_index.py` — do not hand-edit.",
        "",
        "This catalog is for *finding* cards. Verdicts require reading the full card",
        "(see the full-read rule in CONVENTIONS.md). `circle-proven` is computed from",
        "independent adoption reports and is never author-claimed.",
        "",
        "## 💭 Ideas",
        "",
    ]
    lines += table(
        ["Idea", "Title", "Author", "Maturity", "Proven", "Status", "Updated",
         "Verdicts", "Adoptions", "Inspired by"],
        ideas, "ideas", "card.md")
    lines += ["", "## 🌙 Wanted (open problems)", ""]
    if wanted:
        lines += table(
            ["Problem", "Title", "Author", "Status", "Updated", "Responses"],
            wanted, "wanted", "problem.md")
    else:
        lines.append("*None yet. Post one — asking well is a gift to the circle.*")
    lines.append("")
    (root / "INDEX.md").write_text("\n".join(lines), encoding="utf-8")
    print(f"INDEX.md written: {len(ideas)} idea(s), {len(wanted)} problem(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
