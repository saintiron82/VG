"""Exact finite public/native access-skin remainder audit; no source activation."""
import json,math,collections
from .height_field import HERE
from . import finite_geometry_r03 as g,public_domain
from ..r17_district_batches import author as a

def ref(p):return dict(path=str(p.relative_to(a.ROOT)),sha256=a.sha(p))
def main():
 src=HERE/'public_top_r01/physical_owners.json';data=json.loads(src.read_bytes());old=data.get('owners',data.get('records'))if isinstance(data,dict)else data;old=[r for r in old if r['kind']=='nonwalking_private_cap_remainder'];traffic=public_domain.records();ti=a.geo._SpatialIndex(4)
 for i,r in enumerate(traffic):ti.add(i,r['polygon_xz_m'])
 field_path=HERE/'finite_field_candidate_r04_common.json';field=json.loads(field_path.read_bytes())['records'];fi=a.geo._SpatialIndex(4)
 for i,r in enumerate(field):fi.add(i,r['polygon_xz_m'])
 cap_path=a.CITY/'assemblies/property/registered/public_lane_repairs_r01/baseline/cap_columns.json';caps=json.loads(cap_path.read_bytes());rows=[];public_overlap=[];native_cols=[];corrected=[]
 for r in old:
  touches=[];emit=[]
  for i in ti.candidates(r['polygon_xz_m']):
   q=g.clip(r['polygon_xz_m'],traffic[i]['polygon_xz_m'])
   if q:touches.append(dict(public_id=traffic[i]['id'],road_id=traffic[i]['road_id'],polygon_xz_m=q,area_m2=g.area(q)))
  for i in fi.candidates(r['polygon_xz_m']):
   q=g.clip(r['polygon_xz_m'],field[i]['polygon_xz_m'])
   if q:emit.append(dict(public_owner_id=field[i]['id'],polygon_xz_m=q,area_m2=g.area(q),delta_range_m=[min(a.common.height(r['plane_y_xz_m'],v)-a.common.height(field[i]['plane_y_xz_m'],v)for v in q),max(a.common.height(r['plane_y_xz_m'],v)-a.common.height(field[i]['plane_y_xz_m'],v)for v in q)]))
  union=g.union([x['polygon_xz_m']for x in touches]);over=math.fsum(g.area(p)for p in union);row=dict(id=r['id'],source_polygon_xz_m=r['polygon_xz_m'],plane_y_xz_m=r['plane_y_xz_m'],canonical_traffic_overlaps=touches,canonical_traffic_overlap_union_m2=over,emitted_public_overlaps=emit);rows.append(row)
  if over>1e-10:public_overlap.append(row)
 for r in caps['records']:
  for j,c in enumerate(r['candidate_columns']):
   p=c['polygon_xz_m'];cuts=[q for i in sorted(ti.candidates(p))if(q:=g.clip(p,traffic[i]['polygon_xz_m']))];ps=g.subtract([p],cuts);y=max(v['world_y_interval_m'][1]for v in c['cells']);native_cols.append(dict(property_id=r['property_id'],column_index=j,column_polygon_xz_m=p,native_top_y_m=y,public_parts=g.union(cuts),private_parts=ps))
   for k,q in enumerate(ps):corrected.append(dict(id=f"{r['property_id']}:PRIVATE_CAP_EXACT_PUBLIC_REMAINDER:{j}:{k}",polygon_xz_m=q,plane_y_xz_m=[0,0,y],kind='nonwalking_private_cap_remainder',material='ground_stone',action='field',source_column_index=j))
 out=dict(status='PASS_PRIVATE_REMAINDERS_CLEAR_CANONICAL_TRAFFIC'if not public_overlap else'HELD_PRIVATE_REMAINDERS_PUBLIC_OVERLAP',sources=[ref(src),ref(field_path),ref(cap_path)]+public_domain.source_refs(),code_sha256=a.sha(__file__),old_remainder_count=len(old),old_area_m2=math.fsum(g.area(r['polygon_xz_m'])for r in old),traffic_overlap_count=len(public_overlap),traffic_overlap_union_area_m2=math.fsum(r['canonical_traffic_overlap_union_m2']for r in rows),emitted_public_overlap_area_m2=math.fsum(x['area_m2']for r in rows for x in r['emitted_public_overlaps']),rows=rows,whole_column_partition=native_cols,corrected_private_owner_candidates=corrected,corrected_area_m2=math.fsum(g.area(r['polygon_xz_m'])for r in corrected),activation=False,scope='Any correction keeps exactly the original 101 cut columns and old native top planes. Only finite public-versus-private ownership is recomputed; original cells outside those columns remain unchanged.')
 p=HERE/'private_cap_remainder_audit_r01.json';p.write_text(json.dumps(out,separators=(',',':'))+'\n');print({k:v for k,v in out.items()if k not in('rows','whole_column_partition','corrected_private_owner_candidates','sources')},ref(p),flush=True)
if __name__=='__main__':main()
