"""Bounded source and real common-master regressions; no GUI/full-city build."""
import copy,json,math,unittest
from pathlib import Path
from .author_overlay import ROOT,HERE,TREE_FORMS,build_revision_overlay,validate_overlay,apply_revision_overlay,make_master,master_bounds,digest,rect,polygon_area
from voxel_character.common.coordinate_planes import compile_master

class OverlayTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.scene=json.loads((ROOT/'world_city/runtime_city/generated/r2/scene.flat_property.json').read_text())
  cls.base=json.loads((ROOT/'world_city/runtime_city/revisions/r3/urban_fabric.access_repaired.json').read_text())
  cls.data=json.loads((HERE/'generated/overlay.json').read_text())
 def checks(self,d):return validate_overlay(d,self.scene,self.base)
 def test_full_independent_source_audit(self):
  r=self.checks(self.data);self.assertTrue(r['valid'],r['errors']);self.assertEqual(r['retained_access_reservations_checked'],1773);self.assertEqual(r['new_access_reservations_checked'],9)
 def test_deterministic_authored_output(self):self.assertEqual(self.data,build_revision_overlay(self.scene,self.base))
 def test_exact_boundary_and_gates(self):
  for p in self.data['property_records']:
   self.assertAlmostEqual(p['designed_wall_length_m']+p['intentional_gate_length_m'],p['boundary_perimeter_m'])
   self.assertGreaterEqual(p['coherent_garden_area_m2'],60);self.assertEqual(len(p['gates']),3)
   for g in p['gates']:self.assertTrue(any(a['gate_id']==g['id'] for a in self.data['access_reservations']))
 def test_missing_boundary_panel_rejected(self):
  d=copy.deepcopy(self.data);target=next(p for p in d['placements'] if p['spec']['kind']=='wall_panel' and p['spec']['width_m']==6);d['placements'].remove(target)
  names={e['check'] for e in self.checks(d)['errors']};self.assertIn('missing_property_geometry',names);self.assertIn('physical_wall_centerline_gap',names)
 def test_stale_pose_envelope_rejected(self):
  d=copy.deepcopy(self.data);d['placements'][0]['position_m'][0]+=5
  self.assertIn('stale_clearance_envelope',{e['check'] for e in self.checks(d)['errors']})
 def test_road_or_building_overlap_rejected(self):
  d=copy.deepcopy(self.data);p=d['placements'][0];b=self.scene['instances'][0];p['position_m']=b['position_m'][:];p['yaw_rad']=0;p['clearance_footprint_xz_m']=rect([p['position_m'][0],p['position_m'][2]],*master_bounds(p['spec'])[:2])
  self.assertIn('building_road_river_intersection',{e['check'] for e in self.checks(d)['errors']})
 def test_inherited_access_never_silently_deleted(self):
  merged=apply_revision_overlay(self.base,self.data);removed=set(self.data['replacement_ledger']['remove_access_reservation_ids']);old={a['id']:a for a in self.base['access_reservations'] if a['id'] not in removed};after={a['id']:a for a in merged['access_reservations']}
  self.assertTrue(all(after[k]==v for k,v in old.items()))
 def test_overlay_application_reversible_and_input_immutable(self):
  before=digest(self.base);merged=apply_revision_overlay(self.base,self.data);self.assertEqual(before,digest(self.base))
  removed=set(self.data['replacement_ledger']['remove_placement_ids']);after={p['id'] for p in merged['placements']};self.assertFalse(after&removed)
  self.assertEqual(merged['building_override_specs'],self.base['building_override_specs']);self.assertTrue(self.data['replacement_ledger']['preserve_all_building_poses'])
  with self.assertRaises(ValueError):apply_revision_overlay({},self.data)
 def test_all_common_masters_compile_and_fit_envelopes(self):
  self.assertLessEqual(len(self.data['master_specs']),24);stats=[]
  for key,spec in self.data['master_specs'].items():
   pitch=1 if spec['kind']=='forest_tree' else .5;master=make_master(spec);self.assertEqual(master['schema'],'riverstone.voxel.master.v1');result=compile_master(master,{'pitch':pitch},max_candidate_cells=250000,max_output_cells=100000)
   self.assertTrue(result['valid']);self.assertTrue(result['cells']);self.assertEqual(master,make_master(spec));w,d,h=master_bounds(spec)
   lo=[min(c[a] for c in result['cells'])*pitch for a in range(3)];hi=[(max(c[a] for c in result['cells'])+1)*pitch for a in range(3)]
   for a in range(3):self.assertGreaterEqual(lo[a]+1e-6,[-w/2,-1,-d/2][a]);self.assertLessEqual(hi[a]-1e-6,[w/2,h,d/2][a])
   stats.append({'asset_key':key,'spec':spec,'pitch_m':pitch,'occupied_cells':len(result['cells']),'candidate_cells':result['candidate_cells'],'sampled_bounds':{'min':lo,'max':hi},'payload_hash':result['payload_hash']})
  (HERE/'generated/master_sampling_report.json').write_text(json.dumps(stats,indent=2)+'\n')
 def test_varied_cluster_forest_and_dense_cores(self):
  for f in self.data['vegetation_land_use']:
   self.assertEqual(set(f['tree_forms']),set(TREE_FORMS));self.assertGreater(f['nearest_trunk_distance_cv'],.2);self.assertGreater(f['projected_rounded_canopy_union_fraction_2m_grid'],.4);self.assertGreater(max(q['projected_canopy_fraction'] for q in f['wooded_core_windows']),.55)
  self.assertGreater(max(q['projected_canopy_fraction'] for q in self.data['vegetation_land_use'][0]['wooded_core_windows']),.8)
 def test_roots_have_narrow_support_anchors(self):
  for p in self.data['placements']:
   if p['spec']['kind']=='forest_tree':
    self.assertEqual(p['ground_anchor']['support_footprint_kind'],'trunk_root');self.assertAlmostEqual(polygon_area(p['ground_anchor']['support_points_xz_m']),4,places=6);self.assertGreater(polygon_area(p['footprint_xz_m']),60)
 def test_short_grade_modules(self):
  for p in self.data['placements']:
   if p['property_id']=='UF_ESTATE_03' and p['category'] in ('estate_boundary','estate_formal_garden','estate_garden_path'):
    w,d,h=master_bounds(p['spec']);self.assertLessEqual(math.hypot(w,d)*.12,.75)
 def test_source_freezes_untouched(self):
  import hashlib
  p=ROOT/'world_city/runtime_city/urban_fabric/author.py';self.assertEqual(hashlib.sha256(p.read_bytes()).hexdigest(),'59c3b05d210237f681d6d3f6dcdbf2321a7158ce1a12c38ee86c1dd3ec85faae')
  p=ROOT/'world_city/runtime_city/urban_fabric/generated/urban_fabric.json';self.assertEqual(hashlib.sha256(p.read_bytes()).hexdigest(),'ec39c8ba1934179b9520a602c95dc71452f91ee10f11df106a6cc81c0c1dfe29')
if __name__=='__main__':unittest.main()
