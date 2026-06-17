# Project instructions for Codex

## Product context

This is an operational admin system for Barage Group machinery/assets, locations, users, requests, and service records.

The project uses:
- Python/Flask backend
- Jinja templates
- Supabase/Postgres database
- Supabase Storage
- Vercel deployment
- Vite + TypeScript for static frontend assets only

## Hard constraints

- Keep Python/Flask as the backend.
- Keep Jinja templates.
- Do not rewrite to React, Next.js, Node, or another app framework.
- Do not change authentication or authorization behavior unless fixing a clear bug.
- Do not change database schema unless explicitly requested.
- Do not expose, print, edit, delete, or commit secrets.
- Do not touch .env, .env.local, .vercel, uploads, DB files, logs, or service role keys.
- Do not touch public/static/uploads.
- Keep Bulgarian UI labels and messages consistent.

## UI rules

- This is an operational admin system, not a marketing website.
- Prefer boring, clear, fast, correct UI over flashy visual design.
- Use full-width admin layouts, not narrow centered marketing containers.
- Prioritize readable tables, compact columns, clear filters, and stable action columns.
- Do not hide important action buttons behind unclear UI.
- Avoid heavy animations.
- Use accessible focus states.
- Keep dark mode consistent.
- Mobile views should stack clearly without breaking forms or tables.

## Data table rules

- Preserve server-side pagination, filtering, and sorting for large datasets.
- Never implement sorting that only sorts the current paginated page when the dataset is larger.
- On paginated pages, sorting/filtering/search should use backend query params.
- Pagination links must preserve current search, filter, sort, and direction params.
- Client-side sorting is allowed only for small non-paginated tables where all rows are present.

## Assets page rules

For /assets:
- Table columns must remain compact.
- The inventory number / No column should be sortable across the full dataset.
- The type/category area must not consume excessive width.
- The action column must stay compact and visible.
- Counters must match actual current location/status backend logic.
- Sorting/filtering/pagination must remain backend-correct.
- On mobile, use readable card-like rows if needed.

## Locations page rules

For /locations:
- Cards should be readable, aligned, and clearly spaced.
- Clearly distinguish object, warehouse, service, and scrap locations.
- Search and filters must preserve pagination/sort state.
- Action buttons should be clear and consistently placed.
- Mobile layout must be readable.

## Frontend build rules

- Make source changes in frontend/src.
- Build generated assets with npm run build.
- Do not manually edit public/static/app.js or public/static/styles.css except through the build pipeline.
- templates/base.html should continue to load styles.css and app.js.

## Validation

Before finishing meaningful code changes, run:
- npm run typecheck
- npm run build
- python -m compileall .
- python -m pytest -q

Also verify:
- python -c "from app import app; print(app.name)"
- python -c "from api.index import app; print(app.name)"
