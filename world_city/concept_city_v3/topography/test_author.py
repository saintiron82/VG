"""Bounded source checks only; no city compile, GUI or runtime physics claim."""
import hashlib
import math
import random
import unittest
from . import author as a
from world_city.runtime_city.checks.placement import intersection_area

class TerrainWaterContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.contract=a.build_contract()

    def test_provenance(self):
        self.assertEqual(self.contract['source_plan_sha256'],hashlib.sha256(a.SOURCE_PLAN_BYTES).hexdigest())

    def test_landmark_host_datums(self):
        for point,y in [((-300,-250),24),((250,-230),14),((-270,120),8),((20,-32),4)]:
            self.assertAlmostEqual(a.land_height_at(*point),y,places=8)

    def test_superseded_landmark_pads(self):
        self.assertFalse(set(p['building_id'] for p in a.building_pads())&a.SUPERSEDED_LANDMARK_PADS)

    def test_dry_full_width_grade_bound(self):
        rng=random.Random(1450)
        for _ in range(3000):
            x,z=rng.uniform(-530,530),rng.uniform(-510,530)
            theta=rng.uniform(0,math.tau);d=rng.uniform(.01,8)
            q=(x+math.cos(theta)*d,z+math.sin(theta)*d)
            self.assertLessEqual(abs(a.dry_height_at(x,z)-a.dry_height_at(*q)),.12*d+1e-8)

    def test_current_road_profiles(self):
        for p in self.contract['road_profiles'].values():self.assertLessEqual(p['maximum_sampled_grade'],.12+1e-8)

    def test_water_ownership_disjoint(self):
        domains=a.finite_water_domains()
        for i,p in enumerate(domains):
            for q in domains[i+1:]:
                self.assertLessEqual(intersection_area(p['polygon_xz_m'],q['polygon_xz_m']),1e-7)

    def test_water_beds(self):
        for d in a.finite_water_domains():
            poly=d['polygon_xz_m'];points=poly+[[sum(p[j] for p in poly)/len(poly) for j in (0,1)]]
            for x,z in points:
                y=a.water_height_at(d['surface_id'],x,z,d.get('segment_index',0))
                self.assertLess(a.height_at(x,z),y-.1)

    def test_river_mouth_full_width_head(self):
        count=0
        for d in a.finite_water_domains():
            if d['surface_id']!='SERVICE_CANAL':continue
            for x,z in d['polygon_xz_m']:
                if abs(z-420)<1e-8:
                    self.assertAlmostEqual(a.water_height_at('SERVICE_CANAL',x,z,d['segment_index']),a.river_water_y(x),places=9)
                    count+=1
        self.assertGreaterEqual(count,4)

    def test_join_head_is_single_valued(self):
        for w in a.WATER_SURFACES:
            if 'polyline_xz_m' not in w:continue
            for x,z in w['polyline_xz_m'][1:-1]:
                heads=[a.water_height_at(w['id'],x+.3,z-.4,i) for i in range(len(w['levels_m'])-1)]
                self.assertLess(max(heads)-min(heads),1e-10)

    def test_downhill_and_lift_energy(self):
        g=self.contract['water_graph'];nodes={n['id']:n for n in g['nodes']}
        for e in g['edges']:
            if e['mode']=='manual_lift':self.assertTrue(e.get('energy_source'));continue
            self.assertGreater(nodes[e['source']]['head_y_m'],nodes[e['target']]['head_y_m'])

    def test_dirty_network_no_supply_path(self):
        g=self.contract['water_graph'];nodes={n['id']:n for n in g['nodes']};edges={n:[] for n in nodes}
        for e in g['edges']:edges[e['source']].append(e['target'])
        for start,n in nodes.items():
            if n['network'] not in ['storm','contained_waste','industrial_nonpotable']:continue
            pending=[start];seen=set()
            while pending:
                p=pending.pop()
                if p in seen:continue
                seen.add(p);self.assertNotEqual(nodes[p]['network'],'protected_supply');pending+=edges[p]

    def test_primary_pad_thresholds(self):
        failures=[]
        for p in a.building_pads():
            x,z=p['primary_entrance_xz_m'];floor=p['floor_y_m']
            if abs(a.land_height_at(x,z)-floor)>1e-7:failures.append(p['building_id'])
            if p['door_path_id']:self.assertAlmostEqual(a.path_height_at(p['door_path_id'],x,z),floor,places=8)
        self.assertEqual(failures,[])

    def test_compound_gate_datums_and_support(self):
        self.assertEqual(len(a.compound_pads()),7)
        for p in a.compound_pads():
            self.assertLess(p['foundation_bottom_y_m'],p['floor_y_m'])
            for gate in p['gate_ledger']:
                self.assertAlmostEqual(a.land_height_at(*gate['xz_m']),p['floor_y_m'],places=8)
                self.assertEqual(gate['delta_m'],0)

    def test_actual_stair_dimensions_and_ownership(self):
        ready=[s for s in a.actual_stairs() if s['status']=='source_geometry_ready_uncompiled']
        self.assertGreaterEqual(len(ready),1)
        for s in ready:
            self.assertLessEqual(s['step_rise_m'],.15)
            self.assertEqual(len(s['treads']),s['step_count'])
            self.assertAlmostEqual(s['top_y_m']-s['bottom_y_m'],s['step_count']*s['step_rise_m'])
            for tread in s['treads']:
                poly=tread['polygon_xz_m'];x=sum(p[0] for p in poly)/4;z=sum(p[1] for p in poly)/4
                self.assertAlmostEqual(a.height_at(x,z),tread['top_y_m'],places=8)

    def test_declared_door_paths_are_exact_and_bounded(self):
        for pad in a.building_pads():
            for entry in pad['entrance_ledger']:
                self.assertIsNotNone(entry['path_id'])
                path=a._PATH_INDEX[entry['path_id']]
                self.assertLess(math.dist(path['polyline_xz_m'][0],entry['xz_m']),1e-7)
                self.assertLessEqual(entry['approach_length_m'],2+1e-8)
                self.assertLessEqual(math.dist(entry['xz_m'],entry['landing_outer_xz_m']),2+1e-8)
            self.assertEqual(pad['door_path_id'],pad['entrance_ledger'][0]['path_id'])

    def test_approach_weight_is_zero_at_outer_and_public_corridor(self):
        for pad in a.building_pads():
            for entry in pad['entrance_ledger']:
                outer=entry['landing_outer_xz_m']
                self.assertLess(a._entry_weight(entry,*outer),1e-7)
                for point in entry['approach_polyline_xz_m']:
                    if a._road_clearance(*point)<=0:self.assertEqual(a._entry_weight(entry,*point),0)

    def test_port_freeboard(self):
        self.assertAlmostEqual(self.contract['port']['minimum_normal_stage_freeboard_m'],1.28)
        self.assertTrue(self.contract['port']['normal_stage_only_not_flood_safety'])

    def test_nonfinite_rejected(self):
        for x,z in [(float('nan'),0),(0,float('inf'))]:
            with self.assertRaises(ValueError):a.height_at(x,z)

if __name__=='__main__':unittest.main()
