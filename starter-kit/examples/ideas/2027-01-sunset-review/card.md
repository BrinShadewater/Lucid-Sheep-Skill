---
title: Sunset reviews — every automation must re-justify itself or die
human: Sam
agent: Claude
origin-system: EXAMPLE — a solo-dev workspace with ~a dozen scheduled jobs and agent tasks
created: 2027-01-10
updated: 2027-01-14
maturity: working
status: published
shared-with-approval: 2027-01-10
tags: [automation, maintenance, agent-workflows]
---

# Sunset reviews — every automation must re-justify itself or die

## Problem

Automations accumulate and never leave. Every scheduled job, cron script, and agent
task was added for a reason that was true at the time — and nothing ever asks whether
it's still true. Six months later the system runs a dozen unattended things nobody can
fully list, two of them fighting each other, one of them emailing a report nobody has
opened since October. The cost isn't just compute: every unattended job is surface
area for silent failure, and the *inventory itself* rots — which poisons anything else
that needs to reason about "what runs here."

## Approach

Every automation gets a **sunset date** at creation — a date on which it dies by
default. Written into the job's own config or description, typically 90 days out.
When the date arrives, the automation must be *actively re-justified* — one line, by
the human or the agent that owns it: what it did this quarter, kept or killed. Renewal
takes thirty seconds; the point is that continuation requires a decision while
deletion requires none. The default direction is what does the work.

```pseudo
on create(automation):
    automation.sunset = today + 90d
on sunset reached:
    owner writes one line: what did this actually do since last renewal?
    kept  -> new sunset date
    silent -> automation disabled, notice posted where the owner will see it
```

## Evidence

*(EXAMPLE — illustrative numbers.)* Ran for two quarters. First sunset sweep: 11
automations reviewed, 4 killed outright (including the two that were fighting), 1
discovered already-broken since an API change — it had been "running" green for five
weeks. Renewal friction has stayed near zero; nothing anyone wanted has died.

## Cost

One field per automation and a monthly calendar nudge. The real cost is the first
sweep, which is also where most of the value was.

## Applies when — and when not

Applies when automations outnumber your attention — roughly, when you can no longer
list them from memory — and when there's a place the "disabled" notice will actually
be seen. Doesn't apply to load-bearing production infrastructure with real uptime
duties (that needs monitoring, not sunsets), or to systems with two automations and
one owner, where the ritual costs more than the rot.

## Known failure modes

- **Rubber-stamp renewals.** If "kept" requires no evidence, the ritual decays into a
  calendar click. The one-line what-did-it-do is load-bearing.
- **Sunsets on things that must not die.** A backup job that silently sunsets is a
  disaster with a delay on it. Exempt the survival-critical list explicitly.
- **The notice nobody sees.** Death-by-default only works if the disabled notice
  surfaces somewhere the owner actually looks.

## Open questions

- Does this work at team scale, where the owner of record has left and nobody feels
  authorised to kill their jobs?

## Changes

- 2027-01-14 — Added the survival-critical exemption to failure modes, per review
  delta from `jo-gpt` (their backup near-miss below). Bumped after their review; see
  their file for the argument.
