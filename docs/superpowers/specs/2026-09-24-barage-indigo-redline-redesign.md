# Barage Machinery — Indigo Redline Redesign

## Objective

Redesign the complete Barage Machinery operational interface while preserving the existing Flask backend, Jinja templates, authorization rules, database schema, routes, server-side filtering, sorting, and pagination.

The result must feel like a purpose-built Barage Group product: compact, precise, visually polished, and efficient for daily work with machinery, locations, requests, users, service records, and inventory data.

## Approved Direction

The approved direction is **Indigo Redline** with a **compact operational density**.

- Indigo and graphite create the stable structural foundation.
- Barage signal red provides brand character and identifies primary actions, active navigation, keyboard focus, and important emphasis.
- White and near-black preserve the visual language of the official Barage Group website and logo.
- Both light and dark themes are first-class experiences.
- Important actions always use visible Bulgarian text. Icons may support labels but must not replace them.
- Layouts use the available screen width and avoid narrow marketing-style containers.

## Product Constraints

- Keep Python and Flask.
- Keep Jinja templates.
- Keep Bulgarian interface labels and messages.
- Do not change authentication, authorization, or database behavior.
- Do not change the database schema.
- Preserve server-side filtering, sorting, and pagination.
- Do not expose or modify secrets.
- Make frontend source changes in `frontend/src` and generate production assets through the existing Vite build.

## Visual System

### Core palette

The exact shades may be adjusted during accessibility verification, but the semantic roles are fixed:

- Brand red: approximately `#DC252E` for primary actions and active emphasis.
- Brand red hover: approximately `#A9161D`.
- Indigo structural surface: approximately `#20243C`.
- Light canvas: approximately `#F7F7FB`.
- Light surface: `#FFFFFF`.
- Dark canvas: approximately `#11111B`.
- Dark surface: approximately `#1A1A26`.
- Semantic green: success, on-site, and approved states.
- Semantic amber: service, warning, and pending states.
- Semantic blue/indigo: warehouse, informational, and secondary emphasis.
- Neutral gray: scrap, disabled, and archival states.

Semantic state colors must not depend on color alone; every state also needs a Bulgarian text label.

### Typography

- Use a modern system-first sans-serif stack with excellent Bulgarian Cyrillic rendering.
- Use strong, compact headings with limited letter spacing.
- Use tabular numerals for inventory numbers, totals, dates, and currency where supported.
- Keep table text compact but never below a comfortably readable operational size.

### Shape and depth

- Use controlled radii rather than uniformly pill-shaped components.
- Buttons and fields use medium radii.
- Panels and summary containers use slightly larger radii.
- Shadows stay subtle; borders and tonal surfaces provide most grouping.
- Avoid glass effects, decorative gradients, and heavy animation.

## Theme Behavior

- Provide one clearly labeled light/dark theme control.
- Preserve the user's explicit choice in local storage.
- Use the system preference only when no explicit choice exists.
- Apply the theme before the page renders to prevent a light/dark flash.
- Ensure every surface, status, form, table, menu, alert, and empty state is designed for both themes.
- Keep focus rings and semantic contrast visible in both themes.

## Global Layout

### Sidebar

- Compact fixed sidebar on desktop.
- Full text labels for Dashboard, Machines, Requests, Locations, and Users.
- Red active state with high-contrast text.
- Brand block uses the existing Barage logo and a restrained product subtitle.
- User identity, role, profile, theme control, and logout remain visible and understandable.
- Mobile uses a compact header and an explicit menu toggle with text.

### Page header

- Compact page context and title on the left.
- Primary and secondary text-labeled actions on the right.
- Actions may wrap at intermediate widths but must remain discoverable.
- Destructive actions remain visually separate from primary actions.

### Content

- Use the full available width.
- Keep vertical spacing tight enough for operational work.
- Separate sections through tonal surfaces, borders, and headings rather than excessive whitespace.

## Component System

### Buttons

Provide five consistent variants:

1. Primary red filled button for the main action.
2. Secondary outlined button for navigation and secondary operations.
3. Neutral button for low-emphasis controls.
4. Text action for row-level links such as “Виж детайли”.
5. Danger button for destructive actions.

All important buttons use text. Icon-only controls are limited to universally understood, low-risk utilities and must include an accessible name and tooltip.

### Panels and containers

- Standard panel for grouped content.
- KPI summary card with a semantic top rail.
- Location container with a type-specific rail and text label.
- Detail field container for asset and user metadata.
- Alert banner for service warnings and errors.
- Empty state with a concrete next action when permitted.

### Forms

- Compact labels and controls with consistent heights.
- Required fields are marked in text and visually.
- Validation messages appear adjacent to the related control.
- Keyboard focus is highly visible.
- Form actions remain stable and use explicit labels.
- Multi-column forms collapse to one column on mobile.

### Statuses

- Site / on-site: green family.
- Warehouse: blue or indigo family.
- Service: amber family.
- Scrap: neutral gray family.
- Pending: amber.
- Approved: green.
- Rejected and destructive errors: red.

Every status includes text and is readable without relying on the background color.

## Data Tables

The approved table approach is a **fixed compact table** with maximum visible data and no horizontal scrollbar on standard laptop and desktop widths.

### Desktop behavior

- Target row height: approximately 44–48 pixels.
- Use controlled fixed widths for compact fields.
- Allow the main descriptive field to take the remaining width.
- Keep the actions column visible.
- Show almost all important columns on screens at or above approximately 1280 pixels.
- Use ellipsis for values that exceed their allocated width.
- Expose the complete value through the native title tooltip or an accessible equivalent.
- Use short Bulgarian headings where clarity is preserved.
- Keep table sorting links obvious and keyboard accessible.

### Intermediate widths

- Between approximately 900 and 1280 pixels, hide only one or two lowest-priority columns when necessary.
- Never create client-side-only sorting for server-paginated data.
- Preserve all active query parameters through pagination, filtering, and sorting.

### Mobile behavior

- Below approximately 760 pixels, transform rows into compact labeled cards.
- Keep the primary identifier, title, location, status, and action immediately visible.
- Do not force a compressed desktop table or horizontal scrolling.

### Assets table priorities

At full width, prioritize:

1. Inventory number.
2. Type/name.
3. Alias.
4. Brand.
5. Model.
6. Serial number.
7. Location.
8. Status or relevant warning.
9. Text action.

The action must read “Виж детайли” rather than using an ellipsis-only button.

## Page Designs

### Login

- Use a restrained split layout with Barage brand presence.
- Keep the form short, direct, and centered in its working area.
- Include the theme control without distracting from login.
- Preserve existing authentication behavior and messaging.

### Dashboard

- Compact KPI strip for total, on-site, warehouse, service, and scrap counts.
- Strong global search near the top.
- Visible pending-request and long-service warnings.
- Compact grids for recent assets and service items.
- Two-column recent requests and activity section where width allows.

### Assets

- Use the approved fixed compact table.
- Keep search, location filter, active filter chips, import/export, and creation actions clear.
- Preserve backend sorting and pagination.
- Keep service-stay warnings visible but compact.

### Locations

- Use type-specific summary containers and location rows.
- Distinguish site, warehouse, service, and scrap through both label and colored rail.
- Present name, city/address, responsible people, asset count, and explicit detail action consistently.
- Preserve filters, sorting, and pagination state.

### Requests

- Keep request status prominent.
- Separate approve and reject actions clearly.
- Show source, destination, asset, requester, and time in a compact scan path.
- Preserve authorization behavior.

### Users

- Use a compact table for name, email, phone, role, locations, status, and detail action.
- Keep role and status visually distinct.
- Keep full names and emails accessible through tooltip when shortened.

### Detail pages

- Group metadata into compact detail-field containers.
- Keep important actions visible without obscuring content.
- Preserve copy-to-clipboard behavior.
- Use clear sections for images, notes, service history, and audit history.
- Collapsible sections must remain keyboard accessible.

### Create and edit forms

- Group related fields into understandable sections.
- Keep a compact two-column desktop layout and single-column mobile layout.
- Preserve upload limits and backend validation.
- Use explicit Save, Cancel, Move, Approve, Reject, and Delete labels.

## Interaction and Feedback

- Keep animation durations short and functional.
- Respect reduced-motion preferences.
- Provide visible hover, active, focus, disabled, loading, success, warning, and error states.
- AJAX list navigation must keep clear progress feedback and restore usable controls after failure.
- Confirmation dialogs remain for destructive operations.
- Flash messages and toasts use semantic styling and readable Bulgarian text.

## Accessibility

- Target WCAG AA contrast for text and essential controls.
- Provide strong `:focus-visible` treatment.
- Preserve semantic HTML structure.
- Give icon utilities accessible names.
- Maintain comfortable pointer targets even in compact layouts.
- Ensure status meaning is available in text.
- Verify keyboard navigation for sidebar, command palette, forms, table sorting, menus, and collapsible sections.

## Error and Empty States

- Explain what happened in direct Bulgarian.
- Preserve user-entered form values when validation fails.
- Provide a clear next action where appropriate.
- Empty tables and lists must differentiate between “no records exist” and “no records match the filters.”
- Network/AJAX failures must leave the current page usable.

## Implementation Boundaries

- Prefer CSS and small template changes over new dependencies.
- Keep TypeScript modules focused and reuse the existing theme, sidebar, search, AJAX, and table behavior.
- Add or change JavaScript only when CSS and semantic HTML cannot provide the required behavior.
- Do not introduce a new frontend framework.

## Validation and Review

Before preview deployment:

- Run `npm run typecheck`.
- Run `npm run build`.
- Run `python -m compileall .`.
- Run `python -m pytest -q`.
- Verify both Flask entry points import correctly.
- Check key pages at desktop, laptop, tablet, and mobile widths.
- Check every key page in light and dark themes.
- Verify tables have no horizontal scrollbar at supported desktop widths.
- Verify keyboard focus, responsive layouts, empty states, alerts, and form errors.

## Delivery Strategy

- Implement the redesign on a separate branch.
- Deploy a Vercel preview only.
- Do not promote or deploy to production before explicit user approval.
- Present the preview URL and a concise list of changed pages.
- Incorporate review feedback before any production action.

## Success Criteria

- The product is recognizably Barage Group rather than a generic admin theme.
- The interface is compact enough for daily operational use.
- Almost all important table columns are visible without horizontal scrolling on standard laptop and desktop widths.
- Every important action is explicit and understandable.
- Light and dark themes are equally complete.
- Existing application behavior and permissions continue to work.
- The Vercel preview passes automated checks and visual review before production.
