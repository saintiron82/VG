"""Read-only checks on the approved noble common cache and placement pack."""
import hashlib,json,unittest
from pathlib import Path
from .resolver import sha
HERE=Path(__file__).parent
class ResolvedNobleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.pack=json.loads((HERE/'resolved_placements.json').read_text());cls.cache=json.loads((HERE/'cache/manifest.json').read_text())
    def test_exact_approved_scope_and_real_cache(self):
        self.assertEqual(self.pack['summary']['resolved_plots'],7);self.assertEqual(self.pack['summary']['instanced_placements'],133);self.assertEqual(len(self.cache['assets']),10);self.assertEqual(self.pack['cache_binding_status'],'all_required_render_files_verified');self.assertEqual(len(self.pack['deferred_recipe_compounds']),11)
    def test_every_cache_source_and_render_hash_verified(self):
        for key,a in self.cache['assets'].items():
            self.assertEqual(hashlib.sha256(Path(a['master_path']).read_bytes()).hexdigest(),a['master_file_sha256']);self.assertEqual(hashlib.sha256(Path(a['compiled_asset_ref']).read_bytes()).hexdigest(),a['render_sha256']);self.assertEqual(sha(json.loads(Path(a['master_path']).read_text())),a['master_source_sha256']);self.assertEqual(self.pack['asset_manifest'][key]['master_source_sha256'],a['master_source_sha256'])
    def test_one_floor_and_boundary_owner_per_compound(self):
        for r in self.pack['resolved_properties']:
            self.assertTrue(all(p['position_m'][1]==r['floor_y_m'] for p in r['placements']));self.assertEqual(sum(p['role']=='owned_surface' for p in r['placements']),1);self.assertEqual(sum(p['role']=='boundary' for p in r['placements']),1);self.assertTrue(r['surface_ownership']['city_terrain_must_exclude_this_footprint'])
    def test_replacement_ledger_is_exact_and_preserves_external_routes(self):
        self.assertEqual(sum(len(r['replacement_ledger']['replace_building_ids']) for r in self.pack['resolved_properties']),21);self.assertEqual(sum(len(r['replacement_ledger']['replace_internal_path_ids']) for r in self.pack['resolved_properties']),49)
        for r in self.pack['resolved_properties']:
            ledger=r['replacement_ledger'];self.assertFalse(set(ledger['preserve_external_path_ids'])&set(ledger['replace_internal_path_ids']));self.assertTrue(ledger['atomic_replacement_required'])
    def test_new_compile_scope_and_fixed_budgets(self):
        report=json.loads((HERE/'generated/resolver/cache_build_report.json').read_text());self.assertEqual(report['new_compilation_count'],10);self.assertEqual(report['status'],'complete')
        for r in report['results']:self.assertLessEqual(r['candidate_cells'],300000);self.assertLessEqual(r['output_cells'],100000)
    def test_frozen_prototype_and_resolver_sources_intact(self):
        for name,key in [('freeze_manifest.json','all_files_sha256'),('resolver.freeze_manifest.json','files_sha256')]:
            m=json.loads((HERE/name).read_text())
            for path,h in m[key].items():self.assertEqual(hashlib.sha256((HERE/path).read_bytes()).hexdigest(),h,path)
if __name__=='__main__':unittest.main()
