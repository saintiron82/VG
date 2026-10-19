"""Classify new seven-entry physical overlaps without changing any owner."""
import json,math,collections,time
from . import finite_geometry_r03 as g, public_domain as pd
from ..r17_district_batches import author as a
from .height_field import HERE

def ref(p):return {'path':str(p.relative_to(a.ROOT)),'sha256':a.sha(p)}
def ar(ps):return math.fsum(g.area(p) for p in ps)
def clips(p,polys):return g.union([q for poly in polys if a.intersects(a.bounds(p),a.bounds(poly)) and (q:=g.clip(p,poly))])
def main():
 t=time.monotonic();rp=HERE/'noble_full_public_projection_r01.json';hp=HERE/'top_hole_classification_r02.json';np=a.CITY/'assemblies/landmarks/registered/precinct_r06_whole/residual_completion_r01/noble_entry_batch_r01/fixed_public_interfaces_r18.json';cp=a.CITY/'assemblies/property/registered/public_lane_repairs_r01/baseline/cap_columns.json';fp=HERE/'finite_field_candidate_r07_native_bound.json'
 d=json.loads(rp.read_bytes());holes=json.loads(hp.read_bytes());native=json.loads(np.read_bytes());caps=json.loads(cp.read_bytes());field=json.loads(fp.read_bytes());hm={r['owner_id']:r['hole_polygons_xz_m'] for r in holes['rows']};fm={r['id']:r for r in field['records']};nm={r['owner_id']:r for r in native['owners']};cm={r['property_id']:[p['polygon_xz_m'] for p in r['candidate_columns']] for r in caps['records']};roads=pd.records();idx=a.geo._SpatialIndex(16);[idx.add(i,r['polygon_xz_m']) for i,r in enumerate(roads)];summary=collections.defaultdict(lambda:collections.defaultdict(float));rows=[]
 for r in d['rows']:
  p=r['polygon_xz_m'];eid=r['native_owner_id'];rec=fm[r['public_owner_id']];oid=rec.get('previous_owner_id',rec['id']);h=clips(p,hm.get(oid,[]));existing=g.subtract([p],h);cap=clips(p,cm.get(eid,[]));roadpieces=[]
  for ri in idx.candidates(p):
   road=roads[ri]
   if q:=g.clip(p,road['polygon_xz_m']):roadpieces.append({'road_id':road.get('road_id',road['id']),'domain_id':road['id'],'polygon_xz_m':q,'kind':road['kind']})
  row=dict(r,inherited_source_hole_pieces_xz_m=h,source_backed_public_pieces_xz_m=existing,original_retired_cap_column_pieces_xz_m=cap,canonical_road_pieces=roadpieces,inside_source_hole_area_m2=ar(h),source_backed_public_area_m2=ar(existing),inside_retired_cap_columns_area_m2=ar(cap));rows.append(row)
  for k in ['area_m2','inside_source_hole_area_m2','source_backed_public_area_m2','inside_retired_cap_columns_area_m2']:summary[eid][k]+=row[k]
  summary[eid]['records']+=1
 out={'schema':'riverstone.noble_public_projection_classification.v1','status':'HELD_ATOMIC_OWNERSHIP_CORRECTION','sources':[ref(p) for p in [rp,hp,np,cp,fp]],'summary':dict(summary),'rows':rows,'scope':'Exact finite public/native collision-top overlap classification. No plane or ownership edits; canonical traffic and surviving public support stay protected. An inherited source hole alone is not proof that a new private top is an intended terminal.','seconds':time.monotonic()-t};o=HERE/'noble_full_public_projection_classification_r02.json';o.write_text(json.dumps(out,separators=(',',':'))+'\n');print(dict(summary));print(ref(o),out['seconds'])
if __name__=='__main__':main()
