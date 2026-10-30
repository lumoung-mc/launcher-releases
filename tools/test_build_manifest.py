import json, subprocess, tempfile, unittest
from pathlib import Path
import build_manifest as builder

class ManifestTests(unittest.TestCase):
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
            payload.write_bytes(b'not committed')
            with self.assertRaisesRegex(ValueError,'Commit payload'): builder.main()

if __name__ == '__main__': unittest.main()
