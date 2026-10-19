import copy,json,pathlib,unittest
import catalog,private_emission_revision
H=pathlib.Path(__file__).resolve().parent
class NobleR06CatalogTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.old=json.loads((H/'route_catalog_61_ready_r05.json').read_bytes());cls.new=json.loads((H/'route_catalog_61_noble_r06.json').read_bytes());cls.expanded=catalog.validate(cls.new)
 def test_all_412_vectors_and_ids_preserved(self):
  self.assertEqual(len(self.expanded),412);self.assertEqual([(r['id'],r['points_xyz_m'])for r in self.old['routes']],[(r['id'],r['points_xyz_m'])for r in self.new['routes']])
 def test_seven_native_pack_sets(self):self.assertEqual(len(self.new['activation_requirements']['native_packs']),7)
 def test_seven_exact_noble_contracts(self):
  refs=self.new['activation_requirements']['collision_contracts'];self.assertEqual(len(refs),7);self.assertEqual(len({json.loads(catalog.source(r).read_bytes())['id']for r in refs}),7)
 def test_e3_retained_source(self):
  self.assertEqual(self.old['sources']['noble_physical_top_E3'],self.new['sources']['noble_physical_top_E3']);self.assertEqual(self.old['sources']['noble_contract_E3'],self.new['sources']['noble_contract_E3'])
 def test_nonnoble_records_exact(self):
  self.assertEqual([r for r in self.old['routes']if not r['id'].startswith('NOBLE:')],[r for r in self.new['routes']if not r['id'].startswith('NOBLE:')])
 def test_public_emission_and_owner_status_unchanged(self):
  self.assertEqual(self.old['activation_requirements']['finite_public_field'],self.new['activation_requirements']['finite_public_field']);self.assertEqual(self.old['coverage'],self.new['coverage'])
 def test_exact_foundation_revision(self):
  r=self.new['activation_requirements']['private_append_revisions'][0];old=json.loads(catalog.source(r['previous']).read_bytes());new=json.loads(catalog.source(r['current']).read_bytes());review=json.loads(catalog.source(r['review']).read_bytes());contract=json.loads(catalog.source(r['contract']).read_bytes());edge=contract['boundary_connection'];p=private_emission_revision.validate(old,new,review,{edge['material']:edge['triangles_xyz_m']});self.assertIn(r['current'],self.new['activation_requirements']['appended_surface_patches']);self.assertNotIn(r['previous'],self.new['activation_requirements']['appended_surface_patches'])
 def test_corrected_fixture_count_and_cemetery_retirement(self):
  p=json.loads(catalog.source(self.new['sources']['corrected_835_native_pack']).read_bytes());self.assertEqual(len(p['placements']),835);c=json.loads(catalog.source(self.new['sources']['cemetery_r03_native_pack']).read_bytes());self.assertEqual(c['replacement_ledger']['existing_native_placements_removed'],['REGISTERED_LANDSCAPE:SITE_CEMETERY'])
if __name__=='__main__':unittest.main()
