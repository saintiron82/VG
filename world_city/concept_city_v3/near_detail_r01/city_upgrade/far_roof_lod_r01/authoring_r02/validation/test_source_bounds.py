"""Small numerical safety fixtures; never samples or compiles a full asset."""
from pathlib import Path
import sys,json,math,unittest,copy,resource,time
sys.dont_write_bytecode=True
A=Path(__file__).resolve().parents[1];sys.path.insert(0,str(A))
import input_contract_r02 as ic
import source_bounds as b
C=ic.core;I=C.transform();box={'kind':'box','min':[-1,-1,-1],'max':[1,1,1]}
ann={'kind':'annulus','inner_radius':.9,'outer_radius':1,'y_min':-1,'y_max':1}
def bounds(shape=box,t=I,pitch=.5):return b.transformed_bounds(shape,t,pitch)
def contains(bb,p):return all(bb['min'][i]<=p[i]<=bb['max'][i]for i in range(3))
def shift(x):return C.transform({'translation':[x,0,0]})
class Guards(unittest.TestCase):
 def test_box_contains_original_corners(self):
  import itertools
  for p in itertools.product(*zip(box['min'],box['max'])):self.assertTrue(contains(bounds(),p))
 def test_annulus_hole_is_not_disjoint_box(self):
  # The real hole does not authorize accepting an uncertain bounding-box pair.
  tiny={'kind':'box','min':[-.1,-.1,-.1],'max':[.1,.1,.1]}
  self.assertFalse(b.strictly_disjoint(bounds(ann),bounds(tiny)))
 def test_lathe_contains_profile_samples(self):
  s={'kind':'lathe','profile':[[0,-1],[1,-1],[.5,1],[0,1]]};bb=bounds(s)
  for rad,y in s['profile']:
   for n in range(12):self.assertTrue(contains(bb,[rad*math.cos(n*math.pi/6),y,rad*math.sin(n*math.pi/6)]))
 def test_tube_radius_is_enclosed(self):
  s={'kind':'tube','points':[[-2,0,0],[3,1,2]],'radius':.1};bb=bounds(s)
  for p in s['points']:
   for axis in range(3):
    for sign in [-1,1]:q=p.copy();q[axis]+=sign*.1;self.assertTrue(contains(bb,q))
 def test_rotated_corners_enclosed(self):
  c=math.sqrt(.5);t=C.transform({'basis':[[c,0,c],[0,1,0],[-c,0,c]],'translation':[-1000000,5,-100]})
  bb=bounds(box,t)
  import itertools
  for p in itertools.product(*zip(box['min'],box['max'])):
   # Rational affine computation is authoritative; core float result can round
   # outwards by an ULP at enormous translation, covered here as an observation.
   self.assertTrue(contains(bb,C.apply(t,p)))
 def test_rotated_envelope_overlap_rejected(self):
  c=math.sqrt(.5);t=C.transform({'basis':[[c,0,c],[0,1,0],[-c,0,c]],'translation':[2.3,0,0]})
  self.assertFalse(b.strictly_disjoint(bounds(),bounds(ann,t)))
 def test_contact_rejected(self):self.assertFalse(b.strictly_disjoint(bounds(),bounds(box,shift(2))))
 def test_positive_overlap_rejected(self):self.assertFalse(b.strictly_disjoint(bounds(),bounds(box,shift(1.5))))
 def test_tiny_positive_overlap_rejected(self):self.assertFalse(b.strictly_disjoint(bounds(),bounds(box,shift(2-1e-12))))
 def test_positive_separation_accepted(self):self.assertTrue(b.strictly_disjoint(bounds(),bounds(box,shift(2+1e-10))))
 def test_uncertain_one_ulp_gap_rejected(self):self.assertFalse(b.strictly_disjoint(bounds(),bounds(box,shift(math.nextafter(2,math.inf)))))
 def test_shape_minimum_is_conservative(self):
  s={'kind':'tube','points':[[0,0,0],[0,1,0]],'radius':.01,'minimum_radius_cells':1};self.assertGreaterEqual(bounds(s)['max'][0],.5)
 def test_unknown_shape_refused(self):
  with self.assertRaises(ValueError):bounds({'kind':'sphere','radius':1})
 def test_nonfinite_refused(self):
  with self.assertRaises(ValueError):bounds({'kind':'box','min':[float('nan'),0,0],'max':[1,1,1]})
 def test_reflection_refused(self):
  with self.assertRaises(ValueError):bounds(box,{'basis':[[-1,0,0],[0,1,0],[0,0,1]]})
 def test_scale_refused(self):
  with self.assertRaises(ValueError):bounds(box,{'basis':[[2,0,0],[0,1,0],[0,0,1]]})
 def test_bad_pitch_refused(self):
  for p in [True,'0.5',0,-1,float('inf')]:
   with self.assertRaises(ValueError):bounds(pitch=p)
 def master(self,tx=2,selector=None):
  paint={'id':'roof','action':'paint','part':'solid','material':'slate','shape':box}
  cut={'id':'cut','action':'cut','part':'other','shape':box,'transform':{'translation':[tx,0,0]},'selector':selector or {}}
  return {'components':[{'id':'c','parts':[],'operations':[paint,cut]}],'instances':[{'id':'i','component':'c'}],'assembly_cuts':[]}
 def test_cut_contact_rejected(self):
  with self.assertRaisesRegex(ValueError,'ROOF_CUT_'):b.strict_cut_proofs(self.master(),ic.source_parts,.5,{'slate'})
 def test_component_cut_part_label_does_not_exclude(self):
  with self.assertRaisesRegex(ValueError,'ROOF_CUT_'):b.strict_cut_proofs(self.master(0),ic.source_parts,.5,{'slate'})
 def test_positive_cut_separation(self):self.assertEqual(len(b.strict_cut_proofs(self.master(3),ic.source_parts,.5,{'slate'})),1)
 def test_selector_exclusion_preserved(self):self.assertEqual(b.strict_cut_proofs(self.master(0,{'material':['wood']}),ic.source_parts,.5,{'slate'})[0]['exclusion'],'selector_excludes_roof_operation')
 def test_assembly_cut_scope(self):
  m=self.master(0);m['assembly_cuts']=[m['components'][0]['operations'].pop()]
  with self.assertRaisesRegex(ValueError,'ROOF_CUT_'):b.strict_cut_proofs(m,ic.source_parts,.5,{'slate'})

if __name__=='__main__':
 resource.setrlimit(resource.RLIMIT_AS,(256*1024*1024,)*2);resource.setrlimit(resource.RLIMIT_CPU,(90,)*2);start=time.monotonic()
 result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Guards))
 out={'all_pass':result.wasSuccessful(),'tests':result.testsRun,'failures':[(str(t),s)for t,s in result.failures],'errors':[(str(t),s)for t,s in result.errors],'seconds':time.monotonic()-start,'peak_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'address_space_limit_bytes':256*1024*1024}
 (A/'validation/source_bounds_fixtures.json').write_text(json.dumps(out,indent=2)+'\n');raise SystemExit(0 if result.wasSuccessful()else 1)
