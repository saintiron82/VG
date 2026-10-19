"""Focused executable regression and negative-control checks for this native pack."""
import json
import math
from pathlib import Path
import sys
import unittest
sys.dont_write_bytecode = True
import author as a


class GatePackTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pack=json.loads((a.HERE/'pack.json').read_text())
        cls.audit=json.loads((a.HERE/'audit.json').read_text())
        cls.frames=json.loads((a.HERE/'route_frame.json').read_text())['gates']
        cls.added={v['id']:v for v in cls.pack['add_instances']}
        cls.kept=[v for v in a.S['common_instances'] if v['id'] not in set(cls.pack['remove_instance_ids'])]

    def test_source_and_pack_binding(self):
        self.assertEqual(self.pack['schema'],'riverstone.city.visual_addendum.v1')
        self.assertEqual(self.pack['base_scene_sha256'],a.BASE_SHA)
        self.assertEqual(self.audit['pack']['sha256'],a.sha(a.HERE/'pack.json'))
        self.assertEqual(self.audit['route_frame']['sha256'],a.sha(a.HERE/'route_frame.json'))
        for key in (a.HEADER,a.TOWER,a.FOOTING):
            a.compiled(key)  # Verifies master/render hashes, materials, and exact compiled payload.

    def test_exact_removals_and_native_scale(self):
        expected=['FORT_CURTAIN_12_0_05','FORT_CURTAIN_12_0_05:FOOTING:0','FORT_CURTAIN_12_0_05:FOOTING:1','FORT_CURTAIN_26_0_00','FORT_CURTAIN_26_0_00:FOOTING:0','FORT_CURTAIN_26_0_00:FOOTING:1','FORT_CURTAIN_26_0_00:FOOTING:2']
        self.assertEqual(self.pack['remove_instance_ids'],expected)
        self.assertEqual(len(self.added),10)
        self.assertEqual(self.pack['common_assets'],{})
        self.assertTrue(all(v['scale']==[1,1,1] and v['palette_override']=={} for v in self.added.values()))
        self.assertTrue(set(self.added).isdisjoint(a.I))

    def test_requested_frames_and_footings(self):
        for side,floor in [('east',4.0),('west',21.0)]:
            f=self.frames[side]; old=a.I[f['removed_wall_id']]; h=self.added[f['header_id']]
            self.assertEqual(h['position_m'],[old['position_m'][0],floor,old['position_m'][2]])
            self.assertEqual(h['yaw_rad'],old['yaw_rad'])
            for tid,dx in zip(f['tower_ids'],[-9.5,9.5]):
                tower=self.added[tid]; footing=self.added[tid+':FOOTING']
                self.assertEqual(tower['position_m'],a.world([dx,0,0],h))
                self.assertEqual(footing['position_m'],tower['position_m'])
                self.assertEqual(footing['asset_key'],a.FOOTING)
            for name in ('tangent_m','inward_normal_m'):
                self.assertAlmostEqual(sum(x*x for x in f[name]),1.0)
            self.assertAlmostEqual(sum(x*y for x,y in zip(f['tangent_m'],f['inward_normal_m'])),0.0)
            self.assertEqual(f['inward_normal_m'],[math.sin(h['yaw_rad']),0,math.cos(h['yaw_rad'])])

    def test_whole_native_composition_crossing_is_clear(self):
        for side,f in self.frames.items():
            h=self.added[f['header_id']]
            for bounds in [((-4,0,-3),(4,4.5,3)),((-4,0,-6),(4,4.5,6))]:
                proof=a.prism_hits(self.kept+list(self.added.values()),h,*bounds)
                self.assertTrue(proof['clear'],(side,proof))

    def test_negative_control_decorative_gate_against_retained_wall_fails(self):
        for side,f in self.frames.items():
            h=self.added[f['header_id']]
            proof=a.prism_hits(a.S['common_instances']+list(self.added.values()),h)
            self.assertFalse(proof['clear'])
            self.assertIn(f['removed_wall_id'],[v['id'] for v in proof['occupied_native_intersections']])

    def test_header_tower_shared_faces_are_real_occupied_cells(self):
        header={tuple(r[:3]) for r in a.compiled(a.HEADER)['cells']}
        tower={tuple(r[:3]) for r in a.compiled(a.TOWER)['cells']}
        for hx,tx in [(-9,9),(8,-10)]:
            for y in range(9):
                for z in range(-6,6):
                    self.assertIn((hx,y,z),header)
                    self.assertIn((tx,y,z),tower)
        self.assertEqual(9*12*.5*.5,27.0)

    def test_every_tower_adjacent_wall_join_is_exactly_closed(self):
        for side,f in self.frames.items():
            h=self.added[f['header_id']]
            for oldproof in self.audit['gates'][side]['adjacent_wall_joins']:
                proof=a.join_proof(self.added[oldproof['tower_id']],[a.I[k] for k in oldproof['adjacent_ids']],h)
                self.assertTrue(proof['all_slabs_have_positive_solid_overlap'])
                self.assertEqual(proof['slabs'],oldproof['slabs'])


if __name__=='__main__':
    suite=unittest.defaultTestLoader.loadTestsFromTestCase(GatePackTests)
    names=[t.id().split('.')[-1] for t in suite]
    result=unittest.TextTestRunner(verbosity=2).run(suite)
    a.write('test_results.json',{'status':'PASS' if result.wasSuccessful() else 'FAIL','tests_run':result.testsRun,'test_names':names,'failures':len(result.failures),'errors':len(result.errors),'test_source':a.ref(Path(__file__)),'pack':a.ref(a.HERE/'pack.json'),'scope':'Static native geometry and source composition only. No GUI or runtime.'})
    raise SystemExit(0 if result.wasSuccessful() else 1)
