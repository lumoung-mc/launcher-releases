import json, subprocess, tempfile, unittest
from pathlib import Path
from unittest.mock import patch
import build_manifest as builder

class ManifestTests(unittest.TestCase):
    def test_loader_choices(self):
        for loader_type, version in [('fabric', '0.19.5'), ('quilt', '0.28.1-beta.1')]:
            with self.subTest(loader=loader_type):
                self.assertEqual(
                    builder.loader_settings({'loader_type': loader_type, 'loader_version': version}, '1.21.1'),
                    ({'type': loader_type, 'version': version}, None),
                )
        self.assertEqual(builder.loader_settings({}, '26.2'), ({'type': 'fabric', 'version': '0.19.5'}, None))
        self.assertEqual(builder.loader_settings({'loader_type': 'vanilla'}, '1.21.1'), ({'type': 'vanilla'}, None))
        for version in ('47.4.0', '1.20.1-47.4.0'):
            loader, url = builder.loader_settings({'loader_type': 'forge', 'loader_version': version}, '1.20.1')
            self.assertEqual(loader, {'type': 'forge', 'version': '1.20.1-47.4.0'})
            self.assertEqual(url, 'https://maven.minecraftforge.net/net/minecraftforge/forge/1.20.1-47.4.0/forge-1.20.1-47.4.0-installer.jar')
        with self.assertRaisesRegex(ValueError, 'full version'):
            builder.loader_settings({'loader_type': 'forge', 'loader_version': '1.20.2-48.0.0'}, '1.20.1')
        with self.assertRaisesRegex(ValueError, 'loader_version'):
            builder.loader_settings({'loader_type': 'quilt'}, '1.21.1')

    def test_committed_snapshots_without_payload_copies(self):
        with tempfile.TemporaryDirectory() as temporary:
            builder.ROOT = Path(temporary)
            builder.GAME = builder.ROOT / 'games/cleancity'
            builder.SOURCE = builder.GAME / 'minecraft'
            def git(*args):
                return subprocess.check_output(['git', *args], cwd=builder.ROOT, stderr=subprocess.DEVNULL).decode().strip()
            git('init');git('config','user.name','Test');git('config','user.email','test@example.com')
            git('config','core.autocrlf','false')
            (builder.SOURCE / 'mods').mkdir(parents=True)
            payload=builder.SOURCE/'mods/example.jar';payload.write_bytes(b'first')
            details={'games':[{'id':'cleancity','version':'1.0.0'}]}
            path=builder.ROOT/'details.json';path.write_text(json.dumps(details),encoding='utf-8')
            git('add','.');git('commit','-m','Payload')
            revision=git('rev-parse','HEAD')
            builder.main()
            manifest=json.loads((builder.GAME/'manifest.json').read_text())
            self.assertIn('/'+revision+'/',manifest['files'][0]['url'])
            with self.assertRaises(subprocess.CalledProcessError): builder.main(True)
            git('add','.');git('commit','-m','Manifest')
            manifest_revision=git('rev-parse','HEAD')
            builder.main(True)
            self.assertIn('/'+manifest_revision+'/',json.loads(path.read_text())['games'][0]['manifest_url'])
            self.assertFalse((builder.GAME/'versions').exists())
            self.assertFalse((builder.GAME/'files').exists())
            details['games'][0].update(minecraft_version='1.21.1', java_major_version=21,
                                       loader_type='neoforge', loader_version='21.1.172')
            path.write_text(json.dumps(details), encoding='utf-8')
            with self.assertRaisesRegex(ValueError, 'Regenerate manifest'):
                builder.main(True)
            checksum = 'a' * 40
            with patch.object(builder, 'installer_checksum', return_value=checksum) as fetch:
                builder.main()
            url = 'https://maven.neoforged.net/releases/net/neoforged/neoforge/21.1.172/neoforge-21.1.172-installer.jar'
            fetch.assert_called_once_with(url)
            manifest = json.loads((builder.GAME/'manifest.json').read_text())
            self.assertEqual(manifest['loader'], {
                'type': 'neoforge', 'version': '21.1.172', 'installer': {'url': url, 'sha1': checksum},
            })
            git('add', 'games/cleancity/manifest.json')
            git('commit', '-m', 'NeoForge manifest')
            with patch.object(builder, 'installer_checksum', side_effect=AssertionError('pin must be offline')):
                builder.main(True)
            payload.write_bytes(b'not committed')
            with self.assertRaisesRegex(ValueError,'Commit payload'): builder.main()
            details['games'][0]['loader_type'] = 'vanilla'
            del details['games'][0]['loader_version']
            path.write_text(json.dumps(details), encoding='utf-8')
            payload.unlink()
            builder.main()
            manifest = json.loads((builder.GAME/'manifest.json').read_text())
            self.assertEqual(manifest['loader'], {'type': 'vanilla'})
            self.assertEqual(manifest['files'], [])

if __name__ == '__main__': unittest.main()
