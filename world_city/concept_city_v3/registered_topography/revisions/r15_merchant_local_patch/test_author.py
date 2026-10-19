import json,math,unittest
from . import author as a

class LocalPatch(unittest.TestCase):
    def test_immutable_inputs(self):
        for p,h in a.REFERENCES.items():self.assertEqual(a.sha(a.CITY/p),h)
    def test_scope(self):
        self.assertEqual((len(a.PLATFORMS),len(a.GATES),len(a.NATIVE_HOLES),len(a.RETIRED)),(19,19,194,58))
        self.assertAlmostEqual(sum(a.geo.polygon_area(r['polygon_xz_m']) for r in a.PLATFORMS),21384.,7)
    def test_native_holes_are_finite_platform_interiors(self):
        byid={r['property_id']:r for r in a.PLATFORMS}
        for r in a.NATIVE_HOLES:
            outside=a.subtract([r['polygon_xz_m']],[byid[r['property_id']]['polygon_xz_m']])
            self.assertLess(sum(a.geo.polygon_area(p) for p in outside),1e-7)
    def test_untouched_triangle_identity(self):
        tri=[[1000.,2.,1000.],[1004.,4.,1000.],[1000.,6.,1004.]]
        result=a.clip_frozen_triangle(tri)
        self.assertTrue(result['unchanged']);self.assertIs(result['triangles_xyz_m'][0],tri)
    def test_clipped_triangle_original_plane_and_area(self):
        tri=[[0.,2.,0.],[4.,4.,0.],[0.,6.,4.]];mask=[[0.,0.],[1.,0.],[1.,1.],[0.,1.]]
        result=a.clip_frozen_triangle(tri,[mask]);self.assertFalse(result['unchanged'])
        self.assertAlmostEqual(result['removed_projected_area_m2'],1.,12)
        for t in result['triangles_xyz_m']:
            for x,y,z in t:self.assertAlmostEqual(y,2+.5*x+z,12)
            self.assertLess(a.geo.polygon_area(a.geo.convex_intersection([[v[0],v[2]] for v in t],mask)),1e-10)
    def test_overlap_masks_do_not_duplicate_cut(self):
        tri=[[0.,2.,0.],[4.,4.,0.],[0.,6.,4.]];m=[[0.,0.],[1.,0.],[1.,1.],[0.,1.]]
        once=a.clip_frozen_triangle(tri,[m]);twice=a.clip_frozen_triangle(tri,[m,m])
        self.assertAlmostEqual(once['removed_projected_area_m2'],twice['removed_projected_area_m2'],12)
    def test_vertical_side_separate(self):
        tri=[[0.,0.,0.],[0.,2.,0.],[4.,2.,0.]]
        result=a.clip_frozen_triangle(tri,[]);self.assertTrue(result['requires_side_review'])
        self.assertIs(result['triangles_xyz_m'][0],tri)
    def test_exact_side_interval(self):
        m=[[0.,0.],[1.,0.],[1.,1.],[0.,1.]]
        lo,hi=a.segment_mask_interval([-1.,.5],[2.,.5],m)
        self.assertAlmostEqual(lo,1/3);self.assertAlmostEqual(hi,2/3)
        self.assertIsNone(a.segment_mask_interval([-1.,2.],[2.,2.],m))
    def test_retired_domains_disjoint(self):
        index=a.geo._SpatialIndex(16);records=a.retired_owner_domains()
        self.assertTrue(records)
        for i,r in enumerate(records):
            p=r['polygon_xz_m']
            for j in index.candidates(p):self.assertLess(a.geo.polygon_area(a.geo.convex_intersection(p,records[j]['polygon_xz_m'])),1e-7)
            index.add(i,p)
    def test_restoration_disjoint_and_outside_new_owners(self):
        index=a.geo._SpatialIndex(16);records=a.restoration_domains();self.assertTrue(records)
        for i,r in enumerate(records):
            p=r['polygon_xz_m']
            for m in a.NEW_MASKS:self.assertLess(a.geo.polygon_area(a.geo.convex_intersection(p,m)),1e-7)
            for j in index.candidates(p):self.assertLess(a.geo.polygon_area(a.geo.convex_intersection(p,records[j]['polygon_xz_m'])),1e-7)
            index.add(i,p)
    def test_patch_union_preserves_water(self):
        water=a.base.finite_water_polygons();idx=a.geo._SpatialIndex(16)
        for i,r in enumerate(water):idx.add(i,r['polygon_xz_m'])
        for r in a.patch_masks():
            for i in idx.candidates(r['polygon_xz_m']):
                self.assertLess(a.geo.polygon_area(a.geo.convex_intersection(r['polygon_xz_m'],water[i]['polygon_xz_m'])),1e-7)
    def test_gate_source_grade_pending_r5(self):
        risks=a.gate_risk_screen();self.assertEqual(sum(r['needs_shared_public_transition'] for r in risks),11)
        for r in risks:
            self.assertLessEqual(r['source_triangle_max_grade'],.12)
            self.assertIsNone(r['final_frozen_triangle_seams'])
    def test_contract_cannot_claim_activation(self):
        d=json.loads((a.HERE/'source_contract.json').read_bytes())
        self.assertFalse(d['active']);self.assertIsNone(d['base_scene'])
        self.assertEqual(d['author_sha256'],a.sha(a.HERE/'author.py'))
        self.assertFalse(d['replacement_ledger']['render_components'])

if __name__=='__main__':unittest.main()
