"""Classify cross-holding native and grade dependencies before bulk emission."""
import json,time,math,collections
from .screen import HERE,write
from .. import author as a

def run():
 t=time.monotonic();layout=json.loads((HERE/'combined_source_layout.json').read_bytes());prep=json.loads((HERE/'prepared_ownership.json').read_bytes());holds={h['id']:h for h in layout['holdings']};rows=[];idx=a.geo._SpatialIndex(16)
 def add(hid,kind,p,floor):idx.add(len(rows),p);rows.append(dict(holding_id=hid,kind=kind,polygon_xz_m=p,floor_y_m=floor))
 for p in prep['parcels']:
  for q in p['whole_holding_polygons_xz_m']:add(p['id'],'holding',q,p['floor_y_m'])
 for p in layout['placements']:
  for q in p['native_walking_obstacles_xz_m']:add(p['holding_id'],'native_body',q,p['finished_floor_y_m'])
 for h in layout['holdings']:
  for q in h['external_route_polygons_xz_m']:add(h['id'],'external_route',q,h['floor_y_m'])
 hits=[]
 for i,r in enumerate(rows):
  if r['kind']=='native_body':continue
  for j in sorted(idx.candidates(r['polygon_xz_m'])):
   s=rows[j]
   if r['holding_id']==s['holding_id']:continue
   if s['kind']!='native_body'and j<=i:continue
   if r['kind']=='holding'and s['kind']=='native_body':continue
   if r['kind']!='external_route'and s['kind']=='external_route':continue
   if r['kind']=='holding'and s['kind']=='holding'and abs(r['floor_y_m']-s['floor_y_m'])<1e-7:continue
   q=a.clip(r['polygon_xz_m'],s['polygon_xz_m'])
   if q and(ar:=a.geo.polygon_area(q))>1e-7:
    delta=abs(r['floor_y_m']-s['floor_y_m'])
    if s['kind']!='native_body'and delta<1e-7:continue
    hits.append(dict(left_holding=r['holding_id'],left_kind=r['kind'],right_holding=s['holding_id'],right_kind=s['kind'],left_floor_y_m=r['floor_y_m'],right_floor_y_m=s['floor_y_m'],area_m2=ar,polygon_xz_m=q,classification='NEW_NATIVE_CLEARANCE_HOLD'if s['kind']=='native_body'else'SHARED_FINITE_PROFILE_DEPENDENCY'))
 summary=dict(holdings=len(holds),tested_rows=len(rows),native_contact_pieces=sum(h['classification']=='NEW_NATIVE_CLEARANCE_HOLD'for h in hits),cross_level_pieces=sum(h['classification']=='SHARED_FINITE_PROFILE_DEPENDENCY'for h in hits),affected_holding_ids=sorted({h[k]for h in hits for k in('left_holding','right_holding')}),elapsed_s=time.monotonic()-t)
 write('route_ownership_review.json',dict(summary=summary,contacts=hits,activation=False));print(summary,flush=True)
if __name__=='__main__':run()
