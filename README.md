# Barage Group Machinery — Flask + Vercel + Supabase

Това е изчистена и подготвена за deploy версия на първоначалния Flask проект за управление на механизация, инструменти, обекти, склад, сервиз, брак, потребители и заявки за преместване.

## Какво е запазено от стария проект

- Flask routes, шаблони и дизайнът от `templates/` и `styles.css`.
- Ролите: **Администратор**, **Проектов ръководител**, **Технически ръководител**, **Складов работник**.
- Модули за машини/активи, локации, потребители, заявки, история и сервизни записи.
- CSRF защита за POST/PUT/PATCH/DELETE операции.
- Ограничения за image upload: размер, MIME/extension проверка и валидиране чрез Pillow, когато е наличен.
- Базов rate limiting за login и чувствителни POST операции.

## Какво е променено за production

- SQLite вече е само fallback за локална разработка. На Vercel приложението изисква `DATABASE_URL` към Supabase Postgres.
- Upload-ите към Vercel не се пишат във filesystem-а. На Vercel приложението изисква Supabase Storage: `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, `SUPABASE_STORAGE_BUCKET`.
- Статичните файлове са преместени в `public/static/`, за да могат да се обслужват като Vercel public assets, но Flask продължава да ги вижда локално през `/static/...`.
- Добавени са `.vercelignore`, `.gitignore`, `.python-version`, `vercel.json`, Supabase SQL файлове и помощни migration scripts.
- Премахнати са от пакета локални артефакти: `.git`, `.venv`, `app.db`, backups, node_modules, logs, cache и качени тестови файлове.

## Структура

```text
api/index.py                         # Vercel entrypoint
app.py                               # Flask приложението
public/static/                       # CSS, JS, лого; не качвай user uploads тук в production
templates/                           # Jinja templates
migrations/                          # Alembic/Flask-Migrate baseline
scripts/run_migrations.py            # изпълнява db upgrade
scripts/create_admin.py              # създава/поправя първи администратор
scripts/migrate_sqlite_to_supabase.py # копира стара SQLite база към Supabase Postgres
scripts/migrate_uploads_to_supabase.py # качва стари local uploads към Supabase Storage
supabase/schema.sql                  # SQL schema за празна Supabase база
supabase/storage.sql                 # Storage bucket setup
vercel.json                          # Vercel rewrite към Flask function
```

## Локално стартиране

```bash
python -m venv .venv
source .venv/bin/activate            # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
```

Попълни минимум `SECRET_KEY` в `.env`. За локален SQLite development можеш да оставиш `DATABASE_PATH=app.db` и празен `DATABASE_URL`.

```bash
python scripts/create_admin.py --email admin@example.com
python app.py
```

Отвори:

```text
http://127.0.0.1:5001/login
```

## Supabase setup

### 1. Database

В Supabase създай project и вземи **Postgres connection string**. За Vercel/serverless използвай pooler connection string на порт `6543`, обикновено Transaction Pooler.

Примерен формат:

```text
postgresql://postgres.<project-ref>:<password>@aws-0-eu-central-1.pooler.supabase.com:6543/postgres?sslmode=require
```

Важното: `DATABASE_URL` не е `https://<project>.supabase.co`. Това е Supabase API URL, не Postgres connection string.

### 2. Schema

Вариант A — през Alembic от локалната машина:

```bash
export SECRET_KEY='long-random-secret'
export DATABASE_URL='postgresql://...supabase.../postgres?sslmode=require'
python scripts/run_migrations.py
```

Вариант B — през Supabase SQL Editor за чисто празна база:

1. отвори `supabase/schema.sql`;
2. копирай SQL-а в Supabase SQL Editor;
3. изпълни го веднъж.

### 3. Storage bucket

В Supabase SQL Editor изпълни:

```sql
-- виж файла supabase/storage.sql
```

По подразбиране приложението очаква bucket:

```text
barage-uploads
```

Bucket-ът е public, за да могат качените изображения да се визуализират директно в HTML чрез public URL. Качването става само от backend-а със service role key.

## Първи администратор в Supabase

След като schema-та е създадена:

```bash
export SECRET_KEY='long-random-secret'
export DATABASE_URL='postgresql://...supabase.../postgres?sslmode=require'
python scripts/create_admin.py --email admin@example.com
```

Може и non-interactive:

```bash
ADMIN_EMAIL=admin@example.com ADMIN_PASSWORD='StrongPassword123' \
SECRET_KEY='long-random-secret' DATABASE_URL='postgresql://...' \
python scripts/create_admin.py
```

## Миграция от старото `app.db`

Ако искаш да прехвърлиш данните от стария SQLite файл:

```bash
export SECRET_KEY='long-random-secret'
export DATABASE_URL='postgresql://...supabase.../postgres?sslmode=require'
python scripts/migrate_sqlite_to_supabase.py --sqlite /path/to/old/app.db --truncate
```

След това, ако старият проект има файлове в `static/uploads/`, качи ги в Supabase Storage и обнови URL-ите в базата:

```bash
export SUPABASE_URL='https://your-project-ref.supabase.co'
export SUPABASE_SERVICE_ROLE_KEY='your-service-role-key'
export SUPABASE_STORAGE_BUCKET='barage-uploads'
python scripts/migrate_uploads_to_supabase.py --upload-root /path/to/old/static/uploads
```

Първо можеш да провериш без реални промени:

```bash
python scripts/migrate_uploads_to_supabase.py --upload-root /path/to/old/static/uploads --dry-run
```

## Deploy във Vercel

1. Качи този проект в GitHub repo.
2. Във Vercel избери **New Project** и импортни repo-то.
3. В Project Settings → Environment Variables добави:

```text
APP_ENV=production
SECRET_KEY=<дълъг random secret>
DATABASE_URL=<Supabase Postgres pooler connection string>
SUPABASE_URL=https://<project-ref>.supabase.co
SUPABASE_SERVICE_ROLE_KEY=<service-role-key>
SUPABASE_STORAGE_BUCKET=barage-uploads
SUPABASE_STORAGE_PREFIX=uploads
PREFERRED_URL_SCHEME=https
```

4. Deploy.
5. След deploy отвори `/login`.

`SUPABASE_SERVICE_ROLE_KEY` трябва да стои само като backend environment variable във Vercel. Не го слагай в HTML, JavaScript или публично repo.

## Проверки преди production

- `SECRET_KEY` е различен от development стойностите.
- `DATABASE_URL` е Supabase Postgres URL, не Supabase API URL.
- `APP_ENV=production` е зададен, за да се включи secure cookie режим.
- Supabase Storage bucket-ът съществува и е public, ако ще показваш директни image URL-и.
- Има създаден поне един администратор.
- Старите local uploads са мигрирани, ако има реални снимки.
- `.env`, `app.db`, `.venv`, backups и uploads не са commit-нати.

## Тестове

```bash
SECRET_KEY=test-secret PYTHONPATH=. pytest -q
```

В този пакет тестовете минават локално със SQLite test база.
