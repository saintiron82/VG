"""Local source/cache/interface tests only. No placement or simulation claim."""
import copy,json,math,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[4];sys.path.insert(0,str(ROOT))
from voxel_character.common import core,coordinate_planes
from world_city.concept_city_v3.assemblies.waterworks.author import HERE,KINDS,HEAD_CONTRACT,make_master,ref,write,CANDIDATE_CAP,OUTPUT_CAP,approved_palette,source_bounds


def read(p):return json.loads(p.read_text())
def master(k):return read(HERE/'masters'/f'{k}.json')
def sampled(k):
 s=master(k);return coordinate_planes.compile_master(s,{'pitch':s['extensions']['smoke_pitch_m']},max_candidate_cells=CANDIDATE_CAP,max_output_cells=OUTPUT_CAP)
def sockets(m):return {s['id']:s['position_m'] for s in m['extensions']['sockets']}


class WaterworksTests(unittest.TestCase):
 def test_source_schema_palette_and_status(self):
  for kind in KINDS:
   m=master(kind);core.validate_master(m,m['extensions']['smoke_pitch_m']);self.assertEqual(source_bounds(m),m['extensions']['local_bounds_m'])
   self.assertFalse(m['provenance']['new_engine']);self.assertFalse(m['provenance']['new_mesher'])
   self.assertEqual(m['materials'],approved_palette('slate_gray'))
   for k in ('actual_placed','visually_reviewed'):self.assertFalse(m['extensions'][k])
   self.assertIsNone(m['extensions']['city_placement']);self.assertTrue(m['extensions']['supports'])

 def test_all_cache_hashes_and_budget(self):
  report=read(HERE/'evidence/compile_report.json');self.assertEqual(report['status'],'pass');self.assertEqual(len(report['requests']),12)
  self.assertEqual(report['author']['sha256'],ref(report['author']['path'])['sha256'])
  for r in report['requests']:
   self.assertTrue(r['valid']);self.assertEqual(r['source']['sha256'],ref(r['source']['path'])['sha256']);self.assertEqual(r['master_hash'],core.digest(master(r['id'])))
   self.assertEqual(r['render']['sha256'],ref(r['render']['path'])['sha256']);self.assertLessEqual(r['candidate_cells'],CANDIDATE_CAP);self.assertLessEqual(r['output_cells'],OUTPUT_CAP)
   self.assertTrue(all(c['pass'] for c in r['constraints']))

 def test_network_separation_and_no_water_solids(self):
  expected={'spring_intake':'raw_clean_source','reservoir_lining_segment':'raw_clean_source','covered_clean_conduit':'protected_supply','covered_wellhouse':'protected_supply','service_channel_segment':'industrial_nonpotable','sluice_bay':'industrial_nonpotable','undershot_mill_wheel':'industrial_nonpotable','drain_outfall':'storm'}
  for kind,net in expected.items():
   m=master(kind);self.assertEqual(m['extensions']['network'],net)
   self.assertFalse(any('water'==op.get('material') for c in m['components'] for op in c['operations']))
  self.assertFalse(HEAD_CONTRACT['hydraulics_validated'])

 def test_matching_terrain_dimension_contract(self):
  from world_city.concept_city_v3.topography.author import WATER_SURFACES
  by={w['id']:w for w in WATER_SURFACES}
  self.assertEqual(by['SERVICE_CANAL']['width_m'],6);self.assertEqual(by['SERVICE_CANAL']['bed_depth_m'],.8)
  self.assertEqual(by['SPRING_FEEDER']['width_m'],2);self.assertEqual(by['NORTHERN_RESERVOIR']['water_y_m'],16)
  self.assertEqual(by['NORTHERN_RESERVOIR']['bed_depth_m'],2.4);self.assertEqual(by['NORTHERN_RESERVOIR']['bank_crest_y_m'],18)
  for mill in HEAD_CONTRACT['mill_candidates']:self.assertAlmostEqual(mill['forebay_y_m']-mill['tailwater_y_m'],.8)

 def test_wheel_bearing_sockets_and_static_rig(self):
  w=master('undershot_mill_wheel');b=master('mill_bank_interface');ws,bs=sockets(w),sockets(b)
  self.assertEqual(ws['drive_axle'],bs['axle_left']);self.assertEqual(ws['bearing_axle'],bs['axle_right'])
  self.assertEqual(w['components'][0]['id'],'wheel');self.assertEqual(len(w['components'][0]['parts']),1)
  self.assertTrue(all(o['part']=='rotor' for o in w['components'][0]['operations']))
  self.assertEqual(w['extensions']['animation_hooks'][0]['pivot_local_m'],[0,.8,0]);self.assertEqual(w['extensions']['animation_hooks'][0]['axis_local'],[1,0,0])
  self.assertTrue(sampled('mill_bank_interface')['valid'])

 def test_default_stair_exact_sample_and_parameter_variants(self):
  s=master('retaining_stair_landing');c=sampled('retaining_stair_landing');self.assertTrue(c['valid'])
  p=.15;cells=c['cells'];tops=[]
  for i in range(8):
   z=-1.2+i*.3+.15
   col=[(r[1]+1)*p for r in cells if abs((r[0]+.5)*p)<.2 and abs((r[2]+.5)*p-z)<.151]
   # Exact tread interior, not neighboring cell centers at the riser boundary.
   col=[(r[1]+1)*p for r in cells if abs((r[0]+.5)*p)<.2 and -1.2+i*.3+1e-7<(r[2]+.5)*p<-1.2+(i+1)*.3-1e-7]
   top=max(col);tops.append(top);self.assertAlmostEqual(top,(i+1)*.15)
  for spec in ({'risers':14,'rise_m':2},{'risers':26,'rise_m':3.84}):
   a=make_master('retaining_stair_landing',spec);e=a['extensions']['authored_parameters'];self.assertAlmostEqual(e['riser_count']*e['riser_m'],spec['rise_m']);self.assertLessEqual(e['riser_m'],.15)
  with self.assertRaises(ValueError):make_master('retaining_stair_landing',{'risers':4,'rise_m':1})
  write(HERE/'evidence/stair_source_and_sample.json',{'default_sample_pitch_m':.15,'sampled_tread_tops_m':tops,'source_variants':[{'risers':14,'total_rise_m':2,'source_riser_m':2/14},{'risers':26,'total_rise_m':3.84,'source_riser_m':3.84/26}],'variant_sample_status':'Source contract only; no pitch-specific endpoint or controller validation for these variants.'})

 def test_bridge_opening_and_repeat_interfaces(self):
  s=master('stone_road_bridge_bay');p=s['extensions']['authored_parameters'];ss=sockets(s)
  self.assertEqual(ss['repeat_-8'],[-8,0,0]);self.assertEqual(ss['repeat_8'],[8,0,0]);self.assertLess(p['foundation_y_m'],p['candidate_bed_y_m'])
  c=sampled('stone_road_bridge_bay');self.assertTrue(c['valid'])
  self.assertFalse(any(abs((r[0]+.5)*.2)<2.9 and -4.8<(r[1]+.5)*.2<-1.4 for r in c['cells']))
  self.assertTrue(any(abs((r[0]+.5)*.2)>7.05 and (r[1]+.5)*.2<-5.1 for r in c['cells']))

 def test_small_independent_repeat(self):
  s=master('spring_intake');a=coordinate_planes.compile_master(copy.deepcopy(s),{'pitch':.2});b=coordinate_planes.compile_master(copy.deepcopy(s),{'pitch':.2})
  self.assertTrue(a['valid'] and b['valid']);self.assertEqual(a['payload_hash'],b['payload_hash']);write(HERE/'evidence/independent_repeat.json',{'id':'spring_intake','first_payload_hash':a['payload_hash'],'second_payload_hash':b['payload_hash'],'equal':True,'independent_compiles':True,'copied_output':False})

if __name__=='__main__':
 result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(WaterworksTests))
 write(HERE/'evidence/test_report.json',{'status':'pass' if result.wasSuccessful() else 'fail','tests_run':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),'source':ref('world_city/concept_city_v3/assemblies/waterworks/test_waterworks.py'),'actual_placed':False,'visual_review':False,'whole_city_compile':False,'runtime_motion':False,'hydraulic_validation':False})
 sys.exit(0 if result.wasSuccessful() else 1)
