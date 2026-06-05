# Migrations Plan

## Current state

Схемата в момента се поддържа чрез:

- `init_database()`
- `ensure_database_compatibility()`
- runtime `ALTER TABLE` логика за SQLite

Това е удобно за development, но е слабо за production rollout, rollback и auditability.

## Target

Да се премине към Alembic / Flask-Migrate с контролирани migration файлове.

## Suggested rollout

### Phase 1: Baseline

1. Направи backup на:
   - `app.db`
   - `static/uploads/`
   - `service_invoice_images.json`
2. Freeze-вай текущата production схема като baseline migration.
3. Документирай точния build/commit, от който е взет baseline.

### Phase 2: Introduce tooling

1. Добави `Flask-Migrate` / `Alembic`.
2. Инициализирай migration repository.
3. Генерирай първа baseline migration, без да променяш schema semantics.

### Phase 3: Controlled schema changes

Премести бъдещи промени от `ensure_database_compatibility()` към отделни migration файлове:

- нови колони;
- индекси;
- nullable / FK корекции;
- soft-delete полета, ако бъдат одобрени.

### Phase 4: Decommission runtime patching

След като production средата е мигрирана:

1. Спри нови `ALTER TABLE` операции в `ensure_database_compatibility()`;
2. Остави само безопасни compatibility checks, ако са още нужни;
3. В дългосрочен план премахни runtime schema mutation изцяло.

## Special notes

- Преди migration rollout винаги прави backup.
- SQLite migration-ите трябва да се тестват върху копие на реална база.
- Ако по-късно се мине към PostgreSQL, това трябва да е отделен migration проект, не част от текущия hardening pass.

## Deferred design decisions

Тези промени изискват отделно одобрение:

- soft delete за `Asset`, `User`, `Location`, `TransferRequest`;
- preservation на request/history relationships чрез nullable FKs;
- преместване на uploads извън `static/`;
- пълно запазване на audit следи при destructive deletes.
