# Mushar Benchmark Studio — Evidence-Led AI Benchmarking Platform

Standalone platform (Python standard library + SQLite; no web framework). Built from
`AI_Benchmarking Architecture.xlsx`.

## Run
Double-click `run.bat`, or run:
    python app/server.py        → http://localhost:8765

- **Demo mode** (default, no key needed): AI steps use deterministic demo generators.
- **Live mode**: `pip install anthropic`, set `ANTHROPIC_API_KEY`, then restart the server. Research uses
  Claude (`claude-opus-5`, configurable in Settings) with web search.
- Switch roles from the "Acting as" menu in the top bar (Lead, Consultant, Reviewer, QA Lead, Viewer, Admin).
- To reset the demo, delete `data/benchmark.db`.

## Layout
- `app/server.py`: HTTP API, gate logic, permissions
- `app/ai.py`: Claude orchestration and background jobs
- `app/demo.py`: offline demo generators
- `app/prompts.py`: the Prompt Library (7 prompts)
- `app/scoring.py`: comparison matrix and weighted scoring
- `app/qa.py`: the 11 QA rules
- `app/exports.py`: PPTX deliverable and Excel evidence workbook
- `static/`: single-page front end
- `docs/`: DESIGN.md, the Specification (.docx) and the Pitch deck (.pptx)
- `preview/`: read-only single-file preview (published as a shareable link)

## Integration
The front end talks only to the JSON API under `/api/*`, and the user is passed in the `X-User-Id` header.
To embed the platform in another system, reuse the API and replace that header with the host platform's SSO.

## Hosting
- **Vercel** (free): serves the read-only preview (`vercel.json` rewrites `/` to it). Import the repo and deploy.
- **Render** (free web service): runs the full platform from `render.yaml` (New → Blueprint → this repo).
  The free instance sleeps when idle and its disk is ephemeral, so the demo database is re-seeded on each restart.
  Add `ANTHROPIC_API_KEY` in the Render dashboard to switch from demo mode to live Claude research.
