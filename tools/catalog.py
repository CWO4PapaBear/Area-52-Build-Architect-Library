"""Render public build descriptions and copyable codes without executable content."""
import argparse
import html
from pathlib import Path
import re

from library import encode, index, read_json, validate_record


def literal(value):
    value = ''.join(c for c in value if c >= ' ' or c in '\n\t')
    return re.sub(r'([\\`*_{}\[\]()#+.!|>~-])', r'\\\1', html.escape(value, quote=True)).replace('\n', ' ')


def block(value):
    runs = [len(run) for run in re.findall(r'`+', value)]
    fence = '`' * max(3, max(runs, default=0) + 1)
    return fence + 'text\n' + value + '\n' + fence + '\n'


def page(record):
    record = validate_record(record)
    b = record['build']
    lines = ['# ' + literal(b['Name']), '',
             'Author: ' + literal(record['author']), '',
             'Revision: ' + str(record['revision']), '',
             'Catalog: ' + literal(record['compatibility']['catalog']), '',
             'License: CC0-1.0', '',
             'Category: ' + literal(b['Category']), '',
             'Role: ' + literal(b['Roles']) + ' · Primary stat: ' + literal(b['PrimaryStat']), '',
             '## Description', '', block(b['Description']),
             '## Abilities and talents', '', '| Spell ID | Learn at level | Roles | Comment |', '|---|---|---|---|']
    for spell in b['Spells']:
        roles = ', '.join(key[2:] for key in ('IsCoreAbility','IsOptimalAbility','IsEmpoweringAbility','IsSynergisticAbility') if spell[key])
        lines.append('| ' + str(spell['Spell']) + ' | ' + str(spell['Level']) + ' | ' + literal(roles) + ' | ' + literal(spell['Comment']) + ' |')
    lines += ['', '## Mystic Enchants', '', '| Spell ID | Copies | Learn at level | Comment |', '|---|---|---|---|']
    for enchant in b['RandomEnchants']:
        lines.append('| ' + str(enchant['Enchant']) + ' | ' + str(enchant['Stacks']) + ' | ' + str(enchant['Level']) + ' | ' + literal(enchant['Comment']) + ' |')
    lines += ['', '## Equipment preferences', '']
    for key in ('WeaponTypes','ArmorTypes'):
        for row in b[key]:
            lines.append('- ' + literal(row['Type']) + ': ' + literal(row['Comment']))
    lines += ['', '## Import this build', '',
              'Copy the complete code below and use **Import Build Code** in game. Importing creates an editable copy; it does not activate the build or grant abilities or enchants.', '',
              block(encode(b))]
    return '\n'.join(lines)


def overview(items):
    latest = {}
    for item in items:
        if item['id'] not in latest or item['revision'] > latest[item['id']]['revision']:
            latest[item['id']] = item
    lines = ['# Area 52 Build Library', '',
             'Browse a build, then copy its build code into **Import Build Code** in game. **Update Library** refreshes the participating server’s shared copies; personal edits and active builds are preserved.', '',
             '| Build | Author | Revision | Catalog |', '|---|---|---|---|']
    for item in sorted(latest.values(), key=lambda r: (r['name'].casefold(), r['id'])):
        link = 'catalog/' + item['id'] + '/' + str(item['revision']) + '.md'
        lines.append('| [' + literal(item['name']) + '](' + link + ') | ' + literal(item['author']) + ' | ' + str(item['revision']) + ' | ' + literal(item['compatibility']['catalog']) + ' |')
    if not latest:
        lines += ['', 'No builds have been explicitly published yet.']
    return '\n'.join(lines) + '\n'


def render(root, output):
    root, output = Path(root), Path(output)
    entries = index(root)['builds']
    for item in entries:
        record = validate_record(read_json(root / item['path']))
        target = output / 'catalog' / record['id'] / (str(record['revision']) + '.md')
        target.parent.mkdir(parents=True, exist_ok=True)
        data = page(record).encode('utf-8')
        if target.exists():
            if target.read_bytes() != data:
                raise ValueError('Existing catalog revision differs')
        else:
            with target.open('xb') as stream:
                stream.write(data)
    output.mkdir(parents=True, exist_ok=True)
    target = output / 'CATALOG.md'
    target.write_text(overview(entries), encoding='utf-8', newline='\n')
    return target


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    print(render(args.root, args.output))
