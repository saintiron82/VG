"""Read-only source/ownership regressions for the finite E1/E2 cap correction."""
from author import *
import unittest, numpy as np


class SourceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.owners=load(OUT/'physical_owners.json')
        cls.top=load(OUT/'top_retirement_request.json')
        cls.sides=load(OUT/'side_retirement_requests.json')['requests']
        cls.patch=load(OUT/'finite_surface_patch.json')
        cls.report=load(OUT/'author_report.json')
        cls.profiles={r['owner_id']:r for r in load(N/'physical_profile_audit.json')['owners']}

    def test_bound_files(self):
        for r in [self.top['source_patch'],self.top['replacement_patch']]+[s['source_patch']for s in self.sides]:
            self.assertEqual(ref(ROOT/r['path']),r)

    def test_only_e1_e2_existing_solved_domains(self):
        self.assertEqual(set(o['owner_id']for o in self.owners['owners']),{'E1','E2'})
        for o in self.owners['owners']:
            p=self.profiles[o['owner_id']]['private_field_pieces'][o['selected_profile_piece_index']]
            self.assertEqual(o['plane_y_xz_m'],p['plane_y_xz_m'])
            self.assertLess(sum(fg.area(q)for q in fg.subtract([o['polygon_xz_m']],[p['polygon_xz_m']])),1e-9)

    def test_complete_disjoint_old_cap_partition(self):
        caps=self.report['cap_rows']
        self.assertEqual(len(caps),43)
        for cap in caps:
            self.assertAlmostEqual(cap['old_area_m2'],cap['new_area_m2']+cap['retained_old_area_m2'],places=8)
        owners=self.owners['owners'];ix=geo._SpatialIndex(1)
        for i,o in enumerate(owners):
            for j in ix.candidates(o['polygon_xz_m']):
                self.assertLess(fg.area(fg.clip(o['polygon_xz_m'],owners[j]['polygon_xz_m'])),1e-9)
            ix.add(i,o['polygon_xz_m'])

    def test_top_exact_indexed_replacements_and_other_arrays_unchanged(self):
        src=load(ROOT/self.top['source_patch']['path']);dst=load(ROOT/self.top['replacement_patch']['path'])
        rows={r['appended_triangle_index']:r for r in self.top['source_rows']};out=[]
        vs=src['appended_surfaces']['ground_stone']
        for i in range(len(vs)//3):
            t=vs[3*i:3*i+3]
            if i in rows:
                r=rows[i];self.assertEqual(tri_sha(t),r['source_triangle_sha256']);self.assertEqual(t,r['source_triangle_xyz_m'])
                out +=[v for tr in r['replacement_triangles_xyz_m']for v in tr]
            else:out+=t
        self.assertEqual(out,dst['appended_surfaces']['ground_stone'])
        self.assertEqual(src['surface_edits'],dst['surface_edits'])
        for k,v in src['appended_surfaces'].items():
            if k!='ground_stone':self.assertEqual(v,dst['appended_surfaces'][k])
        self.assertAlmostEqual(sum(r['removed_projection_area_m2']for r in rows.values()),self.report['new_floor_area_m2'],places=8)

    def test_side_source_and_exact_area_partitions(self):
        for request in self.sides:
            src=load(ROOT/request['source_patch']['path']);vs=src['appended_surfaces']['bank']
            self.assertEqual(tri_sha(vs),request['source_bank_array_sha256'])
            indices=[]
            for r in request['source_rows']:
                i=r['appended_triangle_index'];indices.append(i);t=vs[3*i:3*i+3]
                self.assertEqual(t,r['source_triangle_xyz_m']);self.assertEqual(tri_sha(t),r['source_triangle_sha256'])
                self.assertAlmostEqual(area3(t),sum(area3(x)for x in r['replacement_triangles_xyz_m'])+r['retired_area3_m2'],places=6)
            self.assertEqual(indices,sorted(set(indices)))

    def test_old_caps_absent_from_full_two_metre_routes(self):
        routes=load(OUT.parent/'noble_runtime_contact_review_r01/cap_route_overlap.json')['owners']
        rows=[]
        for route in routes:
            if route['owner_id']not in ('E1','E2'):continue
            masks=[o['polygon_xz_m']for o in self.owners['owners']if o['owner_id']==route['owner_id']]
            missing=0
            for cap in route['cap_contacts']:
                missing+=sum(fg.area(q)for q in fg.subtract(cap['route_intersection_polygons_xz_m'],masks))
            self.assertLess(missing,1e-8)
            retained=0
            for cap in self.owners['retained_old_cap_pieces']:
                for q in route['route_ribbon_polygons_xz_m']:
                    retained+=fg.area(fg.clip(q,cap['polygon_xz_m']))
            self.assertLess(retained,1e-8)
            rows.append(dict(owner_id=route['owner_id'],unreplaced_old_cap_route_area_m2=missing,retained_cap_route_overlap_m2=retained))
        write('route_cap_clearance.json',dict(status='PASS_FINITE_OLD_CAP_CLEARANCE',routes=rows,runtime_routes=ref(N/'runtime_routes.json'),runtime_ready=False))

    def test_no_public_or_native_floor_conflicts_and_closed_boundaries(self):
        self.assertFalse(self.report['existing_floor_conflicts'])
        boundary=load(OUT/'boundary_review.json')
        self.assertFalse(boundary['unknown_exterior_segments'])
        self.assertEqual(len(boundary['boundary_seams']),861)

    def test_emitted_floor_area_and_finite_source_winding(self):
        surfaces=self.patch['appended_surfaces'];area=0;precision=[]
        for mat,vs in surfaces.items():
            self.assertEqual(len(vs)%3,0)
            zero=[];reversed_projection=[]
            for i in range(len(vs)//3):
                t=vs[3*i:3*i+3];self.assertTrue(all(math.isfinite(v)for p in t for v in p));self.assertGreater(area3(t),0)
                if mat=='ground_stone':
                    self.assertGreater(terrain.normal_y(t),0);area+=fg.area(xz(t))
                f=np.asarray(t,dtype=np.float32);n=np.cross(f[1]-f[0],f[2]-f[0])
                if np.all(n==0):zero.append(i)
                elif mat=='ground_stone' and n[1]<=0:reversed_projection.append(i)
            precision.append(dict(material=mat,source_triangle_count=len(vs)//3,float32_exact_zero_indices=zero,nonzero_float32_reversed_top_indices=reversed_projection))
        self.assertAlmostEqual(area,self.report['new_floor_area_m2'],places=8)
        write('runtime_precision_diagnostic.json',dict(policy='Authored source retained. Parent exact-float32-zero runtime sanitation remains required; this is no runtime pass.',surfaces=precision))
        self.assertFalse([i for r in precision for i in r['nonzero_float32_reversed_top_indices']])


if __name__=='__main__':
    suite=unittest.defaultTestLoader.loadTestsFromTestCase(SourceTests)
    result=unittest.TextTestRunner(verbosity=2).run(suite)
    write('source_tests.json',dict(tests_run=result.testsRun,failures=len(result.failures),errors=len(result.errors),status='PASS'if result.wasSuccessful()else'FAIL',runtime_ready=False))
    raise SystemExit(0 if result.wasSuccessful() else 1)
