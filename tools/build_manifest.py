"""Build a game manifest using committed payloads, then pin its committed URL.

Commit minecraft/ changes first. Run this script, commit manifest.json, and run
again with --pin-manifest before committing details.json and pushing.
"""
import argparse
import hashlib
import json
import subprocess
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parents[1]
GAME = ROOT / 'games' / 'cleancity'
SOURCE = GAME / 'minecraft'
RAW_ROOT = 'https://raw.githubusercontent.com/lumoung-mc/launcher-releases'


def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT).decode().strip()


def main(pin_manifest=False):
    details_path = ROOT / 'details.json'
    details = json.loads(details_path.read_text(encoding='utf-8-sig'))
    game = next(game for game in details['games'] if game['id'] == 'cleancity')
    if pin_manifest:
        # Publish the exact manifest that is already in history; do not re-render it.
        revision = git('rev-parse', 'HEAD')
        relative = (GAME / 'manifest.json').relative_to(ROOT).as_posix()
        committed = subprocess.check_output(['git', 'show', f'{revision}:{relative}'], cwd=ROOT)
        if committed.decode('utf-8').replace('\r\n', '\n') != (GAME / 'manifest.json').read_text(encoding='utf-8'):
            raise ValueError('Commit manifest.json before pinning it.')
        manifest = json.loads(committed)
        if manifest['version'] != game['version'] or manifest['game_id'] != game['id']:
            raise ValueError('Catalog and committed manifest do not match.')
        game['manifest_url'] = f'{RAW_ROOT}/{revision}/{relative}'
        details_path.write_text(json.dumps(details, ensure_ascii=False, indent=4) + '\n', encoding='utf-8')
        print(f'Pinned manifest: {revision}')
        return
    revision = git('log', '-1', '--format=%H', '--', SOURCE.relative_to(ROOT).as_posix())
    if not revision:
        raise ValueError('Commit minecraft/ files before building the manifest.')
    files = []
    for source in sorted(SOURCE.rglob('*')):
        if not source.is_file():
            continue
        relative = source.relative_to(SOURCE).as_posix()
        if relative != 'options.txt' and not relative.startswith(('mods/', 'config/', 'resourcepacks/')):
            raise ValueError(f'Review this file before distributing it: {relative}')
        repository_path = source.relative_to(ROOT).as_posix()
        # A mutable work file must never be described as an older committed payload.
        if git('rev-parse', f'{revision}:{repository_path}') != git('hash-object', '--path=' + repository_path, str(source)):
            raise ValueError(f'Commit payload changes first: {relative}')
        committed = subprocess.check_output(['git', 'show', f'{revision}:{repository_path}'], cwd=ROOT)
        digest = hashlib.sha256(committed).hexdigest()
        files.append({
            'path': relative,
            'url': f'{RAW_ROOT}/{revision}/{quote(repository_path, safe="/")}',
            'size': len(committed),
            'sha256': digest,
            'mode': 'install_if_missing' if relative == 'options.txt' or relative.startswith('config/') else 'managed',
        })
    if not files:
        raise ValueError('minecraft/ contains no game files')
    manifest = {
        'schema_version': 1, 'game_id': game['id'], 'version': game['version'],
        'minecraft_version': '26.2', 'java_major_version': 25,
        'loader': {'type': 'fabric', 'version': '0.19.5'}, 'files': files,
    }
    (GAME / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=4) + '\n', encoding='utf-8')
    print(f'Generated manifest: {len(files)} files; commit it, then run with --pin-manifest.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--pin-manifest', action='store_true')
    main(parser.parse_args().pin_manifest)
