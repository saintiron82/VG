"""Independent read-only clearance/cache checks for the finite landscape pack."""
import hashlib,json,math,unittest
from pathlib import Path
from . import recipes
from .resolve_approved import shape_sha
from world_city.runtime_city.checks.placement import convex_polygon_contains
HERE=Path(__file__).parent
CITY=HERE.parents[1]
class ResolvedLandscapeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pack=json.loads((HERE/'resolved_placements.json').read_text());cls.plan=json.loads((CITY/'source/plan.json').read_text());cls.proposal=json.loads((CITY/'source/proposed_landscape_sites.json').read_text());cls.sites={s['id']:s for s in cls.proposal['sites']};cls.records={s['source_ground_id']:s for s in cls.pack['site_records']};cls.exclusions={e['id']:e for e in cls.proposal['exclusion_catalog']}
    def test_exact_counts_and_missing_sites_are_explicit(self):
        self.assertEqual(self.pack['summary']['placements'],1274);self.assertEqual(self.pack['summary']['trees'],824);self.assertEqual(self.pack['summary']['garden_beds'],12);self.assertEqual({r['source_ground_id'] for r in self.pack['unresolved']},{'LAND_PUBLIC_COMMON','LAND_CLERGY_CEMETERY'});self.assertTrue(all(r['replacement_ids']==[] for r in self.pack['unresolved']))
    def test_all_render_files_and_source_aliases_are_verified(self):
        for key,a in self.pack['asset_manifest'].items():
            self.assertEqual(hashlib.sha256(Path(a['render_path']).read_bytes()).hexdigest(),a['render_sha256']);self.assertEqual(hashlib.sha256(Path(a['master_path']).read_bytes()).hexdigest(),a['master_file_sha256']);self.assertEqual(shape_sha(json.loads(Path(a['master_path']).read_text())),a['geometry_identity_ignoring_asset_id_sha256']);self.assertLessEqual(a['pitch_m'],a['recommended_pitch_m'])
    def test_every_actual_crown_clears_finite_ground_and_hard_exclusions(self):
        for p in self.pack['placements']:
            record=self.records[p['source_ground_id']];site=self.sites[p['source_ground_id']];poly=p['footprint_xz_m'];self.assertTrue(any(recipes.contains(q,poly) for q in record['generation_polygons_xz_m']),p['id'])
            for key in site['exclusion_ids']:self.assertFalse(recipes.overlaps(poly,self.exclusions[key]['polygon_xz_m']),(p['id'],key))
            if site['landscape_kind']=='outside_woodland':self.assertFalse(recipes.overlaps(poly,self.plan['boundary_xz_m']),p['id'])
            else:self.assertTrue(recipes.contains(self.plan['boundary_xz_m'],poly),p['id'])
    def test_cached_render_envelope_fits_validated_crown(self):
        for p in self.pack['placements']:
            a=self.pack['asset_manifest'][p['asset_key']];b=a['bounds'];x,y,z=p['position_m'];theta=p['yaw_rad'];actual=[[x+math.cos(theta)*u+math.sin(theta)*v,z-math.sin(theta)*u+math.cos(theta)*v] for u,v in [(b['min'][0],b['min'][2]),(b['max'][0],b['min'][2]),(b['max'][0],b['max'][2]),(b['min'][0],b['max'][2])]];self.assertTrue(convex_polygon_contains(p['footprint_xz_m'],actual,1e-7),p['id'])
    def test_root_projection_and_no_duplicate_estate_ownership(self):
        estates=[p['polygon_xz_m'] for p in self.plan['plots'] if p['property_type']=='noble_estate']
        for p in self.pack['placements']:
            support=p['terrain_support'];self.assertLessEqual(support['support_delta_m'],.750001);self.assertEqual(p['position_m'][1],support['samples_y_m'][0]);self.assertTrue(support['xz_unchanged']);self.assertFalse(support['crown_scaled']);self.assertTrue(all(not recipes.overlaps(p['footprint_xz_m'],e) for e in estates))
            if p['spec']['kind']=='forest_tree':self.assertAlmostEqual(recipes.polygon_area(p['ground_anchor']['support_points_xz_m']),4,places=5)
    def test_no_scene_compile_floor_or_frozen_source_mutation(self):
        self.assertEqual(self.pack['new_compilation_count'],0);self.assertTrue(self.pack['no_new_floor_planes']);self.assertFalse(self.pack['scene_integration_performed']);self.assertTrue(all(p['spec']['kind'] in ('forest_tree','understory','garden_bed') for p in self.pack['placements']))
        m=json.loads((HERE/'freeze_manifest.json').read_text())
        for path,h in m['all_files_sha256'].items():self.assertEqual(hashlib.sha256((HERE/path).read_bytes()).hexdigest(),h,path)
if __name__=='__main__':unittest.main()
