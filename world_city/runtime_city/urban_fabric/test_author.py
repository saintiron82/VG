"""Source geometry regressions; no GUI or full-city compile."""
from pathlib import Path
import copy,json,math,sys,unittest
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT))
from world_city.runtime_city.urban_fabric.author import make_master,validate_urban_fabric,rect,digest
from voxel_character.common import core,coordinate_planes
HERE=Path(__file__).parent

class UrbanFabricTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data=json.loads((HERE/'generated/urban_fabric.json').read_text())
        cls.plan=json.loads((ROOT/'world_city/data/city_brief.v2.json').read_text())
        cls.scene=json.loads((ROOT/'world_city/runtime_city/generated/r1/scene.json').read_text())
    def check_modified(self,position,collision=True,category=None):
        data=copy.deepcopy(self.data);p=copy.deepcopy(next(p for p in data['placements'] if p['category']=='craft_workyard'))
        p['id']='tampered_test';p['position_m']=[position[0],0,position[1]];p['collision_enabled']=collision
        if category:p['category']=category
        spec=data['master_specs'][p['asset_key']];p['conservative_sample_envelope_xz_m']=rect(position,spec['width_m'],spec['depth_m'],p['yaw_rad'],.18)
        data['placements']=[p]
        return validate_urban_fabric(data,self.plan,self.scene)
    def test_complete_source_audit_passes(self):
        self.assertTrue(validate_urban_fabric(self.data,self.plan,self.scene)['valid'])
    def test_building_obstruction_rejected(self):
        b=next(b for b in self.plan['building_plans'] if b['id']=='D01-B001')
        p=b['footprint_xz_m'];r=self.check_modified([sum(v[0] for v in p)/len(p),sum(v[1] for v in p)/len(p)])
        self.assertFalse(r['valid']);self.assertTrue(any(e.get('target',[None,None])[1]=='building' for e in r['errors']))
    def test_unchanged_reserved_courtyard_rejected(self):
        rep=set(self.data['repurposed_courtyard_plot_ids'])
        q=next(p for p in self.plan['plots'] if p.get('courtyard_xz_m') and p['id'] not in rep)['courtyard_xz_m']
        r=self.check_modified([sum(p[0] for p in q)/len(q),sum(p[1] for p in q)/len(q)])
        self.assertFalse(r['valid'])
        self.assertTrue(any(e.get('target',[None,None])[1]=='reserved_courtyard' for e in r['errors']))
    def test_road_obstruction_rejected(self):
        road=next(r for r in self.plan['roads'] if r['id']=='RT_MARKET_EDGE.001');n={n['id']:n for n in self.plan['road_nodes']}
        a=n[road['from_node']]['position_m'];b=n[road['to_node']]['position_m'];r=self.check_modified([(a[0]+b[0])/2,(a[2]+b[2])/2])
        self.assertFalse(r['valid']);self.assertTrue(any(e.get('target',[None,None])[1]=='road' for e in r['errors']))
    def test_cross_court_obstruction_rejected(self):
        a=next(a for a in self.data['access_reservations'] if a['kind']=='cross_courtyard')
        p,q=a['polyline_xz_m'];r=self.check_modified([(p[0]+q[0])/2,(p[1]+q[1])/2])
        self.assertFalse(r['valid']);self.assertTrue(any(e.get('target',[None,None])[1]=='access' for e in r['errors']))
    def test_market_core_reserved(self):
        r=self.check_modified([20,15]);self.assertFalse(r['valid'])
        self.assertTrue(any(e.get('target',[None,None])[1]=='protected_market_core' for e in r['errors']))
    def test_woodland_inside_city_rejected(self):
        r=self.check_modified([20,15],category='outer_woodland_tree')
        self.assertTrue(any(e['check']=='forest_inside_walls' for e in r['errors']))
    def test_source_id_ledger_and_distinct_estates(self):
        estates=self.data['properties'][:3]
        self.assertEqual({p['property_type'] for p in estates},{'older_stone_manor','merchant_palazzo','timber_courtyard_house'})
        ledger={s['source_building_id']:s for s in self.data['source_building_supersessions']}
        self.assertEqual(len(ledger),17)
        for o in self.data['building_override_specs']:
            self.assertIn(o['id'],ledger);self.assertNotIn('height_m',o)
            self.assertGreater(o['floor_height_m'],2);self.assertTrue(o['entrances'][0].get('access_polyline_xz_m'))
    def test_cache_is_finite_and_master_schema_unchanged(self):
        self.assertLessEqual(len(self.data['master_specs']),32)
        for spec in self.data['master_specs'].values():
            m=make_master(spec);core.validate_master(m,.25)
            self.assertEqual(m['schema'],'riverstone.voxel.master.v1')
            self.assertEqual(m,make_master(spec))
    def test_one_module_per_kind_compiles_nonempty(self):
        seen=set()
        for spec in self.data['master_specs'].values():
            if spec['kind'] in seen:continue
            seen.add(spec['kind']);master=make_master(spec)
            result=coordinate_planes.compile_master(master,{'pitch':.25},max_candidate_cells=250000,max_output_cells=100000)
            self.assertTrue(result['valid']);self.assertTrue(result['cells'])
        self.assertEqual(len(seen),9)
    def test_woodland_is_dense_in_bounded_cores(self):
        patches=[p for p in self.data['vegetation_land_use'] if p['land_use']=='outside_wall_woodland']
        self.assertEqual(len(patches),3)
        for p in patches:
            self.assertGreaterEqual(p['canopy_fraction'],.50)
            self.assertGreaterEqual(p['wooded_core_canopy_fraction'],.67)
            self.assertLessEqual(p['canopy_fraction'],1)
    def test_tree_support_is_root_not_crown(self):
        for p in self.data['placements']:
            if p['category'] not in ('outer_woodland_tree','orchard_tree'):continue
            anchor=p['ground_anchor'];self.assertEqual(anchor['support_footprint_kind'],'trunk_root')
            q=anchor['support_points_xz_m'];self.assertLess(max(v[0] for v in q)-min(v[0] for v in q),1)
            self.assertLess(max(v[1] for v in q)-min(v[1] for v in q),1)
    def test_roof_families_use_canonical_history_keys(self):
        for o in self.data['building_override_specs']:
            self.assertIn(o['roof_material_family'],('clay_red','wood_brown','slate_gray','approved_teal'))
            self.assertEqual(o['construction_era'],o['era_id'])
    def test_missing_terrain_anchor_rejected(self):
        d=copy.deepcopy(self.data);d['placements']=d['placements'][:1];d['placements'][0]['ground_anchor']={}
        self.assertTrue(any(e['check']=='missing_terrain_anchor' for e in validate_urban_fabric(d,self.plan,self.scene)['errors']))
    def test_stale_sample_guard_rejected(self):
        d=copy.deepcopy(self.data);d['placements']=d['placements'][:1];d['placements'][0]['position_m'][0]+=10
        self.assertTrue(any(e['check']=='stale_sample_envelope' for e in validate_urban_fabric(d,self.plan,self.scene)['errors']))

if __name__=='__main__':unittest.main()
