import copy,hashlib,json,tempfile,unittest
from pathlib import Path
from validate_visual_review import validate,VIEWS,TOPICS

class ReviewClosureTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
  (self.root/'evidence.bin').write_bytes(b'fixture source and render')
  ref={'path':'evidence.bin','sha256':hashlib.sha256((self.root/'evidence.bin').read_bytes()).hexdigest()}
  self.report={'schema':'riverstone.actual_visual_promotion.v1','candidate_id':'unit_fixture','author':'author','source_master':ref,'design_contract':ref,'source_render':ref,'reference_guide':ref,'reference_photos':[ref],'actual_renders':[{'view':v,'image':ref,'capture_report':ref,'engine':'Godot','kind':'actual_voxel_scene','source_render_sha256':ref['sha256'],'camera':{'position':[1,2,3],'target':[0,0,0],'fov':45}} for v in VIEWS],'independent_critique':{'reviewer':'independent','actual_images_opened':True,'observations':[{'topic':t,'status':'pass','reason':'unit fixture only'}for t in TOPICS]},'unresolved_issues':[],'functional_tests':{n:{'evidence':ref,'pass':True}for n in ('source_dimensions','entrance_to_public_road','balcony_door_to_deck','clearance_and_plot','lod_and_cache','collision_scope')},'status':'approved_representative'}
  from six_view_review import VIEWS as AXES,TOPICS as ST
  six={'schema':'riverstone.six_view_review.v1','source_render':ref,'reviewer':'independent','actual_images_opened':True,'views':[{'view':v,'image':ref,'capture_report':ref,'engine':'Godot','projection':'orthographic','source_render_sha256':ref['sha256'],'camera':{'position':[x*30 for x in n],'target':[0,0,0],'up':[0,0,1] if v in ('top','bottom') else [0,1,0],'size_m':18},'reference_status':'measured_reference','reference_image':ref,'comparison':ref,'alignment_pass':True,'observations':[{'topic':t,'status':'pass','reason':'unit fixture'} for t in ST]}for v,n in AXES.items()]}
  f=self.root/'six.json';f.write_text(json.dumps(six));self.report['six_view_review']={'path':'six.json','sha256':hashlib.sha256(f.read_bytes()).hexdigest()}
 def tearDown(self):self.temp.cleanup()
 def test_complete_fixture(self):self.assertTrue(validate(self.report,self.root)['all_pass'])
 def test_missing_six_view_closure_rejected(self):
  self.report.pop('six_view_review');self.assertFalse(validate(self.report,self.root)['all_pass'])
 def test_old_source_rejected(self):
  self.report['actual_renders'][0]['source_render_sha256']='stale';self.assertFalse(validate(self.report,self.root)['all_pass'])
 def test_concept_substitution_rejected(self):
  self.report['actual_renders'][0]['kind']='imagegen_concept';self.assertFalse(validate(self.report,self.root)['all_pass'])
 def test_nonindependent_review_rejected(self):
  self.report['independent_critique']['reviewer']='author';self.assertFalse(validate(self.report,self.root)['all_pass'])
 def test_pending_clearance_rejected(self):
  self.report['functional_tests']['clearance_and_plot']['pass']=False;self.assertFalse(validate(self.report,self.root)['all_pass'])
 def test_unresolved_issue_rejected(self):
  self.report['unresolved_issues']=['window too thick'];self.assertFalse(validate(self.report,self.root)['all_pass'])
 def test_mutated_file_rejected(self):
  (self.root/'evidence.bin').write_bytes(b'changed');self.assertFalse(validate(self.report,self.root)['all_pass'])
 def test_missing_view_rejected(self):
  self.report['actual_renders'].pop();self.assertFalse(validate(self.report,self.root)['all_pass'])
 def test_unjustified_notapplicable_rejected(self):
  self.report['independent_critique']['observations'][0]['status']='not_applicable';self.assertFalse(validate(self.report,self.root)['all_pass'])

if __name__=='__main__':unittest.main()
