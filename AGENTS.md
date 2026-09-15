# AGENTS.md

See [`CLAUDE.md`](./CLAUDE.md) — that file is the single source of truth for
agent-facing guidance on this repository (what the project is, build/test/lint
commands, and the pipeline architecture, including non-obvious rationale behind
specific design decisions). This file exists only so that AGENTS.md-reading tools
(Codex, Cursor, etc.) pick up the same context as Claude Code.

Keep `CLAUDE.md` up to date when you add or change a feature — it's the first
thing an agent restarting in this repo should read, and it has fallen behind
actual code before (e.g. the PDF/thumbnail export pipeline in `slide_maker/pdf.py`
and `slide_maker/thumbnail.py` went undocumented for a while after being added).
