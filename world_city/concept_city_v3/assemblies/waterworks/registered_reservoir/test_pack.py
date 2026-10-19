"""Bounded exact native tests for reservoir source, bores and dry ownership."""
import collections,json,math,resource,time,unittest
from author_reservoir import *
from voxel_character.common import coordinate_planes,render_data
class ReservoirTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.started=time.monotonic();cls.p=json.loads((HERE/'resolved_placements.json').read_text());cls.cells={};cls.rows=[]
  for a in cls.p['assets']:
   s=json.loads((ROOT/a['source']['path']).read_text());t=time.monotonic();c=coordinate_planes.compile_master(s,{'pitch':.2},max_candidate_cells=600000,max_output_cells=200000);r=render_data.make_render_data(c);assert c['valid'];assert r==json.loads((ROOT/a['cache']['path']).read_text());cls.cells[a['id']]={tuple(x[:3]) for x in c['cells']};cls.rows.append({'id':a['id'],'candidate_cells':c['candidate_cells'],'output_cells':len(c['cells']),'seconds':time.monotonic()-t})
 @classmethod
 def tearDownClass(cls):
  write(HERE/'native_replay_report.json',{'schema':'riverstone.city.reservoir_native_replay.v1','pack':ref(HERE/'resolved_placements.json'),'requests':cls.rows,'elapsed_seconds':time.monotonic()-cls.started,'peak_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'replay_hashes_match':True})
 def occupied(self,id,point):
  p=next(x for x in self.p['placements'] if x['id']==id);o=p['position_m'];a=math.radians(p['yaw_degrees']);dx,dz=point[0]-o[0],point[2]-o[2];local=[math.cos(a)*dx-math.sin(a)*dz,point[1]-o[1],math.sin(a)*dx+math.cos(a)*dz];index=tuple(math.floor(v/.2+1e-7) for v in local);return index in self.cells[p['asset_key']]
 def test_hashes_and_provenance(self):
  for a in self.p['assets']:
   self.assertEqual(ref(ROOT/a['source']['path']),a['source']);self.assertEqual(ref(ROOT/a['cache']['path']),a['cache'])
  self.assertFalse(self.p['completion_claims']['actual_visual_review']);self.assertFalse(self.p['completion_claims']['flow_or_potable_certified'])
 def test_real_protected_bore(self):
  for zstep in range(61):
   z=-344+zstep*.1
   for x in [-36.2,-36,-35.8]:
    for y in [15.2,15.6,16.0]:
     for id in ['RESERVOIR_BANKS','RESERVOIR_PROTECTED_CONDUIT','RESERVOIR_DRAWPOINT']:
      self.assertFalse(self.occupied(id,[x,y,z]),(id,x,y,z))
 def test_draw_shaft(self):
  for i in range(38):self.assertFalse(self.occupied('RESERVOIR_DRAWPOINT',[-36,15.5+i*.1,-335.7167708839214]))
 def test_wet_mouth_and_sluice(self):
  p=next(x for x in self.p['placements'] if x['id']=='RESERVOIR_OVERFLOW_SLUICE')
  for x in [-.6,0,.6]:
   for z in [-1,0,1]:
    q=pose([x,-.2,z],p['position_m'],p['yaw_degrees']);self.assertFalse(self.occupied('RESERVOIR_OVERFLOW_SLUICE',q));self.assertFalse(self.occupied('RESERVOIR_BANKS',q))
 def test_bed_bank_native_connection(self):
  bed=self.cells['registered_reservoir_basin_bed'];bank=self.cells['registered_reservoir_basin_perimeter_supply_opening_r02'];allcells=bed|bank;seen={next(iter(bed))};queue=collections.deque(seen)
  while queue:
   x,y,z=queue.popleft()
   for q in [(x-1,y,z),(x+1,y,z),(x,y-1,z),(x,y+1,z),(x,y,z-1),(x,y,z+1)]:
    if q in allcells and q not in seen:seen.add(q);queue.append(q)
  self.assertEqual(len(allcells-seen),0)
 def test_dry_floor_actual_and_lane_free(self):
  roads=[r for r in DATA['roads'] if r['id']=='RESERVOIR_SERVICE'];wet=water.finite_water_polygons()
  for f in self.p['owned_floors']:
   poly=f['polygon_xz_m'];x=sum(v[0] for v in poly)/len(poly);z=sum(v[1] for v in poly)/len(poly);self.assertTrue(self.occupied('RESERVOIR_DRAWPOINT',[x,17.99,z]))
   for w in wet:self.assertLess(geo.intersection_area(poly,w['polygon_xz_m']),1e-8)
   for r in roads:
    for a,b in zip(r['polyline_xz_m'],r['polyline_xz_m'][1:]):self.assertLess(geo.intersection_area(poly,geo.road_ribbon(a,b,r['width_m'])),1e-8)
if __name__=='__main__':unittest.main(verbosity=2)
