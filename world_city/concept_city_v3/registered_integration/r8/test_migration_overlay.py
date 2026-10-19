import tempfile,unittest
from pathlib import Path
from .seal_migration_overlay import eligible
class OverlayTests(unittest.TestCase):
 def test_all_new_sources_and_history_but_no_nested_backups(self):
  with tempfile.TemporaryDirectory()as td:
   root=Path(td)
   names=['new_source.py','old_test/unique.json','hidden/.runtime/owned.json','checks/preserved_test_only_bytes.zip','checkpoints/backup.zip','prior.zip','foo/.godot/cache.bin','__pycache__/cache.pyc','file.pyc']
   for n in names:p=root/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b'bytes')
   self.assertEqual({n for n,p in eligible(root)},{'new_source.py','old_test/unique.json','hidden/.runtime/owned.json','checks/preserved_test_only_bytes.zip'})
if __name__=='__main__':unittest.main()
