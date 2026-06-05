"""Upload old local files to Supabase Storage and rewrite DB file URLs.

Run after SQLite -> Supabase data migration if your old DB contains paths like
/static/uploads/assets/file.jpg.

Example:
  SECRET_KEY=... DATABASE_URL=... SUPABASE_URL=... SUPABASE_SERVICE_ROLE_KEY=... \
  SUPABASE_STORAGE_BUCKET=barage-uploads \
  python scripts/migrate_uploads_to_supabase.py --upload-root /path/to/old/static/uploads
"""

from __future__ import annotations

import argparse
import mimetypes
import sys
from pathlib import Path
from uuid import uuid4

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app import (  # noqa: E402
    AssetImage,
    AssetServiceRecord,
    SUPABASE_STORAGE_BUCKET,
    SUPABASE_STORAGE_PREFIX,
    app,
    db,
    extract_service_invoice_path,
    get_supabase_storage_client,
    storage_url_from_key,
    supabase_storage_enabled,
)

LOCAL_PREFIXES = (
    "/static/uploads/",
    "static/uploads/",
    "/public/static/uploads/",
    "public/static/uploads/",
)


def parse_args():
    parser = argparse.ArgumentParser(description="Move DB-referenced local uploads to Supabase Storage.")
    parser.add_argument("--upload-root", action="append", help="Old upload root. Can be passed more than once.")
    parser.add_argument("--dry-run", action="store_true", help="Print planned changes without uploading/updating DB")
    parser.add_argument("--upsert", action="store_true", help="Overwrite objects in Supabase if keys already exist")
    return parser.parse_args()


def default_roots(args) -> list[Path]:
    roots = [Path(item).expanduser().resolve() for item in (args.upload_root or [])]
    roots.extend([
        PROJECT_ROOT / "static" / "uploads",
        PROJECT_ROOT / "public" / "static" / "uploads",
    ])
    unique: list[Path] = []
    for root in roots:
        root = root.resolve()
        if root not in unique:
            unique.append(root)
    return unique


def relative_local_path(reference: str) -> Path | None:
    if not reference:
        return None
    if reference.startswith("http://") or reference.startswith("https://"):
        return None
    normalized = reference.replace("\\", "/")
    for prefix in LOCAL_PREFIXES:
        if normalized.startswith(prefix):
            return Path(normalized[len(prefix):])
    if normalized.startswith("/"):
        normalized = normalized[1:]
    if normalized.startswith("uploads/"):
        return Path(normalized[len("uploads/"):])
    return None


def resolve_source_file(reference: str, roots: list[Path]) -> tuple[Path, Path] | tuple[None, None]:
    rel = relative_local_path(reference)
    if rel is None:
        return None, None
    for root in roots:
        candidate = (root / rel).resolve()
        try:
            candidate.relative_to(root.resolve())
        except ValueError:
            continue
        if candidate.exists() and candidate.is_file():
            return candidate, rel
    return None, rel


def supabase_key_for(rel: Path) -> str:
    safe_name = "/".join(part for part in rel.parts if part not in {"", ".", ".."})
    if not safe_name:
        safe_name = f"migrated/{uuid4().hex}"
    prefix = SUPABASE_STORAGE_PREFIX.strip("/ ")
    return f"{prefix}/{safe_name}" if prefix else safe_name


def upload_file(client, source_path: Path, key: str, *, upsert: bool) -> str:
    content_type = mimetypes.guess_type(source_path.name)[0] or "application/octet-stream"
    payload = source_path.read_bytes()
    client.storage.from_(SUPABASE_STORAGE_BUCKET).upload(
        path=key,
        file=payload,
        file_options={"content-type": content_type, "x-upsert": "true" if upsert else "false"},
    )
    return storage_url_from_key(key)


def collect_references() -> set[str]:
    references = {row.file_path for row in AssetImage.query.with_entities(AssetImage.file_path).all() if row.file_path}
    for record in AssetServiceRecord.query.with_entities(AssetServiceRecord.notes).all():
        invoice_path = extract_service_invoice_path(record.notes)
        if invoice_path:
            references.add(invoice_path)
    return references


def main():
    args = parse_args()
    roots = default_roots(args)
    with app.app_context():
        if not supabase_storage_enabled():
            raise SystemExit("Set SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY and SUPABASE_STORAGE_BUCKET first.")
        client = None if args.dry_run else get_supabase_storage_client()
        replacements: dict[str, str] = {}

        for reference in sorted(collect_references()):
            source_path, rel = resolve_source_file(reference, roots)
            if rel is None:
                print(f"skip non-local reference: {reference}")
                continue
            if source_path is None:
                print(f"missing local file for {reference}; expected relative path {rel}")
                continue
            key = supabase_key_for(rel)
            new_url = storage_url_from_key(key)
            print(f"{reference} -> {new_url}")
            if not args.dry_run:
                new_url = upload_file(client, source_path, key, upsert=args.upsert)
            replacements[reference] = new_url

        if args.dry_run:
            print(f"dry-run complete; {len(replacements)} replacements planned")
            return

        for old, new in replacements.items():
            AssetImage.query.filter_by(file_path=old).update({"file_path": new}, synchronize_session=False)
            records = AssetServiceRecord.query.all()
            for record in records:
                if record.notes and old in record.notes:
                    record.notes = record.notes.replace(old, new)
        db.session.commit()
        print(f"uploaded and rewrote {len(replacements)} references")


if __name__ == "__main__":
    main()
