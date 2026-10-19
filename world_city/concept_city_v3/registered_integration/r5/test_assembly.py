import unittest,json
from pathlib import Path
from .assemble import build,CITY,ROOT,sha
class AssemblyTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.d=build();cls.base=json.loads((CITY/'registered_integration/r4/corrected_visual_candidate.json').read_bytes())
 def test_unique_and_rigid(self):
  d=self.d;ids=[p['id'] for p in d['common_instances']];self.assertEqual(len(ids),len(set(ids)));self.assertTrue(all(p['scale']==[1,1,1] for p in d['common_instances']))
 def test_all_sources_and_caches_bound(self):
  for a in self.d['common_assets'].values():
   for k in ('master','render'):self.assertEqual(sha(ROOT/a[k+'_path']),a[k+'_sha256'])
 def test_exact_atomic_retirements(self):
  pack=json.loads((CITY/'assemblies/property/registered/merchant_block011/resolved_placements.json').read_bytes());old={p['id']:p for p in self.base['common_instances']};new={p['id']:p for p in self.d['common_instances']};retired=set(pack['replaced_placement_ids']);self.assertEqual(set(old)-set(new),retired);self.assertEqual(len(retired),39)
  for ident in set(old)&set(new):self.assertEqual(old[ident],new[ident])
 def test_no_component_double_render(self):
  ids={p['id'] for p in self.d['common_instances']};p=json.loads((CITY/'assemblies/property/registered/merchant_block011/resolved_placements.json').read_bytes());components={c['id'] for c in p['component_placements']};self.assertFalse(ids&components);self.assertEqual(self.d['counts']['merchant_compounds'],14)
 def test_draft_cannot_render(self):self.assertEqual(self.d['terrain_module'],'UNBOUND_R14_DO_NOT_RENDER')
 def test_palette_cache_isolation(self):
  keys={}
  for p in self.d['common_instances']:
   key=(p['asset_key'],p['palette_id']);v=json.dumps(p['palette_override'],sort_keys=True);self.assertEqual(keys.setdefault(key,v),v)
 def test_preserved_structural_packs(self):
  for name in ('woodland','landmarks','property','bridge','ordinary_density','landscape','fortifications','port','market','ordinary_density_b15','reservoir','training','b13_workyards'):
   self.assertEqual([p for p in self.base['common_instances'] if p['source_pack']==name],[p for p in self.d['common_instances'] if p['source_pack']==name])
if __name__=='__main__':unittest.main()
