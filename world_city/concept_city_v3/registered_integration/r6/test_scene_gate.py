import unittest
from .build_scene import build
class SceneGate(unittest.TestCase):
 def test_unaccepted_binding_rejected(self):
  with self.assertRaisesRegex(ValueError,'not accepted'):build({})
 def test_unknown_base_rejected(self):
  with self.assertRaisesRegex(ValueError,'Unknown base'):build(dict(status='sources_reviewed_ready_for_visual',base_scene={'sha256':'other'}))
if __name__=='__main__':unittest.main(verbosity=2)
