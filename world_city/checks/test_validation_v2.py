import unittest, json, copy, importlib.util
from pathlib import Path
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('validate_layout',HERE/'validate_layout_v2.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class PlanChecks(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.plan=json.loads((HERE.parent/'data/city_brief.v2.json').read_text())
 def test_real_plan(self):self.assertTrue(m.validate(self.plan)['passed'])
 def test_duplicate_building_rejected(self):
  p=copy.deepcopy(self.plan);p['building_plans'][1]['id']=p['building_plans'][0]['id'];self.assertIn('unique_building_ids',m.validate(p)['errors'])
 def test_invalid_tier_rejected(self):
  p=copy.deepcopy(self.plan);p['building_plans'][10]['implementation_tier']='fully_built';self.assertIn('implementation_tiers',m.validate(p)['errors'])
 def test_displaced_entrance_rejected(self):
  p=copy.deepcopy(self.plan);p['building_plans'][10]['entrance']['position_xz_m']=[9999,9999];self.assertIn('entrances_on_footprint_edges',m.validate(p)['errors'])
 def test_wrong_source_hash_rejected(self):
  p=copy.deepcopy(self.plan);p['source_references']['assets'][0]['sha256']='0'*64;self.assertIn('source_reference_hashes',m.validate(p)['errors'])
def unused():pass

class WallChecks(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  from check_wall_crossings_v2 import check_wall
  cls.check=staticmethod(check_wall);cls.plan=json.loads((HERE.parent/'data/city_brief.v2.json').read_text())
 def test_real_wall_connections(self):self.assertTrue(self.check(self.plan)['passed'])
 def test_undersized_gate_reservation_rejected(self):
  p=copy.deepcopy(self.plan)
  for b in p['building_plans']:
   if b['functional_role']=='gatehouse':b['opening_required_m']['width']=.2
  self.assertFalse(self.check(p)['passed'])
 def test_missing_water_postern_rejected(self):
  p=copy.deepcopy(self.plan);p['site_features']=[f for f in p['site_features']if f['id']!='F_WATER_GATE_west'];self.assertFalse(self.check(p)['passed'])
if __name__=='__main__':unittest.main()
