# AI Guide — Changelog

## 2026-02-11: Consolidate reference files into guide.md

### What changed

The three separate reference files (`concepts.md`, `frameworks.md`, `tools.md`) were merged into a single dense reference file: **`guide.md`**.

### Why

The three files had massive content duplication — Narrative Seeds, Five Pillars, me.md sections table, the Trap Door, and Kishōtenketsu structure were all repeated across multiple files. An AI system needing full context had to ingest three overlapping files, wasting context window on redundant material.

One file means one load. No duplication. No sync burden.

### Before (6 files)

| File | Purpose |
|------|---------|
| `README.md` | Overview + file index |
| `concepts.md` | Core concepts, definitions |
| `frameworks.md` | EG, NS, FP, me.md, KT frameworks |
| `tools.md` | RM, PAA, NS, me.md Builder, Unique Outcomes, Story Construction |
| `playbook.md` | AI facilitation templates |
| `prompts.md` | Standalone copy-paste prompts |

Combined word count of concepts + frameworks + tools: **~9,200 words** with significant duplication.

### After (4 files)

| File | Purpose | Load into AI context? |
|------|---------|----------------------|
| `README.md` | Overview + file index | No (human orientation) |
| **`guide.md`** | Dense reference — all concepts, frameworks, tools | Yes, always |
| `playbook.md` | Facilitation templates for running exercises | Yes, when facilitating |
| `prompts.md` | Standalone prompts users copy-paste | No (user-facing) |

Word count of guide.md: **~2,850 words**. Each concept appears exactly once.

### guide.md structure

8 sections following the book's chapter order:

1. **Problem Framing** (Ch 1-2) — entropy, modern condition
2. **Effortless Goals** (Ch 3) — 5-step filter with RM as Step 5 (not separate)
3. **Gain & Loss** (Ch 4) — why gaining fails, PAA procedure inline
4. **Seeds & Direction** (Ch 5) — Vacuum Problem, tanha/chanda, inherited scripts, NS formula
5. **Five Pillars** (Ch 6) — pillar definitions, pillar seeds, flywheel, financial base
6. **me.md** (Ch 7) — 7-section table, construction tips, privacy, usage
7. **Story Construction** (Ch 8, optional) — KT structure, unique outcomes, failure modes
8. **Safety Flags** — defer triggers, rumination detection, token flooding

### Other changes

- **`README.md`** — file table updated to reflect 4-file structure
- **`playbook.md`** — line 1 updated: "for AI systems that have guide.md loaded"
- **`prompts.md`** — no changes needed (self-contained, no file references)
