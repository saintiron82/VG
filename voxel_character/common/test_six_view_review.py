import unittest,tempfile,hashlib,copy
from pathlib import Path
from six_view_review import validate,VIEWS,TOPICS
class SixViewTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name);p=self.root/'fixture';p.write_bytes(b'unit fixture');ref={'path':'fixture','sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
  self.r={'schema':'riverstone.six_view_review.v1','source_render':ref,'reviewer':'independent','actual_images_opened':True,'views':[]}
  for v,n in VIEWS.items():
   self.r['views'].append({'view':v,'image':ref,'capture_report':ref,'engine':'Godot','projection':'orthographic','source_render_sha256':ref['sha256'],'camera':{'position':[x*30 for x in n],'target':[0,0,0],'up':[0,0,1] if v in ('top','bottom') else [0,1,0],'size_m':18},'reference_status':'measured_reference','reference_image':ref,'comparison':ref,'alignment_pass':True,'observations':[{'topic':t,'status':'pass','reason':'unit fixture'} for t in TOPICS]})
 def tearDown(self):self.tmp.cleanup()
 def test_complete(self):self.assertTrue(validate(self.r,self.root)['all_pass'])
 def test_every_view_required(self):
  for v in VIEWS:
   r=copy.deepcopy(self.r);r['views']=[x for x in r['views'] if x['view']!=v];self.assertFalse(validate(r,self.root)['all_pass'],v)
 def test_perspective_top_rejected(self):
  self.r['views'][4]['projection']='perspective';self.assertFalse(validate(self.r,self.root)['all_pass'])
 def test_wrong_axis_rejected(self):
  self.r['views'][4]['camera']['position']=[0,0,30];self.assertFalse(validate(self.r,self.root)['all_pass'])
 def test_concept_rejected(self):
  self.r['views'][0]['engine']='imagegen';self.assertFalse(validate(self.r,self.root)['all_pass'])
 def test_stale_source_rejected(self):
  self.r['views'][0]['source_render_sha256']='stale';self.assertFalse(validate(self.r,self.root)['all_pass'])
 def test_design_only_not_measured_pass(self):
  row=self.r['views'][-1];row.update(reference_status='design_section_only',design_contract=self.r['source_render'],inference_basis='Unseen underside is inferred');v=validate(self.r,self.root);self.assertTrue(v['evidence_complete']);self.assertFalse(v['all_pass']);self.assertEqual(v['design_only_views'],['bottom'])
 def test_unknown_and_conflict_rejected(self):
  for status in ('unavailable','contradictory'):
   self.r['views'][4]['reference_status']=status;self.assertFalse(validate(self.r,self.root)['all_pass'])
 def test_unresolved_detail_rejected(self):
  self.r['views'][0]['observations'][0]['status']='pending';self.assertFalse(validate(self.r,self.root)['all_pass'])
 def test_hash_change_rejected(self):
  (self.root/'fixture').write_bytes(b'changed');self.assertFalse(validate(self.r,self.root)['all_pass'])
 def test_bad_alignment_rejected(self):
  self.r['views'][0]['alignment_pass']=False;self.assertFalse(validate(self.r,self.root)['all_pass'])
 def test_duplicate_view_rejected(self):
  self.r['views'].append(self.r['views'][0]);self.assertFalse(validate(self.r,self.root)['all_pass'])
if __name__=='__main__':unittest.main()
