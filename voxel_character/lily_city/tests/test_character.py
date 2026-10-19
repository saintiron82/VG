from pathlib import Path
import copy,hashlib,itertools,json,sys,unittest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from appearance import derive_sources,load_sources,validate_preset
from author_source import make_sources
sys.path.insert(0,str(ROOT.parent/'common'/'animation'))
from build_render import make_animated_render
from core import digest

class CharacterTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.sources=load_sources();cls.master=cls.sources['master.json'];cls.rig=cls.sources['rig.json']
  cls.preset=json.loads((ROOT/'data'/'lily.preset.json').read_text())
  cls.cache=json.loads((ROOT/'generated'/'r5'/'lily.render.json').read_text())
 def test_source_authoring_is_reproducible(self):self.assertEqual(make_sources(),self.sources)
 def test_lily_is_exact_shared_preset(self):self.assertEqual(derive_sources(self.preset),self.sources)
 def test_all_sidecars_bind_source(self):
  for n,v in self.sources.items():
   if n!='master.json':self.assertEqual(v['master_hash'],digest(self.master))
 def test_hierarchy_and_channels_are_complete(self):
  seen=set()
  for p in self.rig['parts']:
   self.assertNotIn(p['id'],seen)
   self.assertTrue(p['parent'] is None or p['parent'] in seen)
   seen.add(p['id'])
  channels=[set(v) for v in self.rig['motion_channels'].values()]
  self.assertEqual(set.union(*channels),seen)
  self.assertTrue(all(not(a&b) for a,b in itertools.combinations(channels,2)))
  self.assertEqual(len(seen),28)
 def test_immutable_common_copies(self):
  for n,p in [('RenderData.gd','preview/RenderData.gd'),('TransformTracks.gd','animation/TransformTracks.gd')]:
   self.assertEqual((ROOT/'generated'/'r5'/'common'/n).read_bytes(),(ROOT.parent/'common'/p).read_bytes())
 def test_cache_has_true_3d_separate_parts(self):
  self.assertEqual(len(self.cache['rigid_parts']),28)
  self.assertEqual(self.cache['groups'],[])
  for p in self.cache['rigid_parts']:
   self.assertGreater(p['cell_count'],0)
   self.assertTrue(all(b-a>=.019 for a,b in zip(p['bounds']['min'],p['bounds']['max'])))
  self.assertLessEqual(self.cache['cell_count'],70000)
  self.assertLessEqual(self.cache['quad_count'],12000)
  self.assertEqual(self.cache['bounds']['min'][1],0)
  self.assertAlmostEqual(self.cache['bounds']['max'][1],1.76)
 def test_eyes_are_palette_voxel_geometry(self):
  head=next(p for p in self.cache['rigid_parts'] if p['selector']['part']=='head')
  materials={g['material'] for g in head['groups']}
  self.assertTrue({'iris','iris_light','eye_white','pupil'}<=materials)
 def test_motion_keys_close_loops_and_preserve_geometry(self):
  for name in ['idle.json','walk.json','blink.json']:
   c=self.sources[name]
   for t in c['tracks']:
    self.assertEqual(t['keys'][0]['rotation_degrees'],t['keys'][-1]['rotation_degrees'])
    self.assertEqual(t['keys'][0]['translation'],t['keys'][-1]['translation'])
  changed=copy.deepcopy(self.sources['bind.json'])
  changed['tracks'][0]['keys'][1]['rotation_degrees']=70
  result=make_animated_render(self.master,changed,.02,max_candidates=1000000)
  self.assertEqual(result,self.cache)
 def test_blink_geometry_covers_open_iris(self):
  lids=[p for p in self.cache['rigid_parts'] if p['selector']['part'].startswith('eyelid_')]
  for p in lids:
   self.assertLessEqual(round(p['bounds']['min'][1]-.08,6),1.58)
   self.assertGreaterEqual(round(p['bounds']['max'][1]-.08,6),1.64)
 def test_repeated_common_build_same_payload(self):
  generated=make_animated_render(self.master,self.sources['bind.json'],.02,max_candidates=1000000)
  self.assertEqual(generated,self.cache)
 def test_invalid_presets_fail_loudly(self):
  for update in [{'body_frame':'child'},{'face':'unknown'},{'palette':{'skin':'red'}},{'palette':{'made_up':'ffffff'}},{'accessories':{'cape':'true'}},{'id':'../escape'}]:
   p={**self.preset,**update}
   with self.assertRaises(ValueError):validate_preset(p)
 def test_preset_variants_reuse_rig_and_compiler(self):
  for i,(body,face,hair,outfit) in enumerate([('slender','angular','cropped','work_tunic'),('broad','soft','loose','guard_tabard'),('standard','angular','braided','traveller_tunic')]):
   p={**self.preset,'id':'fixture_'+str(i),'body_frame':body,'face':face,'hair_style':hair,'outfit':outfit,'palette':{'silver':'593d2d','iris':'486d9b'},'accessories':{'cape':False,'satchel':i==2}}
   sources=derive_sources(p)
   self.assertEqual(sources['master.json']['extensions']['appearance']['base_master_hash'],digest(self.master))
   render=make_animated_render(sources['master.json'],sources['bind.json'],.02,max_candidates=1000000)
   ids={v['selector']['part'] for v in render['rigid_parts']}
   self.assertEqual(ids,{v['id'] for v in sources['rig.json']['parts']})
   self.assertNotIn('cape',ids)
   self.assertEqual('braid' in ids,hair=='braided')
   self.assertEqual(render['materials']['silver'],'593d2d')
   self.assertTrue(render['cell_count']>10000)
   self.assertTrue(render['bounds']['max'][1]<2.0)
if __name__=='__main__':unittest.main()
