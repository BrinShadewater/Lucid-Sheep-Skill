# 🔔 Triggers — how to poke the flock

Every member's agents respond to different nudges. This file is the cheat-sheet:
repo-wide commands first, then a section per member documenting their own levers.
**Add your section when you join** — your circle-mates never trigger your agents, but
seeing how you run your side helps everyone debug "why is their loop quiet".

## 🧰 Repo tools (anyone, any harness)

Run from the repo root:

```
python tools/lint_cards.py     # no-code rule + required sections, cards / problems / reviews
python tools/build_index.py    # regenerate INDEX.md (never hand-edit it)
```

CI runs both on every push, so forgetting locally is caught remotely.

## 🐑 <Your name>'s household

| Say / do | What happens |
|----------|--------------|
| "check the flock" / "run the loop" | full manual loop pass, same rules as the scheduled one |
| "publish a card about X" | drafts the card, shows it in full, ships on your yes — any day, any time |
| "digest now" | the weekly digest, on demand |
| <your scheduled task, if any> | nightly loop pass, automatic |

## 💭 Humans, all members

| Do | What happens |
|----|--------------|
| open a GitHub Issue titled `[<idea-slug>] …` | every agent reads it *before* forming a verdict on that card, and posts its verdict back on your thread |
| tell your own agent to publish / adopt | the two real decisions — in session, any time; **never** via GitHub comment |

---

*New members: copy the shape above for your own agents — what to say, what runs on a
schedule, and how your circle-mates would notice if your loop went quiet.* 🌙
