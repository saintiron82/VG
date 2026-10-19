import gzip
import json
from pathlib import Path
import tempfile
import unittest
import facility_render_bounds as b

class FacilityRenderBounds(unittest.TestCase):
    def render(self):return {'groups':[{'quads':[[[0,0,0],[0,1,0],[0,1,2],[0,0,2]]],'material':'stone'}],'bounds':{'min':[0,0,0],'max':[0,1,2]},'quad_count':1}
    def test_all_vertices_and_metadata_after_groups_gzip(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'render.json.gz';p.write_bytes(gzip.compress(json.dumps(self.render()).encode(),mtime=0));r=b.analyze(p)
            self.assertTrue(r['pass']);self.assertEqual(r['rendered_quad_count'],1);self.assertFalse(r['whole_mesh_loaded'])
    def test_declared_bounds_cannot_hide_a_vertex(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'render.json';r=self.render();r['bounds']['max'][2]=1;p.write_text(json.dumps(r));self.assertFalse(b.analyze(p)['pass'])
    def test_nonfinite_vertex_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'render.json';r=self.render();r['groups'][0]['quads'][0][0][0]=float('nan');p.write_text(json.dumps(r))
            with self.assertRaises(ValueError):b.analyze(p)
    def test_truncation_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'render.json';p.write_text(json.dumps(self.render())[:-3])
            with self.assertRaises(ValueError):b.analyze(p)
if __name__=='__main__':unittest.main()
