"""Source-only regression for bounded coherent datum proposals."""
import unittest,json,math,collections
from pathlib import Path
from .. import author as a
from ..contour_bulk_r01 import profile_mesh
HERE=Path(__file__).resolve().parent;SOURCE=HERE.parent/'contour_bulk_r01'
class TestCoherentDatums(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.summary=json.loads((HERE/'coherent_datum_summary_r01.json').read_bytes());cls.rows=[]
  for row in cls.summary['rows']:
   cls.rows.append((row,json.loads((a.ROOT/row['path']).read_bytes())))
  cls.ready=[d for _,d in cls.rows if d['result']['status']=='FINITE_PROFILE_WITH_COHERENT_DATUM_CANDIDATE']
  cls.groups={g['id']:g for g in json.loads((SOURCE/'shared_private_groups_r03.json').read_bytes())['groups']}
  cls.budgets={r['id']:r for r in json.loads((SOURCE/'required_core_budget.json').read_bytes())['rows']}
 def test_source_hashes(self):
  for row,d in self.rows:
   self.assertEqual(a.sha(a.ROOT/row['path']),row['sha256'])
   for ref in (d['source_profile'],d['source_core_budget']):self.assertEqual(a.sha(a.ROOT/ref['path']),ref['sha256'])
 def test_only_held_source_and_no_activation(self):
  accepted=set(json.loads((SOURCE/'physical_owner_handoff_r02.json').read_bytes())['accepted_holding_ids']);ids=[]
  for _,d in self.rows:
   self.assertFalse(d['activation']);self.assertFalse(accepted.intersection(d['holding_ids']));ids+=d['holding_ids']
  self.assertEqual(len(ids),28);self.assertEqual(len(ids),len(set(ids)));self.assertEqual(sum(len(d['holding_ids'])for d in self.ready),15)
 def test_core_intervals(self):
  for d in self.ready:
   for x in d['result']['datum_changes']:
    b=self.budgets[x['holding_id']];lo=b['floor_y_m']+b['maximum_required_core_cut_m']-2.5;hi=b['floor_y_m']-b['maximum_required_core_fill_m']+2.5
    self.assertGreaterEqual(x['candidate_floor_y_m'],lo-1e-8);self.assertLessEqual(x['candidate_floor_y_m'],hi+1e-8)
    self.assertAlmostEqual(x['candidate_floor_y_m']-x['original_floor_y_m'],x['delta_y_m'],places=10)
 def test_every_actual_upward_face_and_gradient(self):
  for d in self.ready:
   for t in d['result']['triangles']:
    tr=t['vertices_xyz_m'];self.assertTrue(all(math.isfinite(v)for p in tr for v in p));self.assertGreater(a.normal_y(tr),0);plane=a.common.plane(tr);self.assertLessEqual(math.hypot(*plane[:2]),.12000001)
 def test_exact_domain_coverage(self):
  for d in self.ready:
   source=json.loads((a.ROOT/d['source_profile']['path']).read_bytes());domains=source['private_domain_polygons_xz_m'];idx=a.geo._SpatialIndex(4)
   for i,p in enumerate(domains):idx.add(i,p)
   actual=0.
   for t in d['result']['triangles']:
    p=t['polygon_xz_m'];actual+=a.geo.polygon_area(p);c=[sum(v[k]for v in p)/3 for k in(0,1)]
    self.assertTrue(any(a.geo.point_in_convex_polygon(c,domains[i],1e-8)for i in idx.candidates([c])))
   self.assertAlmostEqual(actual,sum(a.geo.polygon_area(p)for p in domains),places=6)
 def test_every_public_and_court_vertex(self):
  for d in self.ready:
   source=json.loads((a.ROOT/d['source_profile']['path']).read_bytes());public=source['public_fixed_regions'];g=self.groups[d['id']];datums={r['holding_id']:r['candidate_floor_y_m']for r in d['result']['datum_changes']};regs=public+[dict(r,plane_y_xz_m=[0.,0.,datums[r['id'].split(':COURT_DATUM')[0]]])for r in g['gate_fixed_regions']];idx=a.geo._SpatialIndex(4)
   for i,r in enumerate(regs):idx.add(i,r['polygon_xz_m'])
   count=0
   for tri in d['result']['triangles']:
    for v in tri['vertices_xyz_m']:
     p=[v[0],v[2]]
     for j in idx.candidates([p]):
      r=regs[j]
      if a.geo.point_in_convex_polygon(p,r['polygon_xz_m'],1e-9):self.assertAlmostEqual(v[1],a.common.height(r['plane_y_xz_m'],p),places=7);count+=1
   self.assertGreater(count,0)
 def test_shared_vertices_and_area_proof(self):
  for d in self.ready:
   buckets=collections.defaultdict(list);eps=1e-8
   for tri in d['result']['triangles']:
    for v in tri['vertices_xyz_m']:
     key=(math.floor(v[0]/eps),math.floor(v[2]/eps))
     for dx in(-1,0,1):
      for dz in(-1,0,1):
       for p in buckets[(key[0]+dx,key[1]+dz)]:
        if math.hypot(v[0]-p[0],v[2]-p[2])<1e-9:self.assertLess(abs(v[1]-p[1]),1e-7)
     buckets[key].append(v)
   for c in d['result']['cell_partition_checks']:self.assertLess(abs(c['residual_area_m2']),1e-7)
if __name__=='__main__':unittest.main()
