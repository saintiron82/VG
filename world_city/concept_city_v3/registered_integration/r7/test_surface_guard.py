import unittest
from . import surface_guard as g

UP = [[0.,0.,0.],[0.,0.,1.],[1.,0.,0.]]

class SurfaceGuardTests(unittest.TestCase):
    def test_upward(self):
        self.assertEqual(g.audit_vertices(UP,'top')['upward'],1)
    def test_downward_rejected(self):
        with self.assertRaisesRegex(ValueError,'Downward'):
            g.audit_vertices([UP[0],UP[2],UP[1]],'bad')
    def test_vertical_retaining_face_allowed(self):
        self.assertEqual(g.audit_vertices([[0,0,0],[0,1,0],[1,0,0]],'wall')['vertical_or_tiny_projection'],1)
    def test_nonfinite_rejected(self):
        with self.assertRaisesRegex(ValueError,'Nonfinite'):
            g.audit_vertices([[0,0,0],[0,float('nan'),1],[1,0,0]],'nan')
    def test_non_xyz_rejected(self):
        with self.assertRaisesRegex(ValueError,'malformed'):
            g.audit_vertices([[0,0],[0,0,1],[1,0,0]],'shape')
    def test_partial_triangle_rejected(self):
        with self.assertRaisesRegex(ValueError,'Non-triangular'):
            g.audit_vertices(UP[:2],'short')
    def test_replacement_and_append_checked(self):
        p={'surface_edits':[{'material':'road','triangle_index':4,'replacement_triangles_xyz_m':[UP]}],
           'appended_surfaces':{'stone':UP}}
        self.assertEqual(g.audit_patch(p)['triangles'],2)
        p['surface_edits'][0]['replacement_triangles_xyz_m']=[[UP[0],UP[2],UP[1]]]
        with self.assertRaisesRegex(ValueError,'replacement:4'):
            g.audit_patch(p)
    def test_no_input_mutation(self):
        import copy
        s={'surfaces':{'stone':copy.deepcopy(UP)}};before=copy.deepcopy(s)
        g.audit_scene(s)
        self.assertEqual(s,before)

if __name__=='__main__':unittest.main()
