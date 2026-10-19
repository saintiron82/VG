import copy,json,unittest
from pathlib import Path
import revise_windows as w
import revise_variants as v
H=Path(__file__).resolve().parent
class WindowRevision(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.rules=w.load(H/'window_rules.v1.json');cls.variants=w.load(H/'window_variants.v2.json');cls.reports=[w.load(p) for p in (H/'generated/glazed_open_shutters').glob('*.candidate.json')]
 def pairs(self):
  for r in self.reports:yield r,w.load(w.a.ROOT/r['inputs']['original_source_path']),w.load(w.a.ROOT/r['inputs']['previous_near_path']),w.load(w.a.ROOT/r['files']['canonical']['path']),w.load(w.a.ROOT/r['files']['near']['path'])
 def test_two_representative_counts(self):self.assertEqual(sorted(r['window_count'] for r in self.reports),[17,47])
 def test_nonwindow_source_and_near_exact(self):
  for r,source,near,canonical,revised in self.pairs():
   for a,b in [(source,canonical),(near,revised)]:
    for ac,bc in zip(a['components'],b['components']):self.assertEqual([o for o in ac['operations'] if not w.is_window(o,self.rules)],[o for o in bc['operations'] if not w.is_window(o,self.rules)])
 def test_instances_materials_constraints_exact(self):
  for r,source,near,canonical,revised in self.pairs():
   for key in ('instances','materials','constraints','assembly_cuts'):self.assertEqual(source.get(key),canonical.get(key));self.assertEqual(near.get(key),revised.get(key))
 def test_near_operation_ids_preserved(self):
  for r,source,near,canonical,revised in self.pairs():
   for ac,bc in zip(near['components'],revised['components']):self.assertEqual([o['id'] for o in ac['operations']],[o['id'] for o in bc['operations']])
 def test_near_far_window_design_exact(self):
  for r,source,near,canonical,revised in self.pairs():
   for ac,bc in zip(canonical['components'],revised['components']):self.assertEqual({o['id']:o for o in ac['operations'] if w.is_window(o,self.rules)},{o['id']:o for o in bc['operations'] if w.is_window(o,self.rules)})
 def test_actual_frame_width_and_clear_gain(self):
  for r,source,near,canonical,revised in self.pairs():
   comps={c['id']:c for c in revised['components']}
   for row in r['windows']:
    op=next(o for o in comps[row['component_id']]['operations'] if o['id']==row['window_base']+'_left');lo,hi=w.rect(op);self.assertAlmostEqual(hi[0]-lo[0],.10);self.assertGreater(row['new_visible_glass_ratio_with_near_cross'],row['old_visible_glass_ratio_with_near_cross'])
 def test_unsupported_open_casement_refused(self):
  r,source,near,*_=next(self.pairs())
  with self.assertRaises(ValueError):w.revise(source,near,self.rules,'casement_open',{})
 def test_missing_frame_refused(self):
  r,source,near,*_=next(self.pairs());c=next(c for c in near['components'] if any(o['id']=='window_0_left' for o in c['operations']));c['operations']=[o for o in c['operations'] if o['id']!='window_0_left']
  with self.assertRaises(ValueError):w.revise_component(c,self.rules,'glazed_closed_shutters_open')
 def test_tiny_aperture_refused(self):
  r,source,near,*_=next(self.pairs());c=next(c for c in near['components'] if any(o['id']=='window_0_aperture' for o in c['operations']));op=next(o for o in c['operations'] if o['id']=='window_0_aperture');op['shape']['max'][0]=op['shape']['min'][0]+.15
  with self.assertRaises(ValueError):w.revise_component(c,self.rules,'glazed_closed_shutters_open')
 def test_closed_shutters_span_aperture(self):
  report=w.load(H/'generated/shutters_closed/ordinary_r2_5ab0065a8cd6bf.candidate.json');m=w.load(w.a.ROOT/report['files']['near']['path']);comps={c['id']:c for c in m['components']}
  for row in report['windows']:
   ops={o['id']:o for o in comps[row['component_id']]['operations']};name=row['window_base'];lo,hi=w.rect(ops[name+'_aperture']);left=ops.get(name+'__near_shutter_-1');right=ops.get(name+'__near_shutter_1')
   if left and right:self.assertAlmostEqual(w.rect(left)[0][0],lo[0]);self.assertAlmostEqual(w.rect(right)[1][0],hi[0]);self.assertAlmostEqual(w.rect(left)[1][0],w.rect(right)[0][0])
 def test_plaster_variant_separates_surround_and_sash(self):
  r=w.load(H/'generated/plaster_trim_recessed_wood/ordinary_r2_5ab0065a8cd6bf.candidate.json');m=w.load(w.a.ROOT/r['files']['near']['path']);c=next(c for c in m['components'] if any(o['id']=='window_0__casement_left' for o in c['operations']));ops={o['id']:o for o in c['operations']};self.assertEqual(ops['window_0_left']['material'],'plaster');self.assertEqual(ops['window_0__casement_left']['material'],'timber_dark');self.assertAlmostEqual(w.rect(ops['window_0__casement_left'])[1][0]-w.rect(ops['window_0__casement_left'])[0][0],.05)
 def test_all_50_house_types_in_inventory(self):
  r=w.load(H/'generated/house_window_inventory.r01.json');self.assertEqual(r['active_house_types'],50);self.assertEqual(r['recognized_windows_in_type_sources'],1915);self.assertEqual(r['pending_type_count'],0)
if __name__=='__main__':unittest.main(verbosity=2)
