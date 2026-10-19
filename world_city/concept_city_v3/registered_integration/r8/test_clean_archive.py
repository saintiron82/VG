"""Synthetic archive checks: no original data and no disk cleanup required."""
import hashlib,io,json,unittest,zipfile
from .check_clean_archive import extraction_selection
class ClosureTests(unittest.TestCase):
 def fixture(self,change=None):
  values={'build.py':b'# code\n','scene.json':b'{}','binding.json':b'{}','needed.json':b'[]','old_failed_scene.json':b'{"historical":true}'}
  ref=lambda n:{'path':n,'sha256':hashlib.sha256(values[n]).hexdigest()}
  m={'actual_scene':ref('scene.json'),'authored_scene':ref('scene.json'),'build_binding':ref('binding.json')}
  c={'schema':'riverstone.scene_build_read_closure.v1','authored_scene':m['authored_scene'],'build_binding':m['build_binding'],'files':{'needed.json':ref('needed.json')['sha256']}}
  values['closure.json']=json.dumps(c).encode();m['clean_extract_closure']=ref('closure.json');m['files']={n:hashlib.sha256(v).hexdigest()for n,v in values.items()}
  if change:change(values,m)
  f=io.BytesIO()
  with zipfile.ZipFile(f,'w')as z:
   for n,v in values.items():z.writestr(n,v)
   z.writestr('INTEGRATED_R8_MANIFEST.json',json.dumps(m))
  f.seek(0);return zipfile.ZipFile(f),m
 def test_history_kept_in_archive_not_second_extraction(self):
  z,m=self.fixture()
  with z:selected,policy=extraction_selection(z,m)
  self.assertIn('needed.json',selected);self.assertIn('build.py',selected);self.assertNotIn('old_failed_scene.json',selected);self.assertIn('old_failed_scene.json',m['files'])
 def test_unselected_history_is_also_checked(self):
  z,m=self.fixture(lambda v,m:v.update({'old_failed_scene.json':b'changed'}))
  with z,self.assertRaisesRegex(ValueError,'Archived bytes differ'):extraction_selection(z,m)
 def test_unmanifested_entry_rejected(self):
  z,m=self.fixture(lambda v,m:v.update({'extra.json':b'{}'}))
  with z,self.assertRaisesRegex(ValueError,'coverage mismatch'):extraction_selection(z,m)
 def test_unbound_closure_rejected(self):
  z,m=self.fixture(lambda v,m:m['clean_extract_closure'].update(sha256='bad'))
  with z,self.assertRaisesRegex(ValueError,'Unbound dependency'):extraction_selection(z,m)
 def test_legacy_complete_extraction(self):
  z,m=self.fixture(lambda v,m:m.pop('clean_extract_closure'))
  with z:selected,policy=extraction_selection(z,m)
  self.assertEqual(selected,set(m['files']));self.assertEqual(policy,'complete_archive_extraction')
 def test_winding_chain_includes_precise_scene_and_contract(self):
  def add(v,m):
   ref=lambda n:{'path':n,'sha256':hashlib.sha256(v[n]).hexdigest()}
   v['precision_scene.json']=b'{}';v['winding_contract.json']=b'{}'
   ledger={'source_scene':ref('precision_scene.json'),'derived_scene':ref('scene.json'),'implementation_refs':[ref('build.py'),ref('winding_contract.json')]}
   v['winding.json']=json.dumps(ledger).encode();m['runtime_winding_ledger']=ref('winding.json');m['files']={n:hashlib.sha256(x).hexdigest()for n,x in v.items()}
  z,m=self.fixture(add)
  with z:selected,policy=extraction_selection(z,m)
  self.assertTrue({'precision_scene.json','winding_contract.json','winding.json','build.py'}<=selected)
 def test_explicit_runtime_scripts_are_bytes_not_json(self):
  def add(v,m):
   v['Runtime.gd']=b'extends Node3D\n';c=json.loads(v['closure.json']);c['additional_runtime_dependencies']=[{'path':'Runtime.gd','sha256':hashlib.sha256(v['Runtime.gd']).hexdigest()}]
   v['closure.json']=json.dumps(c).encode();m['clean_extract_closure']['sha256']=hashlib.sha256(v['closure.json']).hexdigest();m['files']={n:hashlib.sha256(x).hexdigest()for n,x in v.items()}
  z,m=self.fixture(add)
  with z:selected,policy=extraction_selection(z,m)
  self.assertIn('Runtime.gd',selected)
 def test_changed_explicit_runtime_dependency_rejected(self):
  def add(v,m):
   c=json.loads(v['closure.json']);c['additional_runtime_dependencies']=[{'path':'needed.json','sha256':'wrong'}]
   v['closure.json']=json.dumps(c).encode();m['clean_extract_closure']['sha256']=hashlib.sha256(v['closure.json']).hexdigest();m['files']={n:hashlib.sha256(x).hexdigest()for n,x in v.items()}
  z,m=self.fixture(add)
  with z,self.assertRaisesRegex(ValueError,'Unbound runtime dependency'):extraction_selection(z,m)
if __name__=='__main__':unittest.main()
