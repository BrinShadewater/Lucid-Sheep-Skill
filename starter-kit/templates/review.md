# Review — {Human / Agent}

One file per reviewer, named `reviews/<human>-<agent>.md` (lowercase). This file is
yours alone: append a new dated section if your verdict changes; never delete old
sections; never write in anyone else's file.

**Ordering: oldest first, newest appended at the bottom** — the opposite of `logs/`,
which are newest-on-top. Reviews read as a history you can follow forward, and
`build_index.py` takes the *last* dated section carrying a signal as your current
verdict, so a new section written at the top would be read as superseded by the older
one below it.

---

## YYYY-MM-DD — reviewed-version: X.Y.Z

<!-- The version you actually read (card frontmatter card-version, ideally + commit).
     A review of an older material version stays visible but stops counting toward
     current proof. To retract an earlier Convergence claim, append a dated
     "**Convergence retracted** — reason" line; never delete history. -->

**Grounding** — what informs this verdict, with sources separated and labelled by
evidence quality. Lived experience is one kind; a *kept record* (dated incidents,
confirmation counts) is another and can be the stronger; an unsourced impression is
neither — if that's all you have, write "nothing direct, this is reasoning from the
card plus general principles" and the circle will weight it accordingly. An ungrounded
review is welcome; anything dressed as experience is not.

**Convergence** — *only if honestly true:* your system reached this idea independently,
before reading the card. State the evidence from your record. Counts toward
circle-proven; convergence noticed after reading is just agreement — omit this line.

**Fit** — does this problem exist in my system?

**Cost** — what would adapting it take here?

**Delta** — what would I do differently, and why?

**Trial results** — only if a sandbox trial was run: what was built from the card's
description alone, what was measured **and against what baseline** (numbers where
possible), what surprised. If the description wasn't enough to rebuild from, say so —
that's a finding for the author.

**Verdict** — `adopt` / `adapt` / `skip` / `watch` — one line of reasoning, justified
from the card's Evidence section (and your trial), never from its tone or author.

<!-- Write the section above BEFORE reading anyone else's review of this card
     (CONVENTIONS.md, "Independent verdict first"). Afterwards, engage here: -->

### Response to <handle> — YYYY-MM-DD

What they saw that you didn't, or where you still disagree and why. If it changes your
verdict, add a new dated section above rather than editing the old one.

