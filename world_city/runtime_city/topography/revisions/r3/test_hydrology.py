import copy
import json
import unittest
from .hydrology import CANDIDATE, validate

class HydrologyGraphTests(unittest.TestCase):
    def setUp(self): self.g=json.loads(CANDIDATE.read_text())
    def test_structural_candidate(self): self.assertTrue(validate(self.g)['passed'])
    def test_zero_building_conflicts(self): self.assertEqual(self.g['source_audit']['building_overlap_count'],0)
    def test_flat_river_rejected(self):
        option=next(x for x in self.g['alternatives'] if x['id']=='C')
        self.assertLess(option['intake_to_forebay_head_m'],0)
    def test_uphill_rejected(self):
        self.g['edges'][0]['profile_xyz_m'].insert(1,[0,100,0])
        self.assertFalse(validate(self.g)['passed'])
    def test_nonfinite_rejected(self):
        self.g['nodes'][0]['reference_y_m']=float('nan')
        self.assertFalse(validate(self.g)['passed'])
    def test_lift_requires_energy(self):
        e=next(e for e in self.g['edges'] if e['mode']=='manual_lift');e.pop('energy_source')
        self.assertFalse(validate(self.g)['passed'])
    def test_no_frozen_mutation(self): self.assertFalse(self.g['datum']['r2_modified'])
    def test_river_reference_explicit(self):
        self.assertEqual(self.g['datum']['frozen_r2_authored_river_surface_m'],-2)
        self.assertEqual(self.g['datum']['r3_river_design_reference_m'],-2.11)
if __name__=='__main__':unittest.main()
