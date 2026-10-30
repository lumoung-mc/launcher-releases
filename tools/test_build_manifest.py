import tempfile, unittest, json, hashlib
from pathlib import Path
import build_manifest as builder

class ManifestTests(unittest.TestCase):
    def test_immutable_releases(self):
        with tempfile.TemporaryDirectory() as temporary:
            builder.ROOT = Path(temporary)
            builder.GAME = builder.ROOT / 'games/cleancity'
            builder.SOURCE = builder.GAME / 'minecraft'
            (builder.SOURCE / 'mods').mkdir(parents=True)
            payload = builder.SOURCE / 'mods/example.jar'
            payload.write_bytes(b'first release')
            details = {'games': [{'id': 'cleancity', 'version': '1.0.0'}]}
            details_path = builder.ROOT / 'details.json'
            details_path.write_text(json.dumps(details), encoding='utf-8')
            builder.main()
            first_path = builder.GAME / 'versions/1.0.0/manifest.json'
            first_bytes = first_path.read_bytes()
            first = json.loads(first_bytes)
            entry = first['files'][0]
            self.assertIn('/files/' + entry['sha256'] + '/', entry['url'])
            self.assertTrue(json.loads(details_path.read_text())['games'][0]['manifest_url'].endswith('/versions/1.0.0/manifest.json'))
            builder.main()  # Identical regeneration is allowed.
            payload.write_bytes(b'second release')
            with self.assertRaisesRegex(ValueError, 'Increment'):
                builder.main()
            self.assertEqual(first_path.read_bytes(), first_bytes)
            details['games'][0]['version'] = '1.0.1'
            details_path.write_text(json.dumps(details), encoding='utf-8')
            builder.main()
            self.assertEqual(first_path.read_bytes(), first_bytes)
            original = builder.GAME / 'files' / entry['sha256'] / 'example.jar'
            self.assertEqual(hashlib.sha256(original.read_bytes()).hexdigest(), entry['sha256'])
            self.assertEqual(original.read_bytes(), b'first release')

if __name__ == '__main__':
    unittest.main()
