"""Small-data invariants for the source-bound forecourt side repair."""
import json,math,collections,hashlib,sys
from pathlib import Path
import numpy as np
from .build_corridors import H,ref,xz,plane,ph
from world_city.runtime_city.checks import placement as geo

def digest(v):return hashlib.sha256(json.dumps(v,separators=(',',':')).encode()).hexdigest()
def main():
 c=H/(sys.argv[1]if len(sys.argv)>1 else 'shoulder_repair_r10_staging');p=json.load(open(c/'surface_patch.json'));old=json.load(open(H/'candidate_r09/surface_patch.json'));r=json.load(open(c/'repair_report.json'));w=json.load(open(c/'wall_ledger.json'))
 vs=p['appended_surfaces']['ground_grass'];off=r['kept_grass_triangles']*3;new=vs[off:];verts=collections.defaultdict(list);rows=[];index=geo._SpatialIndex(2);areas=collections.defaultdict(float);peak=0.;bad=[]
 for i in range(0,len(new),3):
  t=new[i:i+3];f=np.asarray(t,dtype=np.float32);n=np.cross(f[1]-f[0],f[2]-f[0]);grade=float(np.linalg.norm(n[[0,2]])/n[1]);peak=max(peak,grade);poly=[xz(v)for v in t];rows.append(dict(triangle=t,poly=poly,plane=plane(t)));index.add(i//3,poly)
  for v in f:verts[(float(v[0]),float(v[2]))].append(float(v[1]))
  if n[1]<=0:bad.append(i//3)
 conflicts=[dict(xz=q,heights=sorted(set(ys)))for q,ys in verts.items()if len(set(ys))>1]
 def heights(q):return [ph(rows[i]['plane'],q)for i in index.candidates([q])if geo.point_in_convex_polygon(q,rows[i]['poly'],1e-9)]
 maximum_internal_delta=0.;probes=0
 for row in rows:
  for a,b in zip(row['triangle'],row['triangle'][1:]+row['triangle'][:1]):
   q=[(a[0]+b[0])/2,(a[2]+b[2])/2];ys=heights(q)
   if len(ys)>1:maximum_internal_delta=max(maximum_internal_delta,max(ys)-min(ys));probes+=1
 for name,d in [('old',old),('new',p)]:
  vv=d['appended_surfaces']['ground_grass']
  for i in range(0,len(vv),3):areas[name]+=geo.polygon_area([xz(v)for v in vv[i:i+3]])
 road_walls=[q for q in w if q['adjacent_material']=='road'];maxwall=max(abs(a[1]-b[1])for q in w for a,b in zip(q['upper'],q['lower']))
 same={k:digest(p['appended_surfaces'][k])==digest(old['appended_surfaces'][k])for k in old['appended_surfaces']if k!='ground_grass'}
 area_loss=areas['old']-areas['new'];dropped_area=sum(q['area_m2']for q in r['discarded_subquantization'])
 result=dict(schema='riverstone.forecourt_side_repair.audit.v1',source=ref(H/'candidate_r09/surface_patch.json'),candidate=ref(c/'surface_patch.json'),unchanged_appended_arrays=same,unchanged_source_edits=digest(old['surface_edits'])==digest(p['surface_edits']),unchanged_ownership=digest(old['ownership'])==digest(p['ownership']),road_array_sha256=digest(p['appended_surfaces']['road']),source_edits_sha256=digest(p['surface_edits']),shared_new_shoulder_float32_height_conflicts=conflicts,new_shoulder_upward_failures=bad,shared_edge_midpoint_probes=probes,maximum_new_shoulder_internal_edge_height_delta_m=maximum_internal_delta,maximum_new_shoulder_actual_float32_gradient=peak,road_boundary_retaining_wall_intervals=len(road_walls),missing_adjacent_boundary_intervals=r['missing_adjacent_intervals'],maximum_explicit_retaining_bank_height_m=maxwall,old_grass_projected_area_m2=areas['old'],new_grass_projected_area_m2=areas['new'],grass_projected_area_loss_m2=area_loss,discarded_split_face_area_m2=dropped_area,new_top_triangles=len(new)//3,new_bank_triangles=len(p['appended_surfaces'].get('bank',[]))//3,limits=['Only the widened gate forecourt side strips are repaired; unchanged road shoulders outside these bounds may retain pre-existing discontinuities.','Retaining walls reach the actual existing source top and can be up to the reported height. No traversability claim is made across the side walls.','Public road top arrays and original source edits are byte-equivalent JSON values. Native runtime collision crops change because the side walls are real geometry; runtime reuse or replay requires QA review.','Actual Godot same-eye visual reinspection is pending.'])
 result['status']='PASS_SOURCE_ONLY'if all(same.values())and result['unchanged_source_edits']and result['unchanged_ownership']and not conflicts and not bad and maximum_internal_delta<1e-4 and not road_walls and not r['missing_adjacent_intervals']and abs(area_loss)<1e-5 else 'FAIL_SOURCE'
 (c/'side_geometry_audit.json').write_text(json.dumps(result,separators=(',',':'))+'\n');print(json.dumps({k:result[k]for k in ['status','maximum_new_shoulder_internal_edge_height_delta_m','maximum_new_shoulder_actual_float32_gradient','maximum_explicit_retaining_bank_height_m','grass_projected_area_loss_m2','road_boundary_retaining_wall_intervals']}))
 assert result['status']=='PASS_SOURCE_ONLY'
if __name__=='__main__':main()
