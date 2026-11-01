"""Portable Area 52 build records; no client assets, credentials or database writes."""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import re
import uuid

MAX_CODE = 100000
CATEGORIES = {'Leveling', 'Level60PvE', 'Level60PvP', 'Level70PvE', 'Level70PvP',
              'BuildDraft', 'BuildDraftEndGamePvE', 'BuildDraftEndGamePvP'}
ROLES = {'PLAYER_ROLE_' + v for v in ('NONE', 'LEADER', 'TANK', 'HEALER', 'DAMAGE', 'ANY')}
STATS = {'STAT_' + v for v in ('STRENGTH', 'AGILITY', 'INTELLECT', 'SPIRIT')}
DIFFICULTIES = {'BUILD_DIFFICULTY_RATING_' + v for v in ('EASY', 'NORMAL', 'HARD', 'VERY_HARD', 'IMPOSSIBLE')}
ARMOR = {'ITEM_SUBCLASS_ARMOR_' + v for v in ('CLOTH', 'LEATHER', 'MAIL', 'PLATE', 'SHIELD', 'LIBRAM', 'IDOL', 'TOTEM', 'SIGIL')}
WEAPONS = {'ITEM_SUBCLASS_WEAPON_' + v for v in ('AXE', 'AXE2', 'BOW', 'GUN', 'MACE', 'MACE2', 'POLEARM', 'SWORD', 'SWORD2', 'STAFF', 'FIST', 'DAGGER', 'THROWN', 'CROSSBOW', 'WAND')}
SPELL_ROLES = ('IsCoreAbility', 'IsOptimalAbility', 'IsEmpoweringAbility', 'IsSynergisticAbility')


def require(condition, message):
    if not condition:
        raise ValueError(message)


def number(value, maximum=4294967295, minimum=0):
    require(type(value) is int and minimum <= value <= maximum, 'Invalid integer')
    return value


def text(value, maximum):
    require(isinstance(value, str) and '\0' not in value and len(value.encode('utf-8')) <= maximum, 'Invalid text')
    return value


def choice(value, values):
    require(value in values, 'Unsupported enum value')
    return value


def sequence(value, maximum):
    if isinstance(value, dict):
        require(all(type(k) is int for k in value) and set(value) == set(range(1, len(value) + 1)), 'Invalid array keys')
        value = [value[k] for k in range(1, len(value) + 1)]
    require(isinstance(value, list) and len(value) <= maximum, 'Invalid array')
    return value


def validate_build(build):
    require(isinstance(build, dict), 'Expected build object')
    out = {k: text(build.get(k, ''), limit) for k, limit in (('Name', 128), ('Icon', 256), ('Description', 8192))}
    require(bool(out['Name'].strip()), 'Missing build name')
    for key, values in (('Category', CATEGORIES), ('Roles', ROLES), ('PrimaryStat', STATS), ('DifficultyRating', DIFFICULTIES)):
        out[key] = choice(build.get(key), values)
    for key, id_key, limit in (('Spells', 'Spell', 512), ('RandomEnchants', 'Enchant', 64), ('ArmorTypes', 'Type', 32), ('WeaponTypes', 'Type', 32)):
        rows, seen = [], set()
        for row in sequence(build.get(key), limit):
            require(isinstance(row, dict), 'Invalid selection')
            if id_key == 'Type':
                item = {'Type': choice(row.get('Type'), ARMOR if key == 'ArmorTypes' else WEAPONS)}
            else:
                item = {id_key: number(row.get(id_key), minimum=1),
                        'Level': number(row.get('Level', 1), 80), 'Flags': number(row.get('Flags', 0))}
                if id_key == 'Enchant':
                    item['Stacks'] = number(row.get('Stacks'), 17, 1)
                else:
                    for field in SPELL_ROLES:
                        require(type(row.get(field, False)) is bool, 'Invalid spell role')
                        item[field] = row.get(field, False)
            item['Comment'] = text(row.get('Comment', ''), 128)
            require(item[id_key] not in seen, 'Duplicate selection')
            seen.add(item[id_key])
            rows.append(item)
        out[key] = rows
    return out


def pack(value):
    if isinstance(value, str):
        raw = value.encode('utf-8')
        return b's' + str(len(raw)).encode() + b':' + raw
    if type(value) is bool:
        return b'b1' if value else b'b0'
    if type(value) is int:
        return b'n' + str(number(value)).encode() + b':'
    if isinstance(value, list):
        value = dict(enumerate(value, 1))
    require(isinstance(value, dict), 'Unsupported value')
    keys = sorted(value, key=str)
    return b't' + str(len(keys)).encode() + b':' + b''.join(pack(k) + pack(value[k]) for k in keys)


def encode(build):
    result = 'A52B1:' + pack(validate_build(build)).hex()
    require(len(result) <= MAX_CODE, 'Build exceeds code limit')
    return result


def decode(code):
    require(isinstance(code, str) and len(code) <= MAX_CODE, 'Build code exceeds limit')
    code = code.strip()
    require(code.startswith('A52B1:') and re.fullmatch(r'(?:[0-9a-fA-F]{2})*', code[6:]), 'Invalid build code')
    raw = bytes.fromhex(code[6:])
    position, nodes = 0, 0

    def read(depth):
        nonlocal position, nodes
        nodes += 1
        require(depth <= 5 and nodes <= 16000 and position < len(raw), 'Invalid nesting or truncated code')
        kind = raw[position:position + 1]
        position += 1
        if kind == b'b':
            value = raw[position:position + 1]
            require(value in (b'0', b'1'), 'Invalid boolean')
            position += 1
            return value == b'1'
        end = raw.find(b':', position)
        digits = raw[position:end] if end >= 0 else b''
        require(0 < len(digits) <= 10 and digits.isdigit(), 'Invalid length')
        size = int(digits)
        position = end + 1
        if kind == b'n':
            return number(size)
        if kind == b's':
            require(size <= 8192 and position + size <= len(raw), 'Truncated text')
            value = raw[position:position + size].decode('utf-8')
            position += size
            return value
        require(kind == b't' and size <= 512, 'Invalid table')
        value = {}
        for _ in range(size):
            key = read(depth + 1)
            require(type(key) in (int, str) and key not in value, 'Invalid or repeated key')
            value[key] = read(depth + 1)
        return value

    result = read(0)
    require(position == len(raw), 'Trailing build data')
    return validate_build(result)


def canonical(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + '\n').encode('utf-8')


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def make_record(build, author, catalog, identity=None, revision=1):
    clean = validate_build(build)
    import re
    clean['Description'] = re.sub(r'\n*###AREA52_ARCHETYPE_ID[^#]*', '', clean['Description'])
    if clean['Category'].startswith('BuildDraft'):
        clean['Category'] = 'Leveling'
    record = {'schema': 1, 'id': str(uuid.UUID(identity)) if identity else str(uuid.uuid4()),
              'revision': number(revision, minimum=1), 'license': 'CC0-1.0',
              'author': text(author, 128), 'compatibility': {'realm': 'area52', 'catalog': text(catalog, 128)},
              'build': clean, 'build_sha256': digest(clean)}
    return validate_record(record)


def validate_record(record):
    require(isinstance(record, dict) and set(record) == {'schema', 'id', 'revision', 'license', 'author', 'compatibility', 'build', 'build_sha256'}, 'Unexpected record fields')
    require(type(record['schema']) is int and record['schema'] == 1, 'Unsupported schema')
    require(str(uuid.UUID(record['id'])) == record['id'], 'Noncanonical build ID')
    number(record['revision'], minimum=1)
    require(record['license'] == 'CC0-1.0', 'Unsupported contribution license')
    text(record['author'], 128)
    require(isinstance(record['compatibility'], dict) and set(record['compatibility']) == {'realm', 'catalog'}, 'Invalid compatibility')
    require(record['compatibility']['realm'] == 'area52', 'Unsupported realm')
    require(bool(text(record['compatibility']['catalog'], 128).strip()), 'Missing catalog version')
    clean = validate_build(record['build'])
    require(canonical(clean) == canonical(record['build']), 'Build contains unnormalized or private fields')
    require(digest(clean) == record['build_sha256'], 'Build hash mismatch')
    encode(clean)
    return copy.deepcopy(record)


def read_json(path):
    def pairs(rows):
        value = {}
        for key, item in rows:
            require(key not in value, 'Duplicate JSON key')
            value[key] = item
        return value
    raw = Path(path).read_bytes()
    require(len(raw) <= 200000, 'Record too large')
    return json.loads(raw.decode('utf-8'), object_pairs_hook=pairs)


def store(root, record):
    from layout import migrate, build_path
    migrate(root, record)
    return Path(root) / build_path(record)


def index(root):
    from layout import scan, entry, build_path
    rows = scan(root)
    records, seen = [], set()
    for path, record in rows:
        require(path == build_path(record), 'Legacy layout: run migrate before indexing')
        require(record['id'] not in seen, 'Duplicate current build identity')
        seen.add(record['id'])
        records.append(entry(record, (Path(root) / path).read_bytes()))
    return {'schema': 2, 'builds': sorted(records, key=lambda r: r['id'])}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    export = commands.add_parser('export', help='Convert a build code into a local public-library record; never uploads')
    export.add_argument('code', type=Path)
    export.add_argument('--root', type=Path, required=True)
    export.add_argument('--author', required=True)
    export.add_argument('--catalog', required=True)
    export.add_argument('--id')
    export.add_argument('--revision', type=int, default=1)
    export.add_argument('--accept-cc0', action='store_true', required=True)
    load = commands.add_parser('import', help='Create a code for the existing in-game import confirmation')
    load.add_argument('record', type=Path)
    load.add_argument('--catalog', required=True)
    load.add_argument('--output', type=Path, required=True)
    check = commands.add_parser('validate')
    check.add_argument('--root', type=Path, required=True)
    listing = commands.add_parser('index')
    listing.add_argument('--root', type=Path, required=True)
    listing.add_argument('--output', type=Path, required=True)
    migration = commands.add_parser('migrate', help='Keep current versions; preserve history in Git')
    migration.add_argument('--root', type=Path, required=True)
    args = parser.parse_args()
    if args.command == 'export':
        require(args.code.stat().st_size <= MAX_CODE, 'Code file too large')
        record = make_record(decode(args.code.read_text(encoding='utf-8')), args.author, args.catalog, args.id, args.revision)
        print(store(args.root, record))
    elif args.command == 'import':
        record = validate_record(read_json(args.record))
        require(record['compatibility']['catalog'] == args.catalog, 'Catalog mismatch; review selections before import')
        with args.output.open('x', encoding='utf-8') as output:
            output.write(encode(record['build']) + '\n')
        print('Build code prepared; importing does not activate the build or grant ownership.')
    elif args.command == 'migrate':
        from layout import migrate
        result = migrate(args.root)
        print(str(len(result['builds'])) + ' current builds migrated')
    else:
        result = index(args.root)
        if args.command == 'index':
            with args.output.open('xb') as output:
                output.write(canonical(result))
        print(str(len(result['builds'])) + ' current builds validated')


if __name__ == '__main__':
    main()
