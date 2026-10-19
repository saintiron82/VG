"""Bounded exact ownership/source checks. No runtime or voxel compilation."""
import unittest,math,hashlib
from . import author as a
from world_city.runtime_city.checks.placement import polygon_area,intersection_area

class OwnershipSourceTests(unittest.TestCase):
    def test_base_snapshot_is_unchanged(self):
        a._snapshot_check()
        self.assertEqual(a.base.SOURCE_PLAN_SHA256,a.BASE_SOURCE_SHA256)

    def test_six_poor_pads_have_finite_gate_and_road_clearance(self):
        chosen=[p for p in a.compound_candidates() if p['plot_id'] in a.ACCEPTED_POOR_IDS]
        self.assertEqual(len(chosen),6)
        for p in chosen:
            self.assertEqual(p['rejection_reasons'],[])
            self.assertLess(p['road_overlap_area_sum_m2'],1e-7)
            self.assertLess(p['water_overlap_area_m2'],1e-7)
            self.assertLessEqual(max(p['maximum_fill_m'],p['maximum_cut_m']),2)
            self.assertLess(p['foundation_bottom_y_m'],min(p['floor_y_m'],*p['sampled_source_ground_range_m']))
            for g in p['gate_ledger']:
                self.assertLess(g['full_width_sampled_delta_max_m'],1e-7)
                self.assertAlmostEqual(a.land_height_at(*g['xz_m']),p['floor_y_m'])

    def test_five_large_or_crossfall_candidates_remain_rejected(self):
        rejected=[p for p in a.compound_candidates() if p['plot_id'] not in a.ACCEPTED_POOR_IDS]
        self.assertEqual(len(rejected),5)
        for p in rejected:
            self.assertTrue(p['rejection_reasons'])
            if p['property_type']=='merchant_court':self.assertEqual(len(p['gate_ledger']),3)

    def test_bounded_domains_partition_the_tile(self):
        for bounds in [[-16,-384,16,-352],[112,272,144,304],[-360,40,-328,72]]:
            domains=a.surface_domains(bounds)
            self.assertAlmostEqual(sum(polygon_area(d['polygon_xz_m']) for d in domains),1024,places=6)
            for i,p in enumerate(domains):
                self.assertGreater(polygon_area(p['polygon_xz_m']),1e-8)
                for q in domains[i+1:]:self.assertLess(intersection_area(p['polygon_xz_m'],q['polygon_xz_m']),1e-7)

    def test_shared_owner_boundary_heights_are_identical(self):
        left=a.surface_domains([-16,-384,0,-352]);right=a.surface_domains([0,-384,16,-352])
        for z in [-383.5,-379.5,-375.5,-371.5,-367.5,-363.5,-359.5,-355.5]:
            l=[p for p in left if a.base._inside(0,z,p['polygon_xz_m'])]
            r=[p for p in right if a.base._inside(0,z,p['polygon_xz_m'])]
            matching=[(p,q) for p in l for q in r if p['owner_id']==q['owner_id'] and p['kind']==q['kind']]
            self.assertTrue(matching)
            for p,q in matching:self.assertAlmostEqual(a.surface_height_at(p,0,z),a.surface_height_at(q,0,z),places=9)

    def test_feeder_has_underwater_bed_and_complete_bank_support(self):
        s=a.channel_support_domains()
        self.assertTrue(s['beds']);self.assertTrue(s['exterior_banks'])
        for bed in s['beds']:
            for p,y in zip(bed['polygon_xz_m'],bed['vertex_y_m']):
                self.assertAlmostEqual(a.water_height_at('SPRING_FEEDER',*p)-y,.6,places=9)
        for bank in s['exterior_banks']:
            self.assertGreater(math.dist(bank['from_xz_m'],bank['to_xz_m']),1e-8)
            for bottom,top in zip(bank['bottom_y_m'],bank['top_y_m']):self.assertGreater(top,bottom)
        join=s['bed_depth_interfaces'][0]
        self.assertEqual(join['head_drop_m'],0)
        self.assertLess(join['top_y_m'],join['water_y_m'])
        self.assertLess(join['bottom_y_m'],join['top_y_m'])

    def test_budget_keeps_fine_caps_bounded(self):
        p=a.voxel_stage_plan();c=p['counts']
        self.assertEqual(p['grid_origin_m'],[0,0,0]);self.assertEqual(p['chunk_span_m'],32)
        self.assertLess(c['selected_review_fine_cap_cells_upper_bound'],500000)
        self.assertLess(c['selected_review_fine_patch_area_upper_bound_m2'],2000)
        self.assertGreater(c['full_network_thick_2_5m_micro_fill_cells_upper_bound_rejected'],400000000)

if __name__=='__main__':unittest.main()
