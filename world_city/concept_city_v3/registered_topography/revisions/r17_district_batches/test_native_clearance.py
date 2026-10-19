import unittest,math,tempfile,json
from pathlib import Path
from unittest.mock import patch
from . import native_clearance as n
from . import author as a

class NativeTests(unittest.TestCase):
 def test_rigid_transform(self):
  self.assertAlmostEqual(n.transform([[2,3]],[10,99,20],math.pi/2)[0][0],13)
  self.assertAlmostEqual(n.transform([[2,3]],[10,99,20],math.pi/2)[0][1],18)
 def test_stale_native_ref_rejected(self):
  with tempfile.TemporaryDirectory(dir=a.HERE)as td:
   path=Path(td)/'source.json';path.write_text('{}')
   with self.assertRaisesRegex(ValueError,'Changed source'):
    n.require_ref(dict(path=str(path.relative_to(a.ROOT)),sha256='0'*64))
 def test_exact_native_ref_read(self):
  with tempfile.TemporaryDirectory(dir=a.HERE)as td:
   path=Path(td)/'source.json';path.write_text('{"value":7}')
   self.assertEqual(n.require_ref(dict(path=str(path.relative_to(a.ROOT)),sha256=a.sha(path))),{'value':7})
 def test_stale_scene_projection_rejected(self):
  with tempfile.TemporaryDirectory(dir=a.HERE)as td:
   path=Path(td)/'projection.json';path.write_text(json.dumps(dict(scene=dict(sha256='wrong'))))
   with patch.object(n,'PROJECTION',path),self.assertRaisesRegex(ValueError,'Stale native projection'):n.check({})
if __name__=='__main__':unittest.main()
