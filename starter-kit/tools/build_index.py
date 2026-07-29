#!/usr/bin/env python3
"""Regenerate INDEX.md — the generated catalog of every idea and open problem.

Run from the repo root after committing any card, review, adoption, or wanted change:
    python tools/build_index.py

Proof semantics (CONVENTIONS 1.13):
  - every card carries card-version (MAJOR.MINOR.PATCH); material changes bump minor+
  - reviews/adoptions record reviewed-version per dated section; validations of an
    older material version (different MAJOR.MINOR) stay visible but count as stale
  - signals are distinct: observed (non-retracted Convergence) is displayed, adopted
    verdicts are displayed, and circle-proven requires >=2 version-current `yes`
    adoptions from distinct non-author humans with no version-current `no` (which
    instead degrades the badge to disputed)
  - identity resolves via the MEMBERS.md registry only, fail-closed

Stdlib only, deliberately: founding a circle must require zero installs.
"""
import re
import sys
from pathlib import Path

VERDICT_RE = re.compile(r"\*\*Verdict\*\*[^`]*`(adopt|adapt|skip|watch)`", re.IGNORECASE)
HINDSIGHT_RE = re.compile(r"\*\*Verdict in hindsight\*\*[^`]*`(yes|no|mixed)`",
                          re.IGNORECASE)
CONVERGENCE_RE = re.compile(r"^\*\*Convergence\*\*", re.MULTILINE)
RETRACTED_RE = re.compile(r"^\*\*Convergence retracted\*\*", re.MULTILINE)
REVIEWED_VER_RE = re.compile(r"reviewed-version:\s*([0-9]+(?:\.[0-9]+){0,2})")
SECTION_RE = re.compile(r"^## +(?=\d{4})", re.MULTILINE)


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


def material_version(ver: str) -> str:
    """MAJOR.MINOR — the material identity of a version (patch = editorial)."""
    parts = (ver or "").split(".")
    return ".".join(parts[:2]) if len(parts) >= 2 else (ver or "?")


def handle_owners(root: Path) -> dict[str, str]:
    """Map registered handle -> human-id, from the MEMBERS.md registry table.

    Handles come from the Handle column (third cell) only; human identity is the
    first cell with any decoration stripped. Unknown handles fail closed everywhere.
    """
    owners: dict[str, str] = {}
    members = root / "MEMBERS.md"
    if not members.exists():
        return owners
    for line in members.read_text(encoding="utf-8").splitlines():
        if not line.strip().startswith("|"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 3 or cells[0].lower() in ("human", "") or set(cells[0]) <= {"-"}:
            continue
        human = cells[0].split(" (")[0].strip().lower()
        for handle in re.findall(r"`([^`]+)`", cells[2]):
            owners[handle.strip().lower()] = human
    return owners


def dated_sections(text: str) -> list[str]:
    """Split a review/adoption file into dated ## sections (preamble dropped)."""
    parts = SECTION_RE.split(text)
    return parts[1:] if len(parts) > 1 else []


def latest_signal(path: Path, regex: re.Pattern, card_mv: str):
    """Latest dated section's signal -> (value, version_current: bool) or None."""
    sections = dated_sections(path.read_text(encoding="utf-8"))
    for section in reversed(sections):
        hits = regex.findall(section)
        if hits:
            ver = REVIEWED_VER_RE.search(section)
            current = bool(ver) and material_version(ver.group(1)) == card_mv
            return hits[-1].lower(), current
    return None


def convergence_state(path: Path) -> bool:
    """True if the file declares a Convergence that was never retracted after."""
    text = path.read_text(encoding="utf-8")
    conv = [m.start() for m in CONVERGENCE_RE.finditer(text)]
    retr = [m.start() for m in RETRACTED_RE.finditer(text)]
    if not conv:
        return False
    return not retr or max(retr) < max(conv)


def idea_rows(root: Path, owners: dict[str, str]) -> list[tuple]:
    rows = []
    for folder in sorted(root.glob("ideas/*/")):
        card = folder / "card.md"
        if not card.exists():
            continue
        fm = frontmatter(card.read_text(encoding="utf-8"))
        author = (fm.get("human-id") or fm.get("human", "?")).lower()
        card_ver = fm.get("card-version", "")
        card_mv = material_version(card_ver)
        status = fm.get("status", "?")
        eligible = status == "published"

        verdicts, stale, observed = [], 0, 0
        yes_humans, no_current = set(), 0
        for review in sorted(folder.glob("reviews/*.md")):
            human = owners.get(review.stem.lower())  # fail closed on unknown
            sig = latest_signal(review, VERDICT_RE, card_mv)
            if sig:
                v, current = sig
                verdicts.append(v)
                if not current:
                    stale += 1
            if convergence_state(review) and human is not None:
                observed += 1

        adoptions = sorted(folder.glob("adoptions/*.md"))
        for adoption in adoptions:
            human = owners.get(adoption.stem.lower())
            if human is None:
                continue  # unknown identity never counts
            sig = latest_signal(adoption, HINDSIGHT_RE, card_mv)
            if not sig:
                continue
            v, current = sig
            if human == author:
                continue  # author's own outcome never proves the author's card
            if current and v == "yes":
                yes_humans.add(human)
            elif current and v == "no":
                no_current += 1
            elif not current:
                stale += 1

        if not eligible:
            proven = status  # retired/retracted cards earn nothing new
        elif no_current:
            proven = f"disputed(yes:{len(yes_humans)} no:{no_current})"
        elif len(yes_humans) >= 2:
            proven = "circle-proven(" + ",".join(sorted(yes_humans)) + ")"
        else:
            proven = "—"

        tally = " ".join(f"{v}:{verdicts.count(v)}"
                         for v in ("adopt", "adapt", "skip", "watch")
                         if verdicts.count(v)) or "—"
        extras = []
        if observed:
            extras.append(f"obs:{observed}")
        if stale:
            extras.append(f"stale:{stale}")
        if extras:
            tally = (tally + " " + " ".join(extras)).strip()

        rows.append((
            folder.name,
            fm.get("title", "?"),
            f"{fm.get('human', '?')} / {fm.get('agent', '?')}",
            card_ver or "?",
            fm.get("maturity", "?"),
            proven,
            status,
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

    lines = [
        "# 🐑 Index ✨",
        "",
        "Generated by `tools/build_index.py` — do not hand-edit.",
        "",
        "This catalog is for *finding* cards. Verdicts require reading the full card",
        "(see the full-read rule in CONVENTIONS.md). Badges are computed and",
        "explainable: `circle-proven(...)` names the humans whose version-current",
        "`yes` adoptions earned it; `obs:` counts declared convergence; `stale:`",
        "counts validations of older material versions, visible but non-counting.",
        "",
        "## 💭 Ideas",
        "",
    ]
    lines += table(
        ["Idea", "Title", "Author", "Version", "Maturity", "Proven", "Status",
         "Updated", "Verdicts", "Adoptions", "Inspired by"],
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
