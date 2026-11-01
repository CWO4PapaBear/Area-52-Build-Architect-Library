import copy
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from library import canonical, make_record, store, index, decode, encode
from catalog import page
from layout import migrate, build_path, catalog_path, entry, check_index, check_entry
from test_library import sample


class LayoutTests(unittest.TestCase):
    def test_legacy_migration_latest_identity_and_idempotence(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            first = make_record(sample(), 'Shared alias', 'v1')
            second = make_record(dict(sample(), Name='Renamed build'), 'Shared alias', 'v1', first['id'], 2)
            other = make_record(dict(sample(), Name='Renamed build'), 'Shared alias', 'v1')
            for record in (first, second, other):
                path = root / 'builds' / record['id'] / (str(record['revision']) + '.json')
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(canonical(record))
                path = root / 'catalog' / record['id'] / (str(record['revision']) + '.md')
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(page(record).encode())
            result = migrate(root)
            self.assertEqual(result['schema'], 2)
            self.assertEqual(len(result['builds']), 2)
            self.assertEqual(migrate(root), result)
            self.assertEqual((root / build_path(second)).read_bytes(), canonical(second))
            self.assertEqual(len(list((root / 'builds').glob('*/*.json'))), 2)
            self.assertEqual(len(list((root / 'catalog').glob('*/*.md'))), 2)
            self.assertNotEqual(build_path(second), build_path(other))
            self.assertIn('Shared alias', (root / 'CATALOG.md').read_text())
            self.assertEqual(decode(encode(second['build'])), second['build'])

    def test_update_rename_stale_revision_and_same_revision_conflict(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            first = make_record(sample(), 'Alias', 'v1')
            second = make_record(dict(sample(), Name='New name'), 'Alias', 'v1', first['id'], 2)
            store(root, first)
            store(root, second)
            self.assertFalse((root / build_path(first)).exists())
            self.assertFalse((root / catalog_path(entry(first))).exists())
            self.assertEqual(index(root)['builds'], [entry(second)])
            with self.assertRaises(ValueError):
                store(root, first)
            altered = make_record(sample(), 'Alias', 'v1', first['id'], 2)
            with self.assertRaises(ValueError):
                store(root, altered)
            self.assertEqual(index(root)['builds'], [entry(second)])

    def test_paths_and_index_reject_spoofing(self):
        record = make_record(dict(sample(), Name='../../CON\\evil'), 'Alias', 'v1')
        item = entry(record)
        self.assertNotIn('..', item['path'])
        check_index({'schema': 2, 'builds': [item]})
        check_entry(item, canonical(record))
        for key, value in [('path', '../secret'), ('author', 'Impostor'), ('sha256', '0' * 64)]:
            altered = dict(item, **{key: value})
            with self.assertRaises(ValueError):
                check_index({'schema': 2, 'builds': [altered]})
                check_entry(altered, canonical(record))
        with self.assertRaises(ValueError):
            check_index({'schema': 2, 'builds': [item, item]})

    def test_migration_rejects_edited_page_before_writes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            record = make_record(sample(), 'Alias', 'v1')
            store(root, record)
            target = root / catalog_path(entry(record))
            target.write_bytes(b'hand edited')
            before = {str(p): p.read_bytes() for p in root.rglob('*') if p.is_file()}
            with self.assertRaises(ValueError):
                migrate(root)
            self.assertEqual(before, {str(p): p.read_bytes() for p in root.rglob('*') if p.is_file()})


if __name__ == '__main__':
    unittest.main()
