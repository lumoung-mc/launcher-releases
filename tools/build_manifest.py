"""Build a game manifest using committed payloads, then pin its committed URL.

Commit minecraft/ changes first. Run this script, commit manifest.json, and run
again with --pin-manifest before committing details.json and pushing.
"""
import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path
from urllib.error import URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
GAME = ROOT / 'games' / 'cleancity'
SOURCE = GAME / 'minecraft'
RAW_ROOT = 'https://raw.githubusercontent.com/lumoung-mc/launcher-releases'


def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT).decode().strip()


def loader_settings(game, minecraft):
    loader_type = game.get('loader_type', 'fabric')
    if not isinstance(loader_type, str) or loader_type not in ('fabric', 'quilt', 'forge', 'neoforge', 'vanilla'):
        raise ValueError(f'Unsupported loader_type: {loader_type!r}')
    if loader_type == 'vanilla':
        if 'loader_version' in game:
            raise ValueError('Remove loader_version when using vanilla.')
        return {'type': 'vanilla'}, None

    version = game.get('loader_version', '0.19.5' if loader_type == 'fabric' else None)
    if not isinstance(version, str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9.+_-]{0,79}', version):
        raise ValueError(f'Set a valid loader_version for {loader_type}.')

    installer_url = None
    if loader_type == 'forge':
        prefix = f'{minecraft}-'
        forge_version = version.removeprefix(prefix)
        if not re.fullmatch(r'[0-9]+(?:\.[0-9]+)+(?:-[A-Za-z][A-Za-z0-9._-]*)?', forge_version):
            raise ValueError(f'Use a Forge version or a full version starting with {prefix}.')
        version = prefix + forge_version
        if len(version) > 80:
            raise ValueError('Full Forge version is too long.')
        installer_url = f'https://maven.minecraftforge.net/net/minecraftforge/forge/{version}/forge-{version}-installer.jar'
    elif loader_type == 'neoforge':
        installer_url = f'https://maven.neoforged.net/releases/net/neoforged/neoforge/{version}/neoforge-{version}-installer.jar'
    return {'type': loader_type, 'version': version}, installer_url


def installer_checksum(url):
    request = Request(f'{url}.sha1', headers={'User-Agent': 'LumoungsLauncher-Manifest/1.0'})
    try:
        with urlopen(request, timeout=20) as response:
            checksum = response.read(256).strip().lower()
    except (URLError, TimeoutError) as error:
        raise ValueError(f'Could not download installer checksum: {request.full_url}: {error}') from error
    if not re.fullmatch(rb'[a-f0-9]{40}', checksum):
        raise ValueError(f'Invalid installer checksum: {request.full_url}')
    return checksum.decode('ascii')


def main(pin_manifest=False, game_id='cleancity'):
    details_path = ROOT / 'details.json'
    details = json.loads(details_path.read_text(encoding='utf-8-sig'))
    game = next(game for game in details['games'] if game['id'] == game_id)
    minecraft = game.get('minecraft_version', '26.2')
    if not isinstance(minecraft, str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]*', minecraft):
        raise ValueError('Set a valid minecraft_version.')
    java = game.get('java_major_version', 25)
    loader, installer_url = loader_settings(game, minecraft)
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
        committed_loader = dict(manifest['loader'])
        installer = committed_loader.pop('installer', {})
        if (manifest['minecraft_version'] != minecraft or manifest['java_major_version'] != java
                or committed_loader != loader):
            raise ValueError('Regenerate manifest.json after changing Minecraft, Java or loader settings.')
        if installer_url and (installer.get('url') != installer_url
                              or not re.fullmatch(r'[a-f0-9]{40}', installer.get('sha1', ''))):
            raise ValueError('Regenerate manifest.json to include the official loader installer and checksum.')
        game['manifest_url'] = f'{RAW_ROOT}/{revision}/{relative}'
        details_path.write_text(json.dumps(details, ensure_ascii=False, indent=4) + '\n', encoding='utf-8')
        print(f'Pinned manifest: {revision}')
        return
    sources = sorted(source for source in SOURCE.rglob('*') if source.is_file())
    if sources:
        revision = git('log', '-1', '--format=%H', '--', SOURCE.relative_to(ROOT).as_posix())
        if not revision:
            raise ValueError('Commit minecraft/ files before building the manifest.')
    elif loader['type'] != 'vanilla':
        raise ValueError('minecraft/ contains no game files')
    files = []
    for source in sources:
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
    if installer_url:
        loader['installer'] = {'url': installer_url, 'sha1': installer_checksum(installer_url)}
    manifest = {
        'schema_version': 1, 'game_id': game['id'], 'version': game['version'],
        'minecraft_version': minecraft, 'java_major_version': java,
        'loader': loader, 'files': files,
    }
    (GAME / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=4) + '\n', encoding='utf-8')
    print(f'Generated manifest: {len(files)} files; commit it, then run with --pin-manifest.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--pin-manifest', action='store_true')
    parser.add_argument('--game', default='cleancity')
    args=parser.parse_args()
    if not re.fullmatch(r'[a-z0-9_-]+',args.game): parser.error('Invalid game ID')
    GAME=ROOT/'games'/args.game
    SOURCE=GAME/'minecraft'
    main(args.pin_manifest,args.game)
