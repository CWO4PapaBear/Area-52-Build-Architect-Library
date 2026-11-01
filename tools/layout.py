"""Current-version paths and guarded migration of generated library files."""
import hashlib
import os
from pathlib import Path
import re
import tempfile
import unicodedata

from library import canonical, read_json, require, validate_record


def folder(name, identity):
    import uuid
    require(str(uuid.UUID(identity)) == identity, 'Invalid public identity')
    name = unicodedata.normalize('NFKD', name).encode('ascii', 'ignore').decode()
    slug = re.sub('[^A-Za-z0-9]+', '-', name).strip('-')[:64].rstrip('-') or 'Build'
    return slug + '--' + identity


def build_path(record):
    return 'builds/' + folder(record['build']['Name'], record['id']) + '/current.json'


def catalog_path(item):
    return 'catalog/' + folder(item['name'], item['id']) + '/README.md'


def entry(record, body=None):
    return {'id': record['id'], 'revision': record['revision'], 'name': record['build']['Name'],
            'author': record['author'], 'compatibility': record['compatibility'],
            'path': build_path(record), 'sha256': hashlib.sha256(body or canonical(record)).hexdigest()}


def check_index(value):
    require(isinstance(value, dict) and set(value) == {'schema', 'builds'} and
            type(value['schema']) is int and value['schema'] in (1, 2), 'Unsupported index')
    require(isinstance(value['builds'], list) and len(value['builds']) <= 10000, 'Invalid index size')
    seen = set()
    for item in value['builds']:
        require(isinstance(item, dict) and set(item) ==
                {'id', 'revision', 'name', 'author', 'compatibility', 'path', 'sha256'}, 'Invalid index entry')
        require(type(item['revision']) is int and item['revision'] > 0, 'Invalid indexed revision')
        directory = folder(item['name'], item['id'])
        expected = ('builds/' + directory + '/current.json' if value['schema'] == 2
                    else 'builds/' + item['id'] + '/' + str(item['revision']) + '.json')
        require(item['path'] == expected, 'Invalid library path')
        require(isinstance(item['sha256'], str) and re.fullmatch('[0-9a-f]{64}', item['sha256']), 'Invalid digest')
        key = item['id'] if value['schema'] == 2 else item['path']
        require(key not in seen, 'Duplicate library identity or revision')
        seen.add(key)
    return value


def check_entry(item, body):
    require(body is not None and len(body) <= 200000, 'Missing or oversized library record')
    import json
    record = validate_record(json.loads(body))
    expected = entry(record, body)
    expected['path'] = item['path']
    require(item == expected, 'Index metadata or hash mismatch')
    return record


def safe_path(root, relative):
    root = Path(root).absolute()
    target = root / relative
    require(target.resolve().is_relative_to(root.resolve()), 'Path escapes library')
    for part in (target, *target.parents):
        require(not part.is_symlink(), 'Symlinks are not supported in library output')
        if part == root:
            break
    return target


def scan(root):
    root = Path(root)
    rows = []
    for path in sorted((root / 'builds').glob('*/*.json')):
        relative = path.relative_to(root).as_posix()
        safe_path(root, relative)
        record = validate_record(read_json(path))
        legacy = 'builds/' + record['id'] + '/' + str(record['revision']) + '.json'
        require(relative in (legacy, build_path(record)), 'Record path mismatch')
        rows.append((relative, record))
    return rows


def latest(rows):
    result = {}
    for _, record in rows:
        old = result.get(record['id'])
        if old and old['revision'] == record['revision']:
            require(old == record, 'Conflicting copies of public revision')
        if not old or record['revision'] > old['revision']:
            result[record['id']] = record
    return result


def write_files(root, files):
    targets = {name: safe_path(root, name) for name in files}
    for name, body in files.items():
        path = targets[name]
        if body is None:
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(body)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    for name, body in files.items():
        path = targets[name]
        if body is None and path.exists():
            path.unlink()
            if not any(path.parent.iterdir()):
                path.parent.rmdir()


def migrate(root, replacement=None):
    from catalog import page, overview
    rows = scan(root)
    saved_index = safe_path(root, 'index.json')
    if saved_index.exists():
        previous = check_index(read_json(saved_index))
        for item in previous['builds']:
            target = safe_path(root, item['path'])
            require(target.is_file(), 'Indexed build is missing')
            check_entry(item, target.read_bytes())
    records = latest(rows)
    if replacement is not None:
        replacement = validate_record(replacement)
        old = records.get(replacement['id'])
        if old:
            require(replacement['revision'] >= old['revision'], 'Cannot restore a stale revision')
            require(replacement['revision'] != old['revision'] or replacement == old,
                    'Revision already exists with different content')
        records[replacement['id']] = replacement
    files = {}
    recognized_pages = set()
    for path, record in rows:
        files[path] = None
        old_page = ('catalog/' + record['id'] + '/' + str(record['revision']) + '.md'
                    if path != build_path(record) else catalog_path(entry(record)))
        target = safe_path(root, old_page)
        recognized_pages.add(old_page)
        if target.exists():
            require(target.read_bytes() == page(record).encode('utf-8'), 'Existing catalog page differs')
            files[old_page] = None
    for target in (Path(root) / 'catalog').glob('*/*.md'):
        require(target.relative_to(root).as_posix() in recognized_pages,
                'Unrecognized catalog page; reconcile before migration')
    items = [entry(record) for record in sorted(records.values(), key=lambda r: r['id'])]
    for record in records.values():
        files[build_path(record)] = canonical(record)
        files[catalog_path(entry(record))] = page(record).encode('utf-8')
    files['index.json'] = canonical({'schema': 2, 'builds': items})
    files['CATALOG.md'] = overview(items).encode('utf-8')
    allowed_existing = {p for p, _ in rows} | recognized_pages
    for path, body in files.items():
        target = safe_path(root, path)
        if body is not None and path not in {'index.json', 'CATALOG.md'} and target.exists():
            require(path in allowed_existing or target.read_bytes() == body,
                    'Destination has unrelated content')
    write_files(root, files)
    return {'schema': 2, 'builds': items}
