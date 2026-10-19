import json,unittest
from pathlib import Path
from . import author as r
from .. import author as q
from ... import author as a
class Tests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.old=json.loads((q.HERE/'resolved_placements.json').read_text());cls.new=json.loads((r.HERE/'resolved_placements.json').read_text())
 def test_exact_bounded_change(self):
  self.assertEqual(len(self.new['private_route_repair_ledger']),3);self.assertEqual(len(self.new['placements']),86);self.assertEqual(len(self.new['asset_manifest']),16);self.assertEqual(self.old['external_access_surfaces'],self.new['external_access_surfaces']);self.assertEqual(self.old['actual_doors'],self.new['actual_doors'])
  old={p['id']:p for p in self.old['placements']}
  for p in self.new['placements']:
   if p['id'] not in ('E1:registered_r1:infrastructure','E6:registered_r1:infrastructure'):self.assertEqual(p,old[p['id']])
 def test_verified_asset_hashes(self):
  for m in self.new['asset_manifest'].values():self.assertEqual(a.file_sha(m['compiled_asset_ref']),m['render_sha256']);self.assertEqual(a.file_sha(m['master_path']),m['master_file_sha256'])
  self.assertEqual(self.new['cache_manifest_sha256'],a.file_sha(r.HERE/'cache_manifest.json'))
 def test_all_internal_ribbons_clear_actual_wall_caps(self):
  for pid in ('E1','E6'):
   recipe=json.loads((r.HERE/(pid+'.recipe.json')).read_text());self.assertTrue(a.validate_recipe(recipe)['valid']);mask=next(m for m in self.new['ownership_masks'] if m['property_id']==pid);walls=[p['polygon_xz_m'] for p in mask['compiled_upward_faces'] if p['y_m']>mask['floor_y_m']+1]
   self.assertFalse(any(a.overlap(z,w) for p in recipe['entrance_routes'] for z in p['ribbon_polygons_xz_m'] for w in walls))
 def test_actual_top_geometry_unchanged(self):
  def topcells(ref):
   data=json.loads(Path(ref).read_text());out=set();pitch=data['pitch']
   for group in data['groups']:
    for quad in group['quads']:
     normal=q.cross(q.sub(quad[1],quad[0]),q.sub(quad[2],quad[0]))
     if normal[1]<=1e-7:continue
     for x in range(round(min(v[0] for v in quad)/pitch),round(max(v[0] for v in quad)/pitch)):
      for z in range(round(min(v[2] for v in quad)/pitch),round(max(v[2] for v in quad)/pitch)):out.add((x,round(quad[0][1]/pitch),z))
   return out
  for pid in ('E1','E6'):
   old=next(p for p in self.old['placements'] if p['id']==pid+':registered_r1:infrastructure');new=next(p for p in self.new['placements'] if p['id']==old['id']);self.assertEqual(topcells(old['compiled_asset_ref']),topcells(new['compiled_asset_ref']))
 def test_unpromoted_and_parents_untouched(self):
  self.assertFalse(self.new['runtime_ready']);self.assertFalse(self.new['applied_to_scene']);self.assertEqual(self.new['parent_r1_pack_sha256'],a.file_sha(q.HERE/'resolved_placements.json'))
  for p,s in json.loads((a.HERE/'r0_seal.json').read_text())['files_sha256'].items():self.assertEqual(a.file_sha(a.HERE/p),s)
if __name__=='__main__':unittest.main()
