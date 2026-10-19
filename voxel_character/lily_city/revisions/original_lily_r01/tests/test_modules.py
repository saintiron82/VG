from pathlib import Path
import copy,hashlib,json,sys,unittest
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
from assemble import assemble,load_module,point,FRAMES,sha
from residents import generate
from core import digest

def preset(name='lily_original'):return json.loads((ROOT/'data/presets'/(name+'.json')).read_text())
class ModuleTests(unittest.TestCase):
 def test_deterministic_pure_assembly(self):
  p=preset();original=copy.deepcopy(p);a=assemble(p);b=assemble(p);self.assertEqual(a,b);self.assertEqual(p,original)
 def test_layer_separation(self):
  s=assemble(preset());layers=s['master.json']['extensions']['assembly']['layers'];self.assertEqual({m['layer'] for m in layers},{'body','face','hair','costume','ornament'})
  parts=s['rig.json']['parts'];cost=[q for q in parts if q['id'].startswith('costume_')];self.assertGreaterEqual(len(cost),10)
  by={q['id']:q for q in parts}
  for p in cost:self.assertEqual(p['pivot_m'],by[p['parent']]['pivot_m'])
 def test_all_bindings_topological(self):
  for path in (ROOT/'data/presets').glob('*.json'):
   s=assemble(json.loads(path.read_text()));rig=s['rig.json'];master=s['master.json'];ids=[q['id'] for q in rig['parts']];self.assertEqual(len(ids),len(set(ids)));self.assertLessEqual(len(ids),72)
   seen=set()
   for q in rig['parts']:self.assertTrue(q['parent'] is None or q['parent'] in seen);seen.add(q['id'])
   self.assertEqual(set(ids),{t['selector']['part'] for t in s['bind.json']['tracks']})
   self.assertEqual(set(ids),{o['part'] for o in master['components'][0]['operations']})
   opids=[o['id'] for o in master['components'][0]['operations']];self.assertEqual(len(opids),len(set(opids)))
   for k,v in s.items():
    if k!='master.json':self.assertEqual(v['master_hash'],digest(master));self.assertEqual(v['source_id'],master['id'])
 def test_adult_capsule_exact(self):
  s=assemble(preset());self.assertEqual(s['rig.json']['capsule'],{'radius_m':.23,'height_m':1.72,'center_m':[0,.86,0]})
 def test_actual_reference(self):
  r=json.loads((ROOT/'data/reference.json').read_text());p=ROOT/'reference/current_app_neutral.png';self.assertEqual(sha(p),r['original_sha256']);self.assertIn('rear and side geometry',r['new_interpretation'])
 def test_preserved_medieval_geometry(self):
  m=load_module('medieval_traveller_r5');base=json.loads((ROOT.parents[1]/'data/master.json').read_text());by={o['id']:o for o in base['components'][0]['operations']}
  self.assertGreater(len(m['operations']),90)
  for o in m['operations']:self.assertEqual(o,by[o['id']])
 def test_unique_lily_reserved(self):
  p=preset();p['id']='resident_fake';p['role']='resident'
  with self.assertRaises(ValueError):assemble(p)
 def test_garment_slot_validation(self):
  p=generate(1,'resident','residential',1,'male_tunic');p['costume'].append('female_dress')
  with self.assertRaises(ValueError):assemble(p)
 def test_age_rejection(self):
  p=generate(2,'child','residential',2,'child_tunic');p['body']='adult_female'
  with self.assertRaises(ValueError):assemble(p)
 def test_occupation_district_rejection(self):
  with self.assertRaises(ValueError):generate(3,'guard','garden')
 def test_saved_preset_cannot_bypass_rules(self):
  p=generate(3,'guard','civic',1,'male_coat');p['district']='garden'
  with self.assertRaises(ValueError):assemble(p)
  p=generate(4,'resident','residential',1,'female_long_dress');p['role']='porter';p['district']='harbor'
  with self.assertRaises(ValueError):assemble(p)
 def test_role_cannot_hide_disallowed_geometry_behind_label(self):
  p=generate(3,'guard','civic',1,'male_coat');p['costume']=generate(4,'resident','residential',1,'male_workwear')['costume']
  with self.assertRaises(ValueError):assemble(p)
 def test_apron_fitting_is_separate_and_source_immutable(self):
  p=generate(2,'resident','residential',1,'female_blouse_skirt');before=load_module('apron_bib');m=assemble(p)['master.json'];self.assertEqual(load_module('apron_bib'),before)
  fits=m['extensions']['assembly']['costume_fit'];self.assertEqual(fits[0]['selected_skirt'],'female_skirt');self.assertGreater(len([o for o in m['components'][0]['operations'] if '__fitted_band_' in o['id']]),20)
  self.assertNotIn('costume_fit',assemble(preset())['master.json']['extensions']['assembly'])
 def test_seed_repeatability(self):
  self.assertEqual(generate(61019,'resident','residential'),generate(61019,'resident','residential'));self.assertNotEqual(generate(61019,'resident','residential'),generate(61020,'resident','residential'))
 def test_child_has_nonuniform_proportions(self):
  f=FRAMES['child'];leg=point([0,.94,0],f)[1];head=point([0,1.82,0],f)[1]-point([0,1.405,0],f)[1]
  self.assertGreater(head/(leg+head),(.415/(.94+.415)));self.assertNotAlmostEqual(point([0,1.405,0],f)[1]/1.405,point([0,.94,0],f)[1]/.94)
 def test_geometry_not_palette_only(self):
  ps=[json.loads(p.read_text()) for p in (ROOT/'data/presets').glob('resident*.json')];geoms=[]
  for p in ps:
   m=assemble(p)['master.json'];geoms.append(digest(m['components'][0]['operations']))
  self.assertEqual(len(geoms),10);self.assertEqual(len(set(geoms)),10)
 def test_all_cache_manifests(self):
  for manifest_file in (ROOT/'generated').rglob('manifest.json'):
   folder=manifest_file.parent
   if not folder.is_dir() or not (folder/'manifest.json').exists():continue
   m=json.loads((folder/'manifest.json').read_text());source=json.loads((folder/'derived.master.json').read_text());self.assertEqual(m['source_master_hash'],digest(source))
   for name,value in m['files'].items():self.assertEqual(sha(folder/name),value)
   for name in ['RenderData.gd','TransformTracks.gd']:
    self.assertEqual(sha(folder/'common'/name),sha(ROOT.parents[1]/'generated/r5/common'/name))
if __name__=='__main__':unittest.main(verbosity=2)
