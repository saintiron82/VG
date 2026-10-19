import copy,json,unittest
from .recipes import *
from world_city.concept_city_v3.assemblies.property.recipes import build_property_recipe,example_plot

class LandscapeRecipeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.wall=json.loads(Path('world_city/concept_city_v3/source/plan.json').read_text())['boundary_xz_m']
        cls.sites=examples(cls.wall)
        cls.recipes={p['landscape_kind']:build_landscape_recipe(p,cls.wall) for p in cls.sites}
    def test_all_bounded_source_recipes_valid(self):
        for r in self.recipes.values():self.assertTrue(r['checks']['valid'],r['checks']['errors']);self.assertTrue(r['no_citywide_placement'])
    def test_deterministic_source_recipe(self):
        self.assertEqual(self.recipes['outside_woodland'],build_landscape_recipe(self.sites[0],self.wall))
    def test_six_actual_forest_shapes_heights_and_wooded_core(self):
        m=self.recipes['outside_woodland']['metrics'];self.assertEqual(len(m['tree_forms']),6);self.assertEqual(m['actual_geometry_height_range_m'],[8,17]);self.assertGreater(m['nearest_trunk_spacing_cv'],.15);self.assertGreater(max(c['rounded_canopy_fraction'] for c in m['wooded_core_windows']),.4)
    def test_clearings_have_full_canopy_and_understory_clearance(self):
        r=self.recipes['outside_woodland'];clearing=[e for e in r['exclusions'] if ':clearing:' in e['id']];self.assertTrue(clearing)
        for p in r['placements']:self.assertFalse(any(overlaps(p['footprint_xz_m'],e['polygon_xz_m']) for e in clearing))
    def test_existing_building_and_path_exclusions_are_respected(self):
        ex=[{'id':'reserved_external_path','polygon_xz_m':rect([-585,-245],130,8)}];r=build_landscape_recipe(self.sites[0],self.wall,ex);self.assertTrue(r['checks']['valid'],r['checks']['errors'])
        self.assertTrue(all(not overlaps(p['footprint_xz_m'],ex[0]['polygon_xz_m']) for p in r['placements']))
    def test_inside_wall_forest_is_rejected(self):
        s=copy.deepcopy(self.sites[0]);s['polygon_xz_m']=rect([0,0],100,100)
        with self.assertRaises(ValueError):build_landscape_recipe(s,self.wall)
    def test_outside_wall_garden_is_rejected(self):
        s=copy.deepcopy(self.sites[1]);s['polygon_xz_m']=self.sites[0]['polygon_xz_m']
        with self.assertRaises(ValueError):build_landscape_recipe(s,self.wall)
    def test_orchard_requires_productive_ground(self):
        s=copy.deepcopy(self.sites[2]);s['productive_ground']=False
        with self.assertRaises(ValueError):build_landscape_recipe(s,self.wall)
    def test_all_trees_use_roots_not_crown_for_support(self):
        for r in self.recipes.values():
            for p in r['placements']:
                if p['spec']['kind']=='forest_tree':self.assertAlmostEqual(polygon_area(p['ground_anchor']['support_points_xz_m']),4);self.assertEqual(p['ground_anchor']['support_footprint_kind'],'trunk_root');self.assertNotIn('scale',p)
    def test_source_master_is_frozen_reuse_and_has_no_new_generator(self):
        cache={}
        for r in self.recipes.values():cache.update(r['master_specs'])
        self.assertEqual(len(cache),8)
        for key,s in cache.items():
            m=make_asset_master(s);self.assertEqual(m,make_master(s));self.assertEqual(m['id'],key);self.assertEqual(m['schema'],'riverstone.voxel.master.v1');self.assertEqual(len(m['components'][0]['parts']),1)
    def test_distinct_programs_and_no_duplicate_floor(self):
        f=self.recipes['outside_woodland'];park=self.recipes['public_park'];orchard=self.recipes['productive_orchard'];mon=self.recipes['monastery_garden'];clergy=self.recipes['clergy_garden']
        self.assertGreater(f['metrics']['understory'],0);self.assertEqual(park['metrics']['understory'],0);self.assertLess(park['metrics']['rounded_crown_projection_union_fraction_2m_samples'],.2);self.assertEqual(orchard['metrics']['nearest_trunk_spacing_cv'],0)
        self.assertEqual(sum(p['spec']['kind']=='garden_bed' for p in mon['placements']),8);self.assertEqual(sum(p['spec']['kind']=='garden_bed' for p in clergy['placements']),4)
        for r in self.recipes.values():self.assertTrue(all(p['spec']['kind'] not in ('court_paving','owned_surface') for p in r['placements']))
    def test_estate_garden_reuses_existing_owner_without_new_placement(self):
        p=build_property_recipe(example_plot('noble_estate'));r=build_landscape_recipe({'id':'ESTATE_GARDEN_BINDING','landscape_kind':'estate_garden'},self.wall,property_recipe=p);self.assertEqual(r['placements'],[]);self.assertEqual(len(r['existing_owner_bindings']),14);self.assertEqual(r['floor_owner'],p['surface_ownership']['owner_placement_id'])
    def test_formal_frame_minimum_is_buildable_and_smaller_is_rejected(self):
        for kind in ('monastery_garden','clergy_garden'):
            s={'id':'MINIMUM_'+kind,'landscape_kind':kind,'polygon_xz_m':rect([0,0],40,40),'width_m':40,'depth_m':40}
            r=build_landscape_recipe(s,self.wall);self.assertTrue(r['checks']['valid'],r['checks']['errors']);s.update(width_m=32,depth_m=32)
            with self.assertRaises(ValueError):build_landscape_recipe(s,self.wall)
    def test_stale_footprint_and_bad_root_anchor_detected(self):
        r=copy.deepcopy(self.recipes['outside_woodland']);p=r['placements'][0];p['position_m'][0]+=20;p['ground_anchor']['support_points_xz_m']=p['footprint_xz_m'];checks={e['check'] for e in validate_recipe(r)['errors']};self.assertIn('stale_footprint',checks);self.assertIn('canopy_used_as_root_support',checks)
if __name__=='__main__':unittest.main()
