import copy,json,pathlib,tempfile,unittest
import prepare as p
class CompositionTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory(dir=p.H);self.h=pathlib.Path(self.tmp.name);self.scene={'common_assets':{'A':{'render_sha256':'dummy'}},'common_instances':[{'id':'BASE','asset_key':'A','position_m':[0,0,0]}]}
 def tearDown(self):self.tmp.cleanup()
 def run_packs(self,packs):
  refs=[]
  for i,extra in enumerate(packs):
   path=self.h/f'{i}.json';path.write_text(json.dumps(dict(schema='riverstone.city.visual_addendum.v1',base_scene_sha256=p.BASE_SHA,**extra)));refs.append(p.ref(path))
  return p.compose_natives(self.scene,{'schema':'riverstone.city.visual_pack_index.v1','base_scene_sha256':p.BASE_SHA,'packs':refs},{})
 def test_later_pack_retires_earlier_addition(self):
  _,instances,report=self.run_packs([{'add_instances':[{'id':'ADDED','asset_key':'A','position_m':[1,0,0]}]},{'remove_instance_ids':['ADDED']}]);self.assertEqual([r['id']for r in instances],['BASE']);self.assertEqual(report['removed'],['ADDED'])
 def test_unknown_removal_rejected(self):
  with self.assertRaises(AssertionError):self.run_packs([{'remove_instance_ids':['UNKNOWN']}])
 def test_duplicate_removal_rejected(self):
  with self.assertRaises(AssertionError):self.run_packs([{'remove_instance_ids':['BASE']},{'remove_instance_ids':['BASE']}])
 def test_duplicate_instance_rejected(self):
  with self.assertRaises(AssertionError):self.run_packs([{'add_instances':[{'id':'BASE','asset_key':'A','position_m':[0,0,0]}]}])
 def test_scaled_instance_rejected(self):
  with self.assertRaises(AssertionError):self.run_packs([{'add_instances':[{'id':'SCALED','asset_key':'A','position_m':[0,0,0],'scale':[2,1,1]}]}])
if __name__=='__main__':unittest.main()
