"""Bounded contract tests; no sampling, GUI, or city placement."""
import json
import math
import unittest
from build_audit import HERE,ROOT,CONTROLS,camera_functions,pose,core,estimate_candidates


class RegisteredContracts(unittest.TestCase):
    def setUp(self):
        self.audit=json.loads((HERE/'concept_shape_audit.json').read_text());self.plan=json.loads((HERE/'adaptation_plan.json').read_text())

    def test_inputs_and_sealed_sources(self):
        import hashlib
        for r in self.audit['inputs']:
            self.assertEqual(hashlib.sha256((ROOT/r['path']).read_bytes()).hexdigest(),r['sha256'])
        self.assertTrue(self.audit['sealed_source_cache_hashes_unchanged'])
        self.assertTrue(all(r['pass'] for r in self.audit['cost_estimator_checks']))

    def test_fit_and_road_gate(self):
        self.assertFalse(self.audit['registered_road_footprint_check']['conflicts'])
        for g in self.plan['groups']:
            for m in g['modules']:
                self.assertEqual(m.get('precinct_fit',{}).get('outside_samples',0),0)
        self.assertFalse(self.plan['apply_allowed'])

    def test_tower_pixel_columns(self):
        project,_,_,_=camera_functions(json.loads(CONTROLS.read_text()))
        targets={'single_bell_tower':([1120,263],[1120,84]),'rear_side_bell_tower':([244,500],[244,385])}
        for g in self.plan['groups']:
            for m in g['modules']:
                if m['id'] not in targets:continue
                b=m['local_bounds_m'];x,z=(b['min'][0]+b['max'][0])/2,(b['min'][2]+b['max'][2])/2
                foot=project(pose([x,0,z],g['world_origin_xyz_m'],g['yaw_degrees']));tip=project(pose([x,b['max'][1],z],g['world_origin_xyz_m'],g['yaw_degrees']))
                self.assertLess(math.dist(foot,targets[m['id']][0]),.01)
                self.assertLess(math.dist(tip,targets[m['id']][1]),4)

    def test_verified_tower_caches(self):
        r=json.loads((HERE/'evidence/tower_compile_report.json').read_text())
        self.assertEqual(r['status'],'pass');self.assertEqual(len(r['requests']),2)
        for q in r['requests']:
            s=json.loads((ROOT/q['source']['path']).read_text());cache=json.loads((ROOT/q['cache']['path']).read_text())
            self.assertEqual(core.digest(s),cache['master_hash'])
            self.assertEqual(q['candidate_cells'],estimate_candidates(s,.5)['candidate_cells_exact_aabb_visits'])
            self.assertLess(q['candidate_cells'],400000)
            self.assertEqual(cache['bounds']['max'][1],s['extensions']['spire_top_m'])
            self.assertFalse(q['actual_city_placement']);self.assertFalse(q['actual_visual_review'])

    def test_proxy_tower_and_open_gate(self):
        p=json.loads((HERE/'proxy_masses.json').read_text());groups={g['id']:g for g in p['groups']}
        for name,height in [('cathedral',128),('monastery',84)]:
            self.assertEqual(max(m['position_local_xyz_m'][1]+m['size_xyz_m'][1]/2 for m in groups[name]['masses']),height)
            self.assertTrue(any(m['semantic_role']=='stepped_spire_envelope' for m in groups[name]['masses']))
        gate=[m for m in groups['castle']['masses'] if m['id']=='front_gate_wing_header'][0]
        self.assertEqual(gate['position_local_xyz_m'][1]-gate['size_xyz_m'][1]/2,5)
        self.assertEqual(next(g for g in self.plan['groups'] if g['id']=='civic_registered')['separate_grain_hall']['status'],'held_not_in_proxy_handoff')


if __name__=='__main__':unittest.main()
