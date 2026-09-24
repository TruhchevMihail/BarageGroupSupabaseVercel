# Barage Indigo Redline Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rebuild the existing Flask/Jinja interface as a compact Barage-branded Indigo Redline admin system with complete light/dark themes, explicit text actions, dense no-scroll desktop tables, and card-based mobile fallbacks.

**Architecture:** Preserve all Flask routes, permissions, models, and server-side query behavior. Implement the redesign through semantic Jinja markup, focused CSS modules under `frontend/src/styles`, and the existing small TypeScript UI modules; Vite remains the only frontend build step and emits `public/static/styles.css` and `public/static/app.js`.

**Tech Stack:** Python 3 / Flask / Jinja2 / pytest / HTML / modular CSS / TypeScript / Vite / Vercel

**Spec:** `docs/superpowers/specs/2026-09-24-barage-indigo-redline-redesign.md`

## Global Constraints

- Keep Python and Flask as the backend and keep Jinja templates.
- Keep Bulgarian UI labels and messages.
- Do not change authentication, authorization, database behavior, or database schema.
- Preserve server-side filtering, sorting, and pagination, including all active query parameters.
- Do not expose, print, edit, delete, or commit secrets, `.env*`, `.vercel`, uploads, database files, logs, or service-role keys.
- Make authored frontend changes only in `frontend/src`; regenerate `public/static/app.js` and `public/static/styles.css` through `npm run build`.
- Do not add a frontend framework or a new runtime dependency.
- Important actions must use visible Bulgarian text; icons may support but never replace those labels.
- Standard laptop and desktop data tables must not require horizontal scrolling.
- Mobile tables must become compact labeled cards rather than compressed desktop tables.
- Do not deploy or promote to production; the final deployment is a Vercel preview only.

## Review Focus

1. A user with no stored theme and a dark system preference must receive dark mode before first paint, while a stored explicit choice always wins; Task 1 adds the rendered-shell contract and Task 9 performs browser verification.
2. Very long asset names, aliases, serial numbers, emails, and location names must truncate without widening the table and must expose the complete value through `title`; Tasks 5 and 8 add server-rendered contract tests.
3. Server-side sort, filter, and pagination URLs must keep their query parameters after the markup changes; Tasks 5, 7, and 8 rerun the existing route tests and assert representative query links.
4. Roles that cannot create, approve, edit, or delete must not gain visible actions during the redesign; Tasks 5–8 rerun `tests/test_role_visibility.py` after each template group.
5. AJAX failures and mobile sidebar usage must leave navigation usable, keep controls labeled, and preserve keyboard focus; Task 9 adds browser checks for Escape, focus visibility, failed navigation recovery, reduced motion, and the mobile card layouts.

---

## File Structure

### Existing files to modify

- `templates/base.html` — global shell, sidebar labels, theme button content, and reusable page structure.
- `templates/login.html` — Barage-branded split login experience.
- `templates/dashboard.html` — compact KPI, search, alert, and activity sections.
- `templates/assets.html` — approved fixed compact asset table and explicit row actions.
- `templates/locations.html` — type-specific location containers and explicit actions.
- `templates/requests.html` — compact request table and explicit approve/reject actions.
- `templates/users.html` — compact user table and explicit detail actions.
- `templates/search.html` — consistent dense search results.
- `templates/asset_detail.html`, `templates/location_detail.html`, `templates/asset_service_detail.html`, `templates/profile.html` — compact detail containers and history sections.
- `templates/asset_form.html`, `templates/asset_edit.html`, `templates/asset_move.html`, `templates/asset_service_form.html`, `templates/location_form.html`, `templates/user_form.html`, `templates/profile_edit.html`, `templates/password_form.html`, `templates/assets_import.html` — consistent form sections and action labels.
- `templates/error.html` — actionable branded error state.
- `frontend/src/modules/theme.ts` — text-labeled synchronized theme toggles with persisted state.
- `frontend/src/styles/tokens.css` — single source of truth for Indigo Redline light/dark semantic tokens.
- `frontend/src/styles/layout.css` — global typography, content width, command palette, login shell, detail layouts, and remaining legacy base rules.
- `frontend/src/styles/sidebar.css` — compact desktop navigation and mobile disclosure.
- `frontend/src/styles/buttons.css` — primary, secondary, neutral, text, and danger variants.
- `frontend/src/styles/forms.css` — compact fields, focus, validation, and action rows.
- `frontend/src/styles/cards.css` — panels, KPI rails, chips, alerts, and empty states.
- `frontend/src/styles/tables.css` — shared dense table primitives and mobile row-card behavior.
- `frontend/src/styles/dashboard.css` — dashboard-specific composition.
- `frontend/src/styles/assets.css` — no-scroll asset table widths, truncation, details, and forms.
- `frontend/src/styles/locations.css` — type-specific rails and compact location rows.
- `frontend/src/styles/users.css` — compact users and requests layouts.
- `frontend/src/styles/responsive.css` — breakpoint behavior without horizontal table scrolling.
- `.gitignore` — ignore `.superpowers/` visual-companion session files.

### New files to create

- `tests/test_ui_contracts.py` — rendered HTML contracts for theme controls, explicit actions, table labels, truncation hooks, and role visibility.
- `.design/indigo-redline/DESIGN_BRIEF.md` — concise approved intent and visual direction derived from the spec.
- `.design/indigo-redline/INFORMATION_ARCHITECTURE.md` — navigation, page hierarchy, and responsive behavior.
- `.design/indigo-redline/DESIGN_TOKENS.css` — human-readable token reference matching `frontend/src/styles/tokens.css`.
- `.design/indigo-redline/TASKS.md` — implementation checklist synchronized with this plan.
- `.design/indigo-redline/DESIGN_REVIEW.md` — final preview critique and verification evidence.
- `.design/indigo-redline/screenshots/` — desktop, tablet, mobile, light, and dark preview captures.

## Interfaces

- `initThemeToggle(): void` consumes buttons matching `[data-theme-toggle]`, reads `document.documentElement.dataset.theme`, writes `localStorage.theme`, and updates each button’s `.theme-toggle-label` plus `aria-label`.
- Every compact table wrapper exposes `data-density="compact"`; table cells that can truncate use `.truncate-cell` and a complete `title` value.
- Every row-level navigation action uses `.table-row-action` and visible text such as `Виж детайли`.
- Location containers use `.location-type-site`, `.location-type-warehouse`, `.location-type-service`, or `.location-type-scrap` so the same semantic tokens work in both themes.
- Light/dark tokens are semantic custom properties; component modules consume tokens and do not hardcode theme-specific surface or text colors.

---

### Task 1: Lock the rendered UI contract and theme behavior

**Files:**
- Create: `tests/test_ui_contracts.py`
- Modify: `templates/base.html`
- Modify: `templates/login.html`
- Modify: `frontend/src/modules/theme.ts`
- Modify: `.gitignore`

**Interfaces:**
- Consumes: existing `create_app`, `client`, `make_user`, and `login` pytest fixtures.
- Produces: text-labeled `[data-theme-toggle]` controls containing `.theme-toggle-label`; stable `data-density="compact"` and `.table-row-action` markup contracts for later tasks.

- [ ] **Step 1: Write failing shell and action-label contract tests**

```python
import app as app_module


def _admin(make_user):
    return make_user(
        full_name='UI Администратор',
        email='ui-admin@example.test',
        role=app_module.ROLE_SUPERUSER,
    )


def test_login_has_text_labeled_theme_control(client):
    html = client.get('/login').get_data(as_text=True)
    assert 'data-theme-toggle' in html
    assert 'class="theme-toggle-label"' in html
    assert 'Тъмна тема' in html or 'Светла тема' in html


def test_authenticated_shell_uses_explicit_navigation_labels(client, login, make_user):
    admin = _admin(make_user)
    login(admin)
    html = client.get('/dashboard').get_data(as_text=True)
    for label in ('Общ преглед', 'Машини и инструменти', 'Заявки', 'Обекти и локации', 'Потребители'):
        assert label in html
    assert 'data-theme-toggle' in html


def test_assets_use_compact_table_and_explicit_action(client, login, make_user):
    admin = _admin(make_user)
    login(admin)
    html = client.get('/assets').get_data(as_text=True)
    assert 'data-density="compact"' in html
    assert 'table-row-action' in html
    assert 'Виж детайли' in html
    assert 'title="Детайли">⋯</a>' not in html
```

- [ ] **Step 2: Run the contract tests and verify failure**

Run: `python -m pytest tests/test_ui_contracts.py -q`

Expected: FAIL because the theme buttons contain only glyphs, the sidebar uses shorter labels, and the asset table has no density/action contract.

- [ ] **Step 3: Add labeled theme markup and preserve pre-paint initialization**

```html
<button type="button" class="theme-toggle" data-theme-toggle aria-label="Тъмна тема - смени">
  <span class="theme-toggle-indicator" aria-hidden="true">◐</span>
  <span class="theme-toggle-label">Тъмна тема</span>
</button>
```

Use that structure for both authenticated and login controls. Keep the existing head script that chooses `localStorage.theme` before CSS is painted.

- [ ] **Step 4: Update the TypeScript toggle without replacing button contents**

```ts
function setTheme(theme: string, buttons: HTMLButtonElement[]): void {
  const nextTheme = theme === 'dark' ? 'dark' : 'light';
  document.documentElement.dataset.theme = nextTheme;
  document.documentElement.style.colorScheme = nextTheme;
  window.localStorage.setItem('theme', nextTheme);

  buttons.forEach((button) => {
    const label = button.querySelector<HTMLElement>('.theme-toggle-label');
    const nextLabel = nextTheme === 'dark' ? 'Светла тема' : 'Тъмна тема';
    if (label) label.textContent = nextLabel;
    button.setAttribute('aria-label', `${nextLabel} - смени`);
  });
}
```

- [ ] **Step 5: Add the initial compact-table hooks and ignore companion files**

Add `data-density="compact"` to the assets table wrapper, replace the ellipsis-only link with `<a class="table-row-action">Виж детайли</a>`, and add this ignore rule:

```gitignore
.superpowers/
```

- [ ] **Step 6: Verify tests and frontend types**

Run: `python -m pytest tests/test_ui_contracts.py tests/test_role_visibility.py -q`

Expected: PASS.

Run: `npm run typecheck`

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add .gitignore tests/test_ui_contracts.py templates/base.html templates/login.html templates/assets.html frontend/src/modules/theme.ts
git commit -m "test: define Indigo Redline UI contracts"
```

---

### Task 2: Establish Indigo Redline tokens and global foundations

**Files:**
- Modify: `frontend/src/styles/tokens.css`
- Modify: `frontend/src/styles/layout.css`
- Create: `.design/indigo-redline/DESIGN_BRIEF.md`
- Create: `.design/indigo-redline/INFORMATION_ARCHITECTURE.md`
- Create: `.design/indigo-redline/DESIGN_TOKENS.css`
- Create: `.design/indigo-redline/TASKS.md`

**Interfaces:**
- Consumes: semantic token names already referenced by component styles (`--bg`, `--panel`, `--text`, `--primary`, `--green`, `--amber`, `--red`).
- Produces: the extended semantic tokens `--canvas`, `--surface`, `--surface-raised`, `--text-strong`, `--focus-ring`, `--site`, `--warehouse`, `--service`, `--scrap`, `--radius-*`, and `--shadow-*` for every later CSS task.

- [ ] **Step 1: Move theme variables out of the legacy layout file**

Replace the placeholder `tokens.css` with complete light and dark mappings and remove the old `:root` / `html[data-theme="dark"]` token blocks from the start of `layout.css`.

```css
:root {
  --canvas: #f7f7fb;
  --surface: #ffffff;
  --surface-raised: #ffffff;
  --surface-subtle: #f0f0f7;
  --text-strong: #20243c;
  --text: #2d3149;
  --text-soft: #51566d;
  --muted: #70758a;
  --line: #d8dae5;
  --line-soft: #e7e8ef;
  --primary: #dc252e;
  --primary-dark: #a9161d;
  --primary-soft: #ffebed;
  --ink: #151723;
  --ink-2: #20243c;
  --site: #16835b;
  --warehouse: #4f58cf;
  --service: #b76a0b;
  --scrap: #73798a;
  --focus-ring: rgba(220, 37, 46, .30);
  --radius-sm: 8px;
  --radius-md: 11px;
  --radius-lg: 15px;
  --shadow-soft: 0 6px 20px rgba(24, 34, 48, .06);
}

html[data-theme="dark"] {
  --canvas: #11111b;
  --surface: #1a1a26;
  --surface-raised: #20202e;
  --surface-subtle: #242432;
  --text-strong: #f4f4f8;
  --text: #e6e6ee;
  --text-soft: #c3c3d0;
  --muted: #9c9bad;
  --line: #373744;
  --line-soft: #30303d;
  --primary: #ef4650;
  --primary-dark: #ff6b73;
  --primary-soft: #3b1921;
  --ink: #09090f;
  --ink-2: #11111b;
  --site: #54c99a;
  --warehouse: #8d92ff;
  --service: #f0b35b;
  --scrap: #a7a9b3;
  --focus-ring: rgba(239, 70, 80, .42);
  --shadow-soft: 0 8px 24px rgba(0, 0, 0, .24);
}
```

- [ ] **Step 2: Map legacy aliases to semantic tokens**

Keep current selectors working while modules migrate:

```css
:root {
  --bg: var(--canvas);
  --bg-strong: var(--surface-subtle);
  --panel: var(--surface);
  --panel-muted: var(--surface-subtle);
  --green: var(--site);
  --blue: var(--warehouse);
  --amber: var(--service);
  --red: var(--primary);
  --radius: var(--radius-lg);
  --card: var(--surface);
  --border: var(--line-soft);
  --border-muted: var(--line-soft);
  --accent: var(--primary);
  --surface-hover: color-mix(in srgb, var(--warehouse) 8%, var(--surface));
  --text-primary: var(--text);
  --location-card-bg: var(--surface);
  --location-card-border: var(--line-soft);
  --location-card-shadow: var(--shadow-soft);
  --location-card-hover-shadow: 0 10px 26px rgba(24, 34, 48, .10);
  --section-action-border: var(--line);
  --section-action-bg-hover: var(--primary-soft);
  --section-action-text: var(--text-soft);
}
```

- [ ] **Step 3: Rebuild global typography and surfaces in `layout.css`**

Use the full-width content canvas, compact base sizing, tabular numerals, and semantic backgrounds:

```css
body {
  background: var(--canvas);
  color: var(--text);
  font-family: Inter, "Segoe UI", system-ui, -apple-system, BlinkMacSystemFont, sans-serif;
  font-size: 14px;
  line-height: 1.45;
}

.content {
  width: 100%;
  min-width: 0;
  padding: 24px 26px 36px;
  overflow-x: clip;
}

table,
.summary-pill strong,
.asset-detail-value {
  font-variant-numeric: tabular-nums;
}
```

- [ ] **Step 4: Record the approved design-flow artifacts**

Create the four `.design/indigo-redline/` files with the approved objective, navigation hierarchy, exact semantic tokens, responsive rules, and a task checklist whose entries match Tasks 1–9 in this plan.

- [ ] **Step 5: Build and inspect generated output**

Run: `npm run typecheck && npm run build`

Expected: PASS; `public/static/styles.css` contains `--primary:#dc252e` and dark token mappings.

- [ ] **Step 6: Run backend contracts**

Run: `python -m pytest tests/test_ui_contracts.py tests/test_role_visibility.py -q`

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add .design/indigo-redline frontend/src/styles/tokens.css frontend/src/styles/layout.css public/static/styles.css public/static/app.js
git commit -m "feat: establish Indigo Redline design tokens"
```

---

### Task 3: Rebuild the shell, sidebar, buttons, forms, cards, and tables

**Files:**
- Modify: `templates/base.html`
- Modify: `frontend/src/styles/sidebar.css`
- Modify: `frontend/src/styles/buttons.css`
- Modify: `frontend/src/styles/forms.css`
- Modify: `frontend/src/styles/cards.css`
- Modify: `frontend/src/styles/tables.css`

**Interfaces:**
- Consumes: Task 2 semantic tokens and Task 1 theme markup.
- Produces: reusable `.btn-primary`, `.btn-secondary`, `.btn-neutral`, `.btn-text`, `.danger`, `.panel`, `.summary-pill`, `.table-row-action`, `.truncate-cell`, and `[data-density="compact"]` behavior.

- [ ] **Step 1: Extend UI contract tests for explicit sidebar copy and text actions**

Add assertions to `tests/test_ui_contracts.py`:

```python
assert 'Машини и инструменти' in html
assert 'Обекти и локации' in html
assert 'class="theme-toggle-label"' in html
assert 'aria-expanded="false"' in html
```

- [ ] **Step 2: Verify the new copy tests fail**

Run: `python -m pytest tests/test_ui_contracts.py -q`

Expected: FAIL until `base.html` uses the approved labels.

- [ ] **Step 3: Update the sidebar markup and accessible mobile toggle**

Use explicit labels and preserve all existing permission guards and route names:

```html
<a href="{{ url_for('assets') }}" class="{% if request.endpoint in ['assets', 'asset_detail', 'asset_edit', 'asset_new'] %}active{% endif %}">
  <span>Машини и инструменти</span>
</a>
```

- [ ] **Step 4: Implement the five button variants**

```css
.btn-primary { background: var(--primary); color: #fff; border-color: var(--primary); }
.btn-secondary { background: var(--surface); color: var(--text-strong); border-color: var(--line); }
.btn-neutral { background: var(--surface-subtle); color: var(--text); border-color: transparent; }
.btn-text,
.table-row-action { background: transparent; color: var(--primary-dark); border-color: transparent; box-shadow: none; }
.danger { background: color-mix(in srgb, var(--primary) 10%, var(--surface)); color: var(--primary-dark); }
```

Remove decorative gradients and vertical hover movement from operational buttons.

- [ ] **Step 5: Implement compact forms, panels, chips, focus, and table primitives**

```css
input,
select,
textarea { min-height: 38px; border-radius: var(--radius-sm); background: var(--surface); }

:where(a, button, input, select, textarea):focus-visible {
  outline: 3px solid var(--focus-ring);
  outline-offset: 2px;
}

[data-density="compact"] th { height: 36px; padding: 8px 9px; }
[data-density="compact"] td { height: 46px; padding: 8px 9px; }
.truncate-cell { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
```

- [ ] **Step 6: Verify shared contracts and build**

Run: `python -m pytest tests/test_ui_contracts.py tests/test_role_visibility.py -q`

Expected: PASS.

Run: `npm run typecheck && npm run build`

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add templates/base.html frontend/src/styles/sidebar.css frontend/src/styles/buttons.css frontend/src/styles/forms.css frontend/src/styles/cards.css frontend/src/styles/tables.css public/static/styles.css public/static/app.js tests/test_ui_contracts.py
git commit -m "feat: rebuild the Indigo Redline interface shell"
```

---

### Task 4: Redesign login and dashboard as the reference pages

**Files:**
- Modify: `templates/login.html`
- Modify: `templates/dashboard.html`
- Modify: `frontend/src/styles/dashboard.css`
- Modify: `frontend/src/styles/layout.css`
- Test: `tests/test_ui_contracts.py`

**Interfaces:**
- Consumes: shared tokens and components from Tasks 2–3.
- Produces: reference markup for page headers, KPI rails, search panels, alerts, recent-item cards, and the login split layout.

- [ ] **Step 1: Add dashboard and login contract tests**

```python
def test_dashboard_keeps_operational_sections(client, login, make_user):
    admin = _admin(make_user)
    login(admin)
    html = client.get('/dashboard').get_data(as_text=True)
    for label in ('Общ преглед', 'Статус на машините', 'В сервиз', 'Последно добавени машини', 'Последни заявки'):
        assert label in html
    assert 'data-main-search' in html


def test_login_keeps_only_explicit_access_fields(client):
    html = client.get('/login').get_data(as_text=True)
    assert 'name="email"' in html
    assert 'name="password"' in html
    assert '>Вход<' in html
```

- [ ] **Step 2: Verify the contracts before markup changes**

Run: `python -m pytest tests/test_ui_contracts.py -q`

Expected: PASS for preserved content; this protects the redesign from removing functional sections.

- [ ] **Step 3: Apply the reference page structure**

Keep every existing Jinja loop and permission check, but apply consistent classes:

```html
<div class="page-head split page-head--compact">
  <div><span class="eyebrow">Оперативно табло</span><h1>Общ преглед</h1></div>
  <div class="detail-actions page-actions">
    <a class="btn-secondary" href="{{ url_for('requests_list', status='pending') }}">Чакащи заявки</a>
    {% if stats.long_service_stay_total %}
    <a class="btn-primary" href="{{ url_for('assets', service_stay='long') }}">Дълъг престой в сервиз</a>
    {% endif %}
  </div>
</div>
```

- [ ] **Step 4: Style the dashboard and login in both themes**

Use 4–5 compact KPI columns at desktop sizes, colored semantic top rails, a full-width search panel, and a login split layout with the existing logo. Do not introduce remote fonts or images.

- [ ] **Step 5: Verify routes, build, and role visibility**

Run: `python -m pytest tests/test_ui_contracts.py tests/test_role_visibility.py -q`

Expected: PASS.

Run: `npm run typecheck && npm run build`

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add templates/login.html templates/dashboard.html frontend/src/styles/dashboard.css frontend/src/styles/layout.css public/static/styles.css public/static/app.js tests/test_ui_contracts.py
git commit -m "feat: redesign login and dashboard"
```

---

### Task 5: Deliver the fixed compact assets table

**Files:**
- Modify: `templates/assets.html`
- Modify: `frontend/src/styles/assets.css`
- Modify: `frontend/src/styles/tables.css`
- Modify: `frontend/src/styles/responsive.css`
- Test: `tests/test_ui_contracts.py`
- Test: `tests/test_assets_counters.py`
- Test: `tests/test_assets_csv.py`

**Interfaces:**
- Consumes: `.truncate-cell`, `.table-row-action`, compact table tokens, and existing server-side URL helpers.
- Produces: nine-column desktop asset table, minimal intermediate column hiding, and mobile labeled-card rows.

- [ ] **Step 1: Add asset table semantics and long-value contracts**

Extend `tests/test_ui_contracts.py` with an asset fixture containing long values, then assert:

```python
assert 'class="asset-cell-text truncate-cell"' in html
assert 'title="Телескопичен товарач с много дълго оперативно име"' in html
assert 'title="SERIAL-VERY-LONG-0123456789"' in html
for heading in ('№', 'Тип / име', 'Още познат като', 'Марка', 'Модел', 'Сериен №', 'Локация', 'Статус', 'Действия'):
    assert heading in html
```

- [ ] **Step 2: Run the asset contract and verify failure**

Run: `python -m pytest tests/test_ui_contracts.py -q`

Expected: FAIL because the table currently has eight columns, ellipsis-only actions, and incomplete truncation hooks.

- [ ] **Step 3: Update the asset markup without changing query behavior**

Add a visible Status column, retain all `current_query_url`, `page_url`, `data-ajax-link`, and server-side sort parameters, and use:

```html
<td class="asset-actions-cell" data-label="Действия">
  <a class="table-row-action" href="{{ url_for('asset_detail', asset_id=asset.id) }}">Виж детайли</a>
</td>
```

- [ ] **Step 4: Replace minimum-width scrolling with a true fixed layout**

```css
.assets-page-table-card .assets-table-scroll { overflow-x: clip; }
.assets-page-table-card .assets-table { width: 100%; min-width: 0; table-layout: fixed; }
.assets-page .asset-col-inventory { width: 5.5%; }
.assets-page .asset-col-type { width: 18%; }
.assets-page .asset-col-alias { width: 12%; }
.assets-page .asset-col-brand { width: 9%; }
.assets-page .asset-col-model { width: 10%; }
.assets-page .asset-col-serial { width: 12%; }
.assets-page .asset-col-location { width: 16%; }
.assets-page .asset-col-status { width: 9%; }
.assets-page .asset-col-actions { width: 8.5%; }
```

At 900–1279px hide only `.asset-alias-cell` and `.asset-serial-cell`; below 760px retain the existing labeled-card transformation and ensure no overflow.

- [ ] **Step 5: Verify URL state, counters, exports, and role visibility**

Run: `python -m pytest tests/test_ui_contracts.py tests/test_assets_counters.py tests/test_assets_csv.py tests/test_role_visibility.py -q`

Expected: PASS.

- [ ] **Step 6: Build frontend assets**

Run: `npm run typecheck && npm run build`

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add templates/assets.html frontend/src/styles/assets.css frontend/src/styles/tables.css frontend/src/styles/responsive.css public/static/styles.css public/static/app.js tests/test_ui_contracts.py
git commit -m "feat: add no-scroll compact asset table"
```

---

### Task 6: Redesign asset details and all operational forms

**Files:**
- Modify: `templates/asset_detail.html`
- Modify: `templates/asset_form.html`
- Modify: `templates/asset_edit.html`
- Modify: `templates/asset_move.html`
- Modify: `templates/asset_service_detail.html`
- Modify: `templates/asset_service_form.html`
- Modify: `templates/assets_import.html`
- Modify: `templates/location_form.html`
- Modify: `templates/user_form.html`
- Modify: `templates/profile_edit.html`
- Modify: `templates/password_form.html`
- Modify: `frontend/src/styles/assets.css`
- Modify: `frontend/src/styles/forms.css`
- Test: `tests/test_ui_contracts.py`

**Interfaces:**
- Consumes: shared panels, form controls, button variants, and existing upload/copy/collapsible TypeScript modules.
- Produces: `.detail-field-grid`, `.detail-field`, `.form-section`, and `.sticky-page-actions` patterns for all detail/form pages.

- [ ] **Step 1: Add explicit action and form-label contracts**

```python
def test_asset_form_and_detail_keep_explicit_actions(client, login, make_user, db):
    admin = _admin(make_user)
    login(admin)
    form_html = client.get('/assets/new').get_data(as_text=True)
    assert 'Инвентарен №' in form_html
    assert '>Запиши<' in form_html
    assert '>Отказ<' in form_html
```

Add an asset record and assert its detail page includes `Премести / заявка`, `Добави сервизен запис`, `Редакция`, and the existing copy hooks allowed by permissions.

- [ ] **Step 2: Run the detail/form contracts**

Run: `python -m pytest tests/test_ui_contracts.py -q`

Expected: PASS for existing labels; these assertions prevent functional regression while markup changes.

- [ ] **Step 3: Group forms and details semantically**

Use headings and containers without renaming inputs or changing methods/actions:

```html
<section class="form-section">
  <div class="section-head"><h2>Основни данни</h2></div>
  <div class="asset-form-grid">
    <label>Инвентарен № <input name="inventory_number" required></label>
    <label>Тип <input name="name" required></label>
    <label>Марка <input name="brand"></label>
    <label>Модел <input name="model"></label>
  </div>
</section>
```

- [ ] **Step 4: Apply compact grids and stable action areas**

Desktop detail metadata uses four columns, operational forms use two columns, and both collapse to one column below 760px. Sticky action areas are enabled only above 760px and must not cover content.

- [ ] **Step 5: Verify uploads, permissions, and existing detail behavior**

Run: `python -m pytest tests/test_password_change.py tests/test_locations_assets.py tests/test_service_stay.py tests/test_visibility_and_security.py tests/test_role_visibility.py tests/test_ui_contracts.py -q`

Expected: PASS.

- [ ] **Step 6: Build and commit**

Run: `npm run typecheck && npm run build`

Expected: PASS.

```bash
git add templates/asset_detail.html templates/asset_form.html templates/asset_edit.html templates/asset_move.html templates/asset_service_detail.html templates/asset_service_form.html templates/assets_import.html templates/location_form.html templates/user_form.html templates/profile_edit.html templates/password_form.html frontend/src/styles/assets.css frontend/src/styles/forms.css public/static/styles.css public/static/app.js tests/test_ui_contracts.py
git commit -m "feat: redesign details and operational forms"
```

---

### Task 7: Redesign locations as semantic operational containers

**Files:**
- Modify: `templates/locations.html`
- Modify: `templates/location_detail.html`
- Modify: `frontend/src/styles/locations.css`
- Test: `tests/test_ui_contracts.py`
- Test: `tests/test_locations_assets.py`

**Interfaces:**
- Consumes: Task 2 location tokens and Task 3 card/button patterns.
- Produces: compact `.location-row-card` containers with type rails, explicit `Виж детайли`, and full-value titles for long names.

- [ ] **Step 1: Add location-type and explicit-action contracts**

Create site, warehouse, service, and scrap records in `tests/test_ui_contracts.py` and assert:

```python
for class_name in ('location-type-site', 'location-type-warehouse', 'location-type-service', 'location-type-scrap'):
    assert class_name in html
assert 'Виж детайли' in html
assert 'data-ajax-link' in html
```

- [ ] **Step 2: Verify the new action contract fails**

Run: `python -m pytest tests/test_ui_contracts.py -q`

Expected: FAIL until every location row exposes the standardized text action.

- [ ] **Step 3: Apply the approved location structure**

Preserve existing search, filters, server pagination, and data attributes. Each row uses three zones: identity/address, operational metadata, and explicit action.

- [ ] **Step 4: Implement semantic top/left rails in both themes**

```css
.location-type-site { --location-accent: var(--site); }
.location-type-warehouse { --location-accent: var(--warehouse); }
.location-type-service { --location-accent: var(--service); }
.location-type-scrap { --location-accent: var(--scrap); }
.location-row-card { border-top: 3px solid var(--location-accent); }
```

- [ ] **Step 5: Verify location data and route state**

Run: `python -m pytest tests/test_ui_contracts.py tests/test_locations_assets.py tests/test_role_visibility.py -q`

Expected: PASS.

- [ ] **Step 6: Build and commit**

Run: `npm run typecheck && npm run build`

Expected: PASS.

```bash
git add templates/locations.html templates/location_detail.html frontend/src/styles/locations.css public/static/styles.css public/static/app.js tests/test_ui_contracts.py
git commit -m "feat: redesign operational locations"
```

---

### Task 8: Complete users, requests, search, profiles, and error states

**Files:**
- Modify: `templates/users.html`
- Modify: `templates/requests.html`
- Modify: `templates/search.html`
- Modify: `templates/profile.html`
- Modify: `templates/error.html`
- Modify: `frontend/src/styles/users.css`
- Modify: `frontend/src/styles/cards.css`
- Modify: `frontend/src/styles/tables.css`
- Modify: `frontend/src/styles/responsive.css`
- Test: `tests/test_ui_contracts.py`

**Interfaces:**
- Consumes: shared table/card/status/button patterns.
- Produces: consistent no-scroll desktop tables, mobile cards, explicit user detail links, guarded approve/reject controls, and actionable empty/error states.

- [ ] **Step 1: Add long-content and permission contracts**

Add tests with a long Bulgarian full name, email, and location name:

```python
assert 'class="user-name user-name-plain truncate-cell"' in users_html
assert f'title="{user.full_name}"' in users_html
assert f'title="{user.email}"' in users_html
assert 'Виж профил' in users_html
```

For requests, keep the existing role matrix assertions and additionally require visible `Одобри` / `Откажи` text only for allowed roles.

- [ ] **Step 2: Run UI and role tests and verify the new explicit-action test fails**

Run: `python -m pytest tests/test_ui_contracts.py tests/test_role_visibility.py -q`

Expected: FAIL until the ellipsis-only user action becomes `Виж профил` and truncation hooks are complete.

- [ ] **Step 3: Update templates without changing route or permission branches**

Use fixed column percentages for desktop, hide only low-priority columns between 900 and 1279px, and reuse labeled mobile cards below 760px. Keep all form methods, CSRF inputs, confirmation attributes, and route names intact.

- [ ] **Step 4: Add actionable empty and error states**

```html
<div class="empty-state panel">
  <h2>Няма намерени резултати</h2>
  <p class="muted">Промени търсенето или изчисти активните филтри.</p>
  <a class="btn-secondary" href="{{ url_for('global_search') }}">Изчисти търсенето</a>
</div>
```

For `error.html`, retain the supplied status/message and add only safe navigation actions.

- [ ] **Step 5: Verify role, request, profile, and search behavior**

Run: `python -m pytest tests/test_ui_contracts.py tests/test_role_visibility.py tests/test_requests_authz.py tests/test_authz_profile_user.py -q`

Expected: PASS.

- [ ] **Step 6: Build and commit**

Run: `npm run typecheck && npm run build`

Expected: PASS.

```bash
git add templates/users.html templates/requests.html templates/search.html templates/profile.html templates/error.html frontend/src/styles/users.css frontend/src/styles/cards.css frontend/src/styles/tables.css frontend/src/styles/responsive.css public/static/styles.css public/static/app.js tests/test_ui_contracts.py
git commit -m "feat: complete the Indigo Redline page system"
```

---

### Task 9: Verify responsiveness, accessibility, full behavior, and Vercel preview

**Files:**
- Modify: `frontend/src/styles/responsive.css`
- Modify: `frontend/src/styles/sidebar.css`
- Modify: `frontend/src/styles/tables.css`
- Modify: `.design/indigo-redline/TASKS.md`
- Create: `.design/indigo-redline/DESIGN_REVIEW.md`
- Create: `.design/indigo-redline/screenshots/`

**Interfaces:**
- Consumes: the complete redesign from Tasks 1–8 and the existing Vercel project `barage-group-supabase-vercel`.
- Produces: verified responsive CSS, design-review evidence, passing full test suite, and a preview URL that is not promoted to production.

- [ ] **Step 1: Run all static and backend verification**

Run:

```bash
npm run typecheck
npm run build
python -m compileall .
python -m pytest -q
python -c "from app import app; print(app.name)"
python -c "from api.index import app; print(app.name)"
```

Expected: every command exits 0; both import checks print the Flask application name.

- [ ] **Step 2: Start the local app with test-safe configuration**

Run: `SECRET_KEY=local-ui-review DATABASE_URL= DATABASE_PATH=/tmp/barage-ui-review.sqlite python app.py`

Expected: the local server starts on its configured local port without exposing production secrets.

- [ ] **Step 3: Capture and review the key visual states**

Use browser automation to capture:

```text
.design/indigo-redline/screenshots/review-login-desktop-light.png
.design/indigo-redline/screenshots/review-dashboard-desktop-light.png
.design/indigo-redline/screenshots/review-dashboard-desktop-dark.png
.design/indigo-redline/screenshots/review-assets-laptop-1280.png
.design/indigo-redline/screenshots/review-assets-mobile-375.png
.design/indigo-redline/screenshots/review-locations-desktop-light.png
.design/indigo-redline/screenshots/review-locations-desktop-dark.png
```

Verify the assets table has no horizontal scrollbar at 1280px, the actions column is visible, full values appear in tooltips, and mobile rows are cards.

- [ ] **Step 4: Verify keyboard, theme, and failure behavior**

In the browser:

1. Tab through navigation, filters, table sorting, actions, and theme toggle; every focused item has a visible red focus ring.
2. Open the mobile menu and press Escape; it closes and returns focus to the menu button.
3. Toggle dark mode, reload, and confirm it persists without a light flash.
4. Simulate a failed AJAX list request and confirm the existing content remains usable and controls are no longer disabled.
5. Enable reduced motion and confirm hover/transition motion is effectively removed.

- [ ] **Step 5: Write the design review and resolve must-fix findings**

Create `.design/indigo-redline/DESIGN_REVIEW.md` with sections for hierarchy, brand fidelity, table density, theme parity, responsiveness, accessibility, and a must-fix list. Fix every must-fix issue, rerun the focused tests, and update the review with the resolution.

- [ ] **Step 6: Mark implementation tasks complete and commit verification artifacts**

```bash
git add .design/indigo-redline frontend/src/styles/responsive.css frontend/src/styles/sidebar.css frontend/src/styles/tables.css public/static/styles.css public/static/app.js
git commit -m "test: verify Indigo Redline responsive design"
```

- [ ] **Step 7: Link the working directory and create a preview deployment**

Run:

```bash
vercel link --yes --project barage-group-supabase-vercel --scope truhchevmihails-projects
vercel deploy --scope truhchevmihails-projects 2>&1 | tee /tmp/barage-preview-deploy.log
```

Expected: Vercel returns a unique preview URL; the deployment target is preview, not production.

- [ ] **Step 8: Verify the preview deployment**

Run:

```bash
BARAGE_PREVIEW_URL=$(rg -o 'https://[^ ]+\.vercel\.app' /tmp/barage-preview-deploy.log | tail -n 1)
vercel inspect "$BARAGE_PREVIEW_URL" --scope truhchevmihails-projects
```

Expected: deployment state is `READY`, framework is Flask, and no production alias was changed.

Open the preview and repeat the login shell, light/dark, assets table, locations, mobile menu, and error-state checks against the deployed build.

- [ ] **Step 9: Commit any preview-only corrections and redeploy preview if required**

```bash
git add templates frontend/src public/static tests .design/indigo-redline
git commit -m "fix: polish Indigo Redline preview"
vercel deploy --scope truhchevmihails-projects
```

Skip this step when the first preview has no corrections. Never add `--prod` and never run `vercel promote` without explicit user approval.
