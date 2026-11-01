import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
import subprocess

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import library


def sample():
    return {'Name': 'Frost healer', 'Icon': 'Interface\\Icons\\Spell_Frost_FrostBolt02',
            'Description': 'A player-written guide — 冰\nSecond line', 'Category': 'Leveling',
            'Roles': 'PLAYER_ROLE_HEALER', 'PrimaryStat': 'STAT_SPIRIT',
            'DifficultyRating': 'BUILD_DIFFICULTY_RATING_NORMAL',
            'Spells': [{'Spell': 116, 'Level': 4, 'IsCoreAbility': True}],
            'RandomEnchants': [{'Enchant': 86576, 'Stacks': 1, 'Level': 10}],
            'ArmorTypes': [{'Type': 'ITEM_SUBCLASS_ARMOR_CLOTH'}], 'WeaponTypes': []}


class LibraryTests(unittest.TestCase):
    def test_public_draft_does_not_export_local_assignment(self):
        build = sample()
        build.update(Category='BuildDraft', Description='Guide\n###AREA52_ARCHETYPE_ID=97')
        before = copy.deepcopy(build)
        record = library.make_record(build, 'Tester', 'area52-v1')
        decoded = library.decode(library.encode(record['build']))
        self.assertEqual(decoded['Category'], 'Leveling')
        self.assertEqual(decoded['Description'], 'Guide')
        self.assertEqual(build, before)

    def test_roundtrip_and_private_identity_exclusion(self):
        build = sample()
        build.update(ID='123', Owner=456, Author='private character', Featured=True, Certified=True)
        before = copy.deepcopy(build)
        clean = library.decode(library.encode(build))
        self.assertEqual(clean, library.validate_build(build))
        self.assertEqual(build, before)
        self.assertFalse(set(clean) & {'ID', 'Owner', 'Author', 'Featured', 'Certified'})
        self.assertEqual(clean['Description'], build['Description'])

    def test_malformed_codes(self):
        for code in ['', 'A52B1:0', 'A52B1:zz', 'https://example.com', 'x' * 100001,
                     'A52B1:' + b't2:s1:an1:s1:an2:'.hex(),
                     'A52B1:' + b't1:b1n1:'.hex(),
                     'A52B1:' + b't1:s1:at1:s1:at1:s1:at1:s1:at1:s1:at1:s1:an1:'.hex(),
                     'A52B1:' + b's8193:'.hex(), library.encode(sample()) + '00']:
            with self.subTest(code=code[:30]), self.assertRaises(ValueError):
                library.decode(code)

    def test_invalid_selections(self):
        for mutate in [lambda b: b['Spells'].append(b['Spells'][0]),
                       lambda b: b['RandomEnchants'][0].update(Stacks=0),
                       lambda b: b['Spells'][0].update(Level=81),
                       lambda b: b['Spells'][0].update(Spell=True),
                       lambda b: b.update(Category='Featured'),
                       lambda b: b.update(Name='é' * 65),
                       lambda b: b['Spells'][0].update(IsCoreAbility=1)]:
            b = sample(); mutate(b)
            with self.assertRaises(ValueError):
                library.encode(b)

    def test_record_integrity(self):
        record = library.make_record(sample(), 'Public alias', 'test-catalog')
        for mutate in [lambda r: r['build'].update(Owner=1),
                       lambda r: r['build'].update(Name='modified'),
                       lambda r: r.update(revision=True),
                       lambda r: r.update(id='../../file'),
                       lambda r: r.update(license='proprietary'),
                       lambda r: r.update(account_id=5)]:
            bad = copy.deepcopy(record); mutate(bad)
            with self.assertRaises(ValueError):
                library.validate_record(bad)

    def test_current_revisions_and_index(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            record = library.make_record(sample(), 'Public alias', 'test-catalog')
            path = library.store(root, record)
            self.assertEqual(path, library.store(root, record))
            changed = library.make_record(sample(), 'Other alias', 'test-catalog', record['id'])
            with self.assertRaises(ValueError):
                library.store(root, changed)
            changed['revision'] = 2
            library.store(root, changed)
            self.assertEqual(len(library.index(root)['builds']), 1)
            path.write_text(json.dumps(dict(record, id='invalid')))
            with self.assertRaises(ValueError):
                library.index(root)

    def test_duplicate_json_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / 'bad.json'
            p.write_text('{"schema":1,"schema":2}')
            with self.assertRaises(ValueError):
                library.read_json(p)

    def test_cli_export_import_and_catalog_mismatch(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            code = root / 'source.txt'
            code.write_text(library.encode(sample()), encoding='utf-8')
            tool = str(Path(library.__file__))
            def run(*args):
                return subprocess.run([sys.executable, '-X', 'utf8', tool, *map(str, args)], capture_output=True)
            exported = run('export', code, '--root', root, '--author', 'Public alias', '--catalog', 'v1', '--accept-cc0')
            self.assertEqual(exported.returncode, 0, exported.stderr)
            record = next((root / 'builds').glob('*/*.json'))
            output = root / 'import.txt'
            self.assertNotEqual(run('import', record, '--catalog', 'v2', '--output', output).returncode, 0)
            self.assertFalse(output.exists())
            self.assertEqual(run('import', record, '--catalog', 'v1', '--output', output).returncode, 0)
            self.assertEqual(library.decode(output.read_text()), library.decode(code.read_text()))
            self.assertNotEqual(run('import', record, '--catalog', 'v1', '--output', output).returncode, 0)
            self.assertEqual(run('validate', '--root', root).returncode, 0)


if __name__ == '__main__':
    unittest.main()
