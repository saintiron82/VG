"""Bounded source ownership and exterior support diagnosis for common repair."""
from pathlib import Path
import sys,json,time
OUT=Path(__file__).resolve().parent;BASE=OUT.parent;sys.path.insert(0,str(BASE))
from resolve_pack import *
from native_walks import CompositeSupportIndex
from world_city.concept_city_v3.registered_topography.revisions.r17_district_batches.coherent_b15_r01.compose_cluster import interfaces
OUT=Path(__file__).resolve().parent

def main():
 t=time.monotonic();d=load(OUT/'common_entry_surface_audit.json');ext=d['row']['external_surface'];scene=terrain.load_scene();polys=ext['polygon_regions_xz_m'];ix=terrain.TriangleIndex(scene,[b.rect(-304,-61,-241,-40)]);proj=load(BASE/'actual_native_projection.json');hits=[];cache={}
 for p in proj['instances']:
  if not any(geo.intersection_area(q,r)>1e-7 for q in p['native_parts_xz_m']for r in polys):continue
  key=p['asset_key'];mesh=load(ROOT/proj['assets'][key]['cache']['path']);body=slab_rectangles(mesh,.01,2.2)
  for q in [b.xform(q,p)for q in body]:
   for r in polys:
    ar=geo.intersection_area(q,r)
    if ar>1e-7:hits.append({'native_id':p['id'],'asset':key,'area_m2':ar,'polygon_xz_m':geo.convex_intersection(q,r),'position_m':p['position_m']})
 logical=[]
 for i,row in enumerate(ext['triangulated_top_surface']):
  tri=row['vertices_xyz_m'];logical.append({'id':f'COMMON_ENTRY:{i}','polygon_xz_m':[[v[0],v[2]]for v in tri],'plane_y_xz_m':terrain.common.plane(tri),'action':'field','material':'alley','kind':'common_public_approach'})
 # Support index includes actual native common floor at the inside gate.
 native=load(BASE/'native_walk_support.json');vs=native['triangles_xyz_m'];nativeix=terrain.TriangleIndex({'surfaces':{'retained_native_floor':vs}},[b.rect(-304,-61,-241,-40)])
 offset=len(ix.rows)
 for i,r in enumerate(nativeix.rows):ix.index.add(len(ix.rows),r['polygon_xz_m']);ix.rows.append(r)
 closure=interfaces(scene,ix,logical)
 boxes=[]
 for box in scene.get('boxes',[]):
  if any(x in box.get('id','').lower()for x in('block_006','common','park')):boxes.append(box)
 report={'source':ref(OUT/'common_entry_surface_audit.json'),'native_contacts':hits,'logical_owners':logical,'closure':closure,'possible_source_boxes':boxes,'elapsed_seconds':time.monotonic()-t};(OUT/'common_field_diagnosis.json').write_text(json.dumps(report,indent=2)+'\n');print('native',len(hits),'unknownedges',len(closure['unknown_exterior_segments']),'sides',len(closure['side_surface_edits']),'retaining',len(closure['appended_retaining_triangles_xyz_m']),'seconds',report['elapsed_seconds']);print(hits[:3])
if __name__=='__main__':main()
