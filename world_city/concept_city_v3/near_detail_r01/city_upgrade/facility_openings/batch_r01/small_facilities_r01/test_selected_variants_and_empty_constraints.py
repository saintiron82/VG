"""No-sampling regression guards for exact variant selection and source bays."""
import copy,json,sys,unittest
from pathlib import Path
from unittest.mock import patch
HERE=Path(__file__).resolve().parent;sys.path.insert(0,str(HERE))
import plan_selected_variant_r01 as p
import verify_empty_constraint_geometry as e

class Variant(unittest.TestCase):
 def setUp(self):
  self.roof={'asset_key':'native__wood','native_asset_key':'native','source_sha256':'source','emitted_master_path':'roof','emitted_master_sha256':'roofsha','covering':'wood_shingle'}
  self.row={'asset_key':'native','source_sha256':'source','roof_variant_asset_key':'native__wood','roof_master_path':'roof','roof_master_sha256':'roofsha','roof_selector_path':'selector','roof_selector_sha256':'selected'}
  self.choice={'native_asset_key':'native','selected_variant_asset_key':'native__wood','source_master_sha256':'source','roof_covering':'wood_shingle'}
 def call(self):
  def load(path):
   if path==p.ROOFS:return {'assets':[self.roof]}
   if str(path)=='catalog':return {'assets':[self.row]}
   if str(path).endswith('/selector'):return {'placements':[self.choice]}
   raise AssertionError(path)
  with patch.object(p.a,'load',side_effect=load),patch.object(p.a,'sha',return_value='selected'):return p.selected_roof('native',Path('catalog'))
 def test_wood_keeps_explicit_native_identity(self):self.assertEqual(self.call()[1]['roof_variant_asset_key'],'native__wood')
 def test_unknown_variant(self):
  self.row['roof_variant_asset_key']='missing'
  with self.assertRaises(AssertionError):self.call()
 def test_wrong_native(self):
  self.roof['native_asset_key']='other'
  with self.assertRaises(AssertionError):self.call()
 def test_wrong_master(self):
  self.row['roof_master_sha256']='tilehash'
  with self.assertRaises(AssertionError):self.call()
 def test_wrong_source(self):
  self.row['source_sha256']='other'
  with self.assertRaises(AssertionError):self.call()
 def test_missing_selector(self):
  del self.row['roof_selector_path']
  with self.assertRaises(AssertionError):self.call()
 def test_wrong_selector_hash(self):
  self.row['roof_selector_sha256']='stale'
  with self.assertRaises(AssertionError):self.call()
 def test_wrong_placement_covering(self):
  self.choice['roof_covering']='roof_tile'
  with self.assertRaises(AssertionError):self.call()
 def test_wrong_placement_variant(self):
  self.choice['selected_variant_asset_key']='native'
  with self.assertRaises(AssertionError):self.call()
 def test_default_plan_same_numeric_domains(self):
  cat=HERE/'shelter_sources/canonical/generated/catalog.json';key='registered_precinct_r06_shelter_8x6';old=p.a.load(HERE/'shelter_sources/contact_plan'/f'{key}.plan.json');captured={}
  with patch.object(p.a,'write',side_effect=lambda path,value:captured.update(value)),patch.object(p,'HERE',HERE/'shelter_sources'):p.make(key,cat)
  for k in old:
   if k!='algorithm_sha256':self.assertEqual(old[k],captured[k],k)
  self.assertEqual(captured['selected_roof_binding']['roof_variant_asset_key'],key)
 def test_actual_bank_23_wood_placements(self):
  roof,choice=p.selected_roof('working_r01_bank_joinery',HERE/'bank_sources_r02/canonical/generated/catalog.json');self.assertEqual(choice['placement_count'],23);self.assertEqual(roof['asset_key'],'working_r01_bank_joinery__wood_shingle')

class Empty(unittest.TestCase):
 def setUp(self):
  self.source={'instances':[{'id':'bay'}],'components':[{'id':'wall','operations':[{'id':'wall','action':'paint'}]},{'id':'roof','operations':[{'id':'roof','action':'paint'}]}],'constraints':[{'id':'open_bay','kind':'empty_region','shape':{'kind':'box','min':[0,0,0],'max':[1,1,1]},'selector':{}}]};self.canonical=copy.deepcopy(self.source);self.contract={'patches':[]};self.proof={'source_roof_components':['roof']}
 def call(self):return e.source_proof(self.source,self.canonical,self.contract,self.proof)
 def test_valid(self):self.assertTrue(self.call()['original_instances_constraints_and_nonroof_components_exact'])
 def test_component_cut(self):
  self.source['components'][0]['operations'].append({'id':'door','action':'cut'})
  with self.assertRaises(AssertionError):self.call()
 def test_assembly_cut(self):
  self.source['assembly_cuts']=[{'id':'door'}]
  with self.assertRaises(AssertionError):self.call()
 def test_window_needs_depth_qa(self):
  self.contract['patches']=[{'id':'window'}]
  with self.assertRaises(AssertionError):self.call()
 def test_nonroof_changed(self):
  self.canonical['components'][0]['operations'][0]['id']='changed'
  with self.assertRaises(AssertionError):self.call()
 def test_constraint_changed(self):
  self.canonical['constraints'][0]['shape']['max'][0]=2
  with self.assertRaises(AssertionError):self.call()
 def test_transformed_constraint_unsupported(self):
  for m in [self.source,self.canonical]:m['constraints'][0]['transform']={'translation':[1,0,0]}
  with self.assertRaises(AssertionError):self.call()
 def test_actual_shelter(self):
  row=e.a.load(HERE/'shelter_sources/canonical/generated/catalog.json')['assets'][0];source=e.a.load(e.a.ROOT/row['source_master_path']);canonical=e.a.load(e.a.ROOT/row['emitted_master_path']);contract=e.a.load(e.a.ROOT/row['replacement_contract_path']);proof=e.a.load(e.a.ROOT/row['composition_proof_path']);self.assertTrue(e.source_proof(source,canonical,contract,proof)['original_instances_constraints_and_nonroof_components_exact'])
class Handoff(unittest.TestCase):
 def setUp(self):
  import compose_selected_variant_r01 as c
  self.c=c;self.cat={'asset_key':'native','source_sha256':'source','source_render_sha256':'render','roof_master_sha256':'roof'};self.row={'asset_key':'native','native_asset_key':'native','source_sha256':'source','source_render_sha256':'render','emitted_master_sha256':'roof','complete_authored_source_domain_coverage':True,'independent_qa':{'pass':True},'independent_replay':{'pass':True}}
 def test_default_object_identical(self):self.assertIs(self.c.select_roof_handoff(self.cat,{},self.row),self.row)
 def test_wrong_selected(self):
  with self.assertRaises(AssertionError):self.c.select_roof_handoff(self.cat,{'roof_variant_asset_key':'native__wood'},self.row)
 def test_duplicate(self):
  with self.assertRaises(AssertionError):self.c.select_roof_handoff(self.cat,{}, {'assets':[self.row,self.row]})
 def test_wrong_source(self):
  self.row['source_sha256']='changed'
  with self.assertRaises(AssertionError):self.c.select_roof_handoff(self.cat,{},self.row)
 def test_incomplete(self):
  self.row['complete_authored_source_domain_coverage']=False
  with self.assertRaises(AssertionError):self.c.select_roof_handoff(self.cat,{},self.row)
 def test_missing_replay(self):
  self.row['independent_replay']['pass']=False
  with self.assertRaises(AssertionError):self.c.select_roof_handoff(self.cat,{},self.row)
 def test_wood_authenticates_selector(self):
  self.row['asset_key']='native__wood';contract={'roof_variant_asset_key':'native__wood','roof_selector_path':'selector','roof_selector_sha256':'selectorhash','roof_covering':'wood_shingle'};choice={'native_asset_key':'native','selected_variant_asset_key':'native__wood','source_master_sha256':'source','roof_covering':'wood_shingle'}
  with patch.object(self.c.a,'sha',return_value='selectorhash'),patch.object(self.c.a,'load',return_value={'placements':[choice]}):self.assertIs(self.c.select_roof_handoff(self.cat,contract,self.row),self.row)
if __name__=='__main__':unittest.main()
