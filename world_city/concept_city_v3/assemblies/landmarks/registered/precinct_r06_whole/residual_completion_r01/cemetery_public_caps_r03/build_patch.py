"""Close only the retired cemetery branch footprint outside canonical traffic."""
from author_retirement import *
from world_city.concept_city_v3.registered_topography.revisions.r17_district_batches.coherent_b15_r01.compose_cluster import interfaces
OUT=Path(__file__).resolve().parent

def main():
 partition=load(OUT/'retirement_partition.json');pack=load(OUT/'resolved_native_candidate.json');scene=terrain.load_scene();rows=[dict(r,id='CEMETERY_RESTORED_SOIL:'+str(i),action='field',kind='retired_native_same_datum_soil')for i,r in enumerate(partition['off_public_restoration'])];windows=[r['polygon_xz_m']for r in partition['retired_native_floor']];index=terrain.TriangleIndex(scene,windows);edits=[];parts=[];maskidx=geo._SpatialIndex(8)
 for i,r in enumerate(rows):maskidx.add(i,r['polygon_xz_m'])
 for r in index.rows:
  q=r['polygon_xz_m'];a=fg.area(q)
  if a<=1e-8:continue
  masks=[rows[i]['polygon_xz_m']for i in maskidx.candidates(q)];outside=fg.subtract([q],masks);oa=sum(fg.area(p)for p in outside)
  if a-oa<1e-8:continue
  edits.append(dict(material=r['material'],triangle_index=r['triangle_index'],source_triangle_sha256=r['source_triangle_sha256'],replacement_triangles_xyz_m=[t for p in outside for t in terrain.fan_upward(lift(p,r['plane_y_xz_m']))]));parts.append(dict(material=r['material'],triangle_index=r['triangle_index'],original_area_m2=a,retained_area_m2=oa,cut_area_m2=a-oa))
 # Supply the actual retained native floor and exact parent public planes to
 # finite edge closure; these are context, not duplicate emitted public tops.
 public_source=load(ROOT/partition['public_source']['path']);public_index=geo._SpatialIndex(8)
 for i,r in enumerate(public_source['records']):public_index.add(i,r['polygon_xz_m'])
 context=upper(faces(pack['placements'][0])[0])+[public_source['records'][i]for i in sorted({i for q in windows for i in public_index.candidates(q)})]
 for rr in context:
  for t in terrain.fan_upward(lift(rr['polygon_xz_m'],rr['plane_y_xz_m'])):
   r=dict(material='retained_native_or_canonical_public_context',triangle_index=len(index.rows),vertices_xyz_m=t,polygon_xz_m=[[v[0],v[2]]for v in t],plane_y_xz_m=rr['plane_y_xz_m'],source_triangle_sha256=terrain.canonical_sha(t));index.index.add(len(index.rows),r['polygon_xz_m']);index.rows.append(r)
 spatial=index.index
 class PrioritySpatial:
  def candidates(self,p):return sorted(spatial.candidates(p),key=lambda i:(index.rows[i]['material']!='retained_native_or_canonical_public_context',i))
 index.index=PrioritySpatial()
 closure=interfaces(scene,index,rows);edits+=closure['side_surface_edits'];app={'ground_earth':[v for r in rows for t in terrain.fan_upward(lift(r['polygon_xz_m'],r['plane_y_xz_m']))for v in t]};walls=closure['appended_retaining_triangles_xyz_m'];print('closure keys',closure.keys(),flush=True)
 # compose_cluster returns finite side closure in appended_surfaces.
 for mat,vs in closure.get('appended_surfaces',{}).items():app.setdefault(mat,[]).extend(vs)
 if walls:app.setdefault('bank',[]).extend(v for t in walls for v in t)
 overlap=[]
 pub=load(ROOT/partition['public_source']['path']);pi=geo._SpatialIndex(8)
 for i,r in enumerate(pub['records']):pi.add(i,r['polygon_xz_m'])
 for r in rows:
  for i in pi.candidates(r['polygon_xz_m']):
   a=fg.area(fg.clip(r['polygon_xz_m'],pub['records'][i]['polygon_xz_m']))
   if a>1e-7:overlap.append(dict(soil_id=r['id'],public_owner_id=pub['records'][i]['id'],area_m2=a))
 patch=dict(schema='riverstone.finite_source_index_surface_patch.v1',id='R8_CEMETERY_OBSOLETE_BRANCH_RETIREMENT_R03',status='CANDIDATE_FINAL_CLOSURE_REVIEW',base_scene_sha256=terrain.SCENE_SHA256,source_surface_hashes={m:terrain.canonical_sha(scene['surfaces'][m])for m in {e['material']for e in edits}},surface_edits=edits,appended_surfaces=app,removed_foundation_proxy_ids=[],native_pack=ref(OUT/'resolved_native_candidate.json'),public_ownership=partition['public_source'],policy='Only the obsolete branch floor is retired. Canonical public polygons receive no soil/native overlay. All off-public restoration preserves the original Y14 datum; cemetery walls, gate and burial floor operations are unchanged.');write('surface_patch_candidate.json',patch);write('ground_audit.json',dict(restoration_owners=rows,source_partitions=parts,side_closure=closure,public_overlap=overlap,summary=dict(soil_area_m2=sum(fg.area(r['polygon_xz_m'])for r in rows),surface_indices=len(edits),unknown_edges=len(closure['unknown_exterior_segments']),appended_by_material={m:len(v)//3 for m,v in app.items()})));print('patch',len(edits),'unknown',len(closure['unknown_exterior_segments']),'publicoverlap',len(overlap),flush=True)
if __name__=='__main__':main()
