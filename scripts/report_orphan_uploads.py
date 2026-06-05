import argparse
import os
import sys
from pathlib import Path

os.environ.setdefault('SECRET_KEY', 'orphan-report-secret')

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app import app, AssetImage, BASE_DIR, SERVICE_INVOICE_MAP, UPLOAD_FOLDER, load_service_invoice_map  # noqa: E402


def collect_referenced_paths():
    referenced = {row.file_path for row in AssetImage.query.with_entities(AssetImage.file_path).all() if row.file_path}
    referenced.update(path for path in load_service_invoice_map().values() if path)
    return referenced


def to_public_reference(path: Path) -> str:
    rel_path = path.relative_to(Path(BASE_DIR)).as_posix()
    return f'/{rel_path}'


def main():
    parser = argparse.ArgumentParser(description='Report orphan upload files. Dry-run by default.')
    parser.add_argument('--apply', action='store_true', help='Delete orphan files. Use with care.')
    args = parser.parse_args()

    with app.app_context():
        uploads_root = Path(UPLOAD_FOLDER)
        referenced = collect_referenced_paths()
        orphan_files = []

        if uploads_root.exists():
            for file_path in uploads_root.rglob('*'):
                if not file_path.is_file():
                    continue
                public_ref = to_public_reference(file_path)
                if public_ref not in referenced:
                    orphan_files.append(file_path)

        print(f'Upload root: {uploads_root}')
        print(f'Referenced upload paths: {len(referenced)}')
        print(f'Orphan files found: {len(orphan_files)}')
        for orphan in orphan_files:
            print(f' - {orphan}')

        if args.apply:
            for orphan in orphan_files:
                orphan.unlink(missing_ok=True)
            print(f'Deleted orphan files: {len(orphan_files)}')
        else:
            print('Dry run only. Re-run with --apply to delete the listed files.')


if __name__ == '__main__':
    main()
