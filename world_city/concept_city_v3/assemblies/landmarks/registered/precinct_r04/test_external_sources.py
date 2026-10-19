"""Exact XZ source-ribbon audit; independent native controller audit is separate."""
from plan_coverage import *
def main():
 plan=load(HERE/'coverage_plan.json');prod=load(HERE/'productive_frames.json');land=load(LAND);garden=load(GARDEN);routes=load(HERE/'exterior_access_proposal.json');obstacles=[]
 for f in land['owned_floors']:obstacles.append((f['placement_id'],f['polygon_xz_m']))
 for s in garden['sites']:obstacles.append((s['id'],s['polygon_xz_m']))
 for c in plan['compounds']:obstacles.append((c['id'],c['requested_frame_xz_m']))
 for f in prod['frames']:obstacles.append((f['id'],f['polygon_xz_m']))
 index=geo._SpatialIndex(24)
 for i,(_,p)in enumerate(obstacles):index.add(i,p)
 findings=[];rows=[]
 for r in routes['routes']:
  owner=r['gate_id'].split(':')[0];hits=[]
  for kind,polys in [('ribbon',r['ribbon_polygons_xz_m']),('join',r['join_polygons_xz_m'])]:
   for j,p in enumerate(polys):
    for i in index.candidates(p):
     id,body=obstacles[i]
     if id==owner:continue
     area=geo.intersection_area(p,body)
     if area>1e-6:hits.append({'piece_type':kind,'piece_index':j,'obstacle_id':id,'area_m2':area})
  findings+=hits;rows.append({'route_id':r['id'],'length_m':r['length_m'],'exact_body_or_sealed_garden_hits':hits})
 report={'source_proposal':ref(HERE/'exterior_access_proposal.json'),'routes':rows,'total_hits':len(findings),'all_source_ribbons_clear':not findings,'limits':['Own gate crossing is intentional and requires native gate slab audit.','This does not validate terrain slope, capsule physics or destination surface ownership.']};write(HERE/'evidence/exterior_source_ribbon_audit.json',report);print('exact ribbon hits',len(findings));print(findings[:8])
if __name__=='__main__':main()
