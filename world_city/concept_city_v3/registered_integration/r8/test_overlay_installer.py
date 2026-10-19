"""Guarded overlay tests using small isolated ZIPs; never touch installed project."""
import contextlib
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[4]
spec = importlib.util.spec_from_file_location('vg_overlay_installer', ROOT / 'Apply-VG-Overlay.py')
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
sha = lambda data: hashlib.sha256(data).hexdigest()


class OverlayInstallerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name); self.target = self.home / 'installed'
        self.base_files = {'unchanged.py': b'original unchanged\n', 'changed.txt': b'prior\n',
                           'geometry/ROAD:OLD.json': b'old colon geometry\n'}
        self.base = self.home / 'base.zip'
        self.base_raw = m.encoded({'schema': 'riverstone.integrated_r8.checkpoint.v1',
                                   'files': {n: sha(v) for n, v in self.base_files.items()}})
        with zipfile.ZipFile(self.base, 'w') as archive:
            for name, value in self.base_files.items(): archive.writestr(name, value)
            archive.writestr(m.BASE_MANIFEST, self.base_raw)
        self.base_sha = m.digest(self.base)
        with contextlib.redirect_stdout(io.StringIO()):
            m.X.extract(self.base, self.target, self.base_sha)
        self.starter = self.target / 'starter-project'; self.starter.mkdir()
        (self.starter / 'keep.txt').write_bytes(b'local starter, never replace\n')
        self.payload = {'changed.txt': b'new target\n', 'new.py': b'new source\n',
                        'geometry/ROAD:NEW.json': b'new colon geometry\n'}
        self.overlay = self.home / 'overlay.zip'
        self.make_overlay()

    def make_overlay(self, setup=None):
        changes = {name: {'sha256': sha(data), 'bytes': len(data),
                          'prior_sha256': sha(self.base_files[name]) if name in self.base_files else None,
                          'kind': 'changed' if name in self.base_files else 'added'} for name, data in self.payload.items()}
        if setup:
            for name, row in changes.items():
                row['accepted_prior_sha256'] = [v for v in (row['prior_sha256'], setup.get(name)) if v]
        overlay = {'schema': 'riverstone.full_migration.overlay.v1', 'requires_complete_base': True,
                   'base_archive_sha256': self.base_sha, 'changes': changes,
                   'compatible_setup_overlay': {'sha256': 'a' * 64, 'payload_hashes': setup} if setup else None}
        overlay_raw = m.encoded(overlay)
        wrapper = {'schema': 'riverstone.integrated_r8.checkpoint.v1', 'requires_external_baseline': True,
                   'base_archive_sha256': self.base_sha,
                   'files': {**{n: sha(v) for n, v in self.payload.items()}, m.OVERLAY_MANIFEST: sha(overlay_raw)}}
        with zipfile.ZipFile(self.overlay, 'w') as archive:
            for name, data in self.payload.items(): archive.writestr(name, data)
            archive.writestr(m.OVERLAY_MANIFEST, overlay_raw)
            archive.writestr(m.BASE_MANIFEST, m.encoded(wrapper))
        self.overlay_sha = m.digest(self.overlay)

    def apply(self):
        return m.apply_overlay(self.overlay, self.overlay_sha, self.base, self.base_sha, self.target)

    def snapshot(self):
        return {p.relative_to(self.target).as_posix(): p.read_bytes() for p in self.target.rglob('*') if p.is_file()}

    def test_exact_apply_and_superseded_bytes_backup(self):
        result = self.apply()
        self.assertEqual(result['status'], 'APPLIED')
        self.assertEqual(result['changed_files_applied'], 3)
        for name, data in self.payload.items():
            self.assertEqual((self.target / m.X.windows_path(name)).read_bytes(), data)
        history = self.target / m.HISTORY / self.overlay_sha
        backup = history / 'backups' / sha(self.base_files['changed.txt']) / 'changed.txt'
        self.assertEqual(backup.read_bytes(), self.base_files['changed.txt'])
        self.assertEqual((self.target / m.BASE_MANIFEST).read_bytes(), self.base_raw)
        self.assertTrue((history / 'VG_OVERLAY_MANIFEST.json').is_file())
        self.assertTrue((history / 'INTEGRATED_OVERLAY_MANIFEST.json').is_file())
        self.assertTrue((history / 'receipt.json').is_file())

    def test_wrong_prior_hash_rejected_before_any_mutation(self):
        (self.target / 'changed.txt').write_bytes(b'user edit')
        before = self.snapshot()
        with self.assertRaisesRegex(ValueError, 'prior/new-file conflict'):
            self.apply()
        self.assertEqual(self.snapshot(), before)
        self.assertFalse((self.target / m.HISTORY).exists())

    def test_new_file_conflict_rejected_before_any_mutation(self):
        (self.target / 'new.py').write_bytes(b'unrelated existing source')
        before = self.snapshot()
        with self.assertRaisesRegex(ValueError, 'prior/new-file conflict'):
            self.apply()
        self.assertEqual(self.snapshot(), before)

    def test_unchanged_baseline_must_match(self):
        (self.target / 'unchanged.py').write_bytes(b'changed behind installer')
        before = self.snapshot()
        with self.assertRaisesRegex(ValueError, 'Unchanged baseline bytes differ'):
            self.apply()
        self.assertEqual(self.snapshot(), before)

    def test_missing_baseline_must_not_be_silently_repaired(self):
        (self.target / 'unchanged.py').unlink()
        before = self.snapshot()
        with self.assertRaisesRegex(ValueError, 'Missing complete-baseline file'):
            self.apply()
        self.assertEqual(self.snapshot(), before)

    def test_path_map_is_merged_and_unknown_fields_preserved(self):
        path = self.target / m.MAP_NAME; old = json.loads(path.read_bytes())
        old['custom_note'] = 'retained extraction note'
        old['renamed_paths']['earlier/A:B.txt'] = 'earlier/A%3AB.txt'
        old['renamed_count'] += 1; path.write_bytes(m.encoded(old))
        self.apply(); new = json.loads(path.read_bytes())
        self.assertEqual(new['archive_sha256'], self.base_sha)
        self.assertEqual(new['custom_note'], old['custom_note'])
        self.assertEqual(new['renamed_paths']['geometry/ROAD:OLD.json'], 'geometry/ROAD%3AOLD.json')
        self.assertEqual(new['renamed_paths']['geometry/ROAD:NEW.json'], 'geometry/ROAD%3ANEW.json')
        self.assertEqual(new['renamed_paths']['earlier/A:B.txt'], 'earlier/A%3AB.txt')
        self.assertEqual(new['applied_overlay_sha256'], [self.overlay_sha])

    def test_repeat_apply_is_byte_idempotent(self):
        self.apply(); before = self.snapshot()
        result = self.apply()
        self.assertEqual(result['status'], 'ALREADY_APPLIED')
        self.assertEqual(self.snapshot(), before)

    def test_starter_and_unrelated_files_retained(self):
        unrelated = self.target / 'notes.txt'; unrelated.write_bytes(b'local unrelated notes')
        self.apply()
        self.assertEqual((self.starter / 'keep.txt').read_bytes(), b'local starter, never replace\n')
        self.assertEqual(unrelated.read_bytes(), b'local unrelated notes')

    def test_declared_setup_prior_is_accepted_and_backed_up(self):
        setup_bytes = b'intentional interim setup\n'
        (self.target / 'changed.txt').write_bytes(setup_bytes)
        self.make_overlay({'changed.txt': sha(setup_bytes)})
        self.apply()
        backup = self.target / m.HISTORY / self.overlay_sha / 'backups' / sha(setup_bytes) / 'changed.txt'
        self.assertEqual(backup.read_bytes(), setup_bytes)

    def test_wrong_zip_hash_rejected_before_mutation(self):
        before = self.snapshot()
        with self.assertRaisesRegex(ValueError, 'ZIP SHA-256 mismatch'):
            m.apply_overlay(self.overlay, '0' * 64, self.base, self.base_sha, self.target)
        self.assertEqual(self.snapshot(), before)

    def test_case_fold_conflict_rejected(self):
        (self.target / 'New.py').write_bytes(b'local file with another case')
        before = self.snapshot()
        with self.assertRaisesRegex(ValueError, 'case-fold'):
            self.apply()
        self.assertEqual(self.snapshot(), before)

    def test_archive_directory_case_fold_conflict_rejected(self):
        self.payload.update({'NEW/a.txt': b'a', 'new/b.txt': b'b'}); self.make_overlay()
        before = self.snapshot()
        with self.assertRaisesRegex(ValueError, 'case-fold'):
            self.apply()
        self.assertEqual(self.snapshot(), before)

    def test_installed_symlink_rejected(self):
        link = self.target / 'link'
        try: link.symlink_to(self.home, target_is_directory=True)
        except OSError: self.skipTest('symlink not permitted')
        with self.assertRaisesRegex(ValueError, 'symlink|Symlink'):
            self.apply()
        self.assertFalse((self.target / m.HISTORY).exists())

    def test_partial_apply_can_resume_safely(self):
        replace = m.os.replace; calls = []
        def fail_second(source, destination):
            calls.append(str(destination))
            if len(calls) == 2: raise OSError('simulated interruption')
            return replace(source, destination)
        with patch.object(m.os, 'replace', side_effect=fail_second):
            with self.assertRaisesRegex(OSError, 'simulated interruption'):
                self.apply()
        result = self.apply()
        self.assertEqual(result['status'], 'APPLIED')
        self.assertEqual(result['already_target_files'], 1)
        for name, value in self.payload.items():
            self.assertEqual((self.target / m.X.windows_path(name)).read_bytes(), value)

    def test_original_base_manifest_is_required(self):
        (self.target / m.BASE_MANIFEST).write_bytes(b'wrong old wrapper')
        before = self.snapshot()
        with self.assertRaisesRegex(ValueError, 'base manifest'):
            self.apply()
        self.assertEqual(self.snapshot(), before)

    def test_unsafe_archive_path_is_rejected(self):
        self.payload['../escape.txt'] = b'no'; self.make_overlay()
        before = self.snapshot()
        with self.assertRaisesRegex(ValueError, 'unsafe path'):
            self.apply()
        self.assertEqual(self.snapshot(), before)


if __name__ == '__main__':
    unittest.main(verbosity=2)
