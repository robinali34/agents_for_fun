# DFT + hardware-test software — personal learning map

Generic industry map (not Apple-specific). Use it to prioritize questions for your team.

## Core concepts

| Area | Learn enough to… |
|------|------------------|
| Why DFT exists | Explain test cost, yield, time-to-debug vs design cost |
| Scan / structural test | Describe scan chains, ATPG, stuck-at / transition concepts at a high level |
| BIST / memory test | Know when on-chip self-test is used vs ATE |
| Boundary scan / board | Relate chip test to board bring-up |
| ATE / lab | Understand patterns, vectors, fixtures at a software interface level |
| Silicon bring-up | Know the SW loop: detect → isolate → log → bisect → ticket |

## Software engineer angles (your likely leverage)

1. **Test frameworks & harnesses** — reliability, flakiness, parallelization
2. **Data pipelines** — logs, failing vectors, triage dashboards
3. **Tooling UX** — make hardware engineers faster without hiding failures
4. **Automation / CI** — gate quality without blocking lab velocity
5. **Interfaces** — clean APIs between DFT IP, firmware, and host SW
6. **Observability** — structured logs, repro packs, bisect helpers

## Suggested study cadence (personal time / public sources only)

- Week 1: glossary + one overview paper/book chapter on DFT fundamentals
- Week 2: how your org’s SW talks to hardware (ask buddy for architecture diagram *in approved systems*)
- Week 3: one end-to-end failure story — how a bug was found and fixed
- Week 4: pick a small reliability or DX improvement

## Questions that show senior judgment

- Where do false failures come from today, and how are they attributed?
- What is the cost of a late DFT discovery in this product line?
- Which tools are “source of truth” vs tribal knowledge?
- What would you delete from the toolchain if you could?
