import copy,hashlib,json,unittest
from pathlib import Path
from parts_v1 import ROOT
from registration_gate_v1 import validate_registration_binding,template_affine
from measurements_v1 import pixel_world
HERE=Path(__file__).resolve().parent;REF=ROOT/'world_city/reference/house_quality_photos_20261019/six_views_r01'
def ref(p):return {'path':str(p.relative_to(ROOT)),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
class Gate(unittest.TestCase):
 def test_actual_rejected_generated_sheet_refused(self):
  data={'grid_template':ref(REF/'template.json'),'registration_report':ref(REF/'registration_r01.json')}
  with self.assertRaisesRegex(ValueError,'registration failed'):validate_registration_binding(data,ROOT)
 def test_six_view_exact_template_axes(self):
  t=json.load(open(REF/'template.json'))
  for name,v in t['views'].items():
   m=template_affine(t,name);x0,y0,x1,y1=v['grid_bounds_px'];view={'size_px':t['canvas_px'],'pixel_to_world_3x3':m};a=pixel_world(view,[x0,y1]);b=pixel_world(view,[x1,y0]);delta=[b[j]-a[j] for j in range(3)];axes=v['projection_axes']
   for j,spec in enumerate(axes):self.assertAlmostEqual(delta['XYZ'.index(spec[1])],(1 if spec[0]=='+' else -1)*v['span_m'][j])
 def test_template_scale_mismatch_rejected(self):
  t=json.load(open(REF/'template.json'));t['views']['front']['pixels_per_meter']=31
  with self.assertRaises(ValueError):template_affine(t,'front')
 def test_unregistered_image_hash_rejected(self):
  # Production report is actually rejected already. It may never be repaired
  # in a test to create a fake passing input or a production source.
  report=json.load(open(REF/'registration_r01.json'));self.assertFalse(report['registration_pass']);self.assertGreater(report['max_error_px'],2)
if __name__=='__main__':
 r=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Gate));(HERE/'registration_gate_tests.r01.json').write_text(json.dumps({'tests':r.testsRun,'all_pass':r.wasSuccessful(),'actual_failed_sheet_refused':True,'sampling_calls':0},indent=2)+'\n');raise SystemExit(not r.wasSuccessful())
