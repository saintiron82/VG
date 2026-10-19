import json,collections
from .prepare import HERE,write,load
from .. import author as a
from ...r01_ownership import author as ownership

def run():
 report=json.loads((HERE/'top_coverage_report_r01.json').read_bytes());hand=json.loads((HERE/'physical_owner_handoff_r02.json').read_bytes());byid={r['id']:r for r in hand['rendered_plane_owners']};context=json.loads((HERE/'side_context_binding.json').read_bytes());public=load(context['public_field'])['records'];pi=a.geo._SpatialIndex(8)
 for i,r in enumerate(public):pi.add(i,r['polygon_xz_m'])
 fixed=hand['public_fixed_regions'];fi=a.geo._SpatialIndex(8)
 for i,r in enumerate(fixed):fi.add(i,r['polygon_xz_m'])
 roads=[];ri=a.geo._SpatialIndex(8)
 for r in json.loads(a.PLAN_PATH.read_bytes())['roads']:
  for p in ownership.corridor(r['polyline_xz_m'],r['width_m']):ri.add(len(roads),p);roads.append(dict(id=r['id'],polygon_xz_m=p))
 out=[]
 for fail in report['failures']:
  if fail['outside_cut_domain_m2']<=1e-7:continue
  owner=byid[fail['id']];row=dict(id=fail['id'],holding_id=fail['holding_id'],outside_area_m2=fail['outside_cut_domain_m2'],public_hits=[],fixed_hits=[],canonical_road_ids=[])
  for p in fail['outside_cut_polygons_xz_m']:
   for label,source,index in [('public_hits',public,pi),('fixed_hits',fixed,fi)]:
    for j in index.candidates(p):
     r=source[j];q=a.clip(p,r['polygon_xz_m'])
     if q and a.geo.polygon_area(q)>1e-9:row[label].append(dict(id=r['id'],area_m2=a.geo.polygon_area(q),height_difference_m=max(abs(a.common.height(owner['plane_y_xz_m'],v)-a.common.height(r['plane_y_xz_m'],v))for v in q)))
   for j in ri.candidates(p):
    q=a.clip(p,roads[j]['polygon_xz_m'])
    if q and a.geo.polygon_area(q)>1e-9:row['canonical_road_ids'].append(roads[j]['id'])
  out.append(row)
 write('top_hold_diagnosis_r01.json',dict(rows=out))
 group=collections.defaultdict(lambda:dict(area=0,public_area=0,fixed_area=0,max_public_delta=0,max_fixed_delta=0,roads=set()))
 for r in out:
  s=group[r['holding_id']];s['area']+=r['outside_area_m2'];s['roads'].update(r['canonical_road_ids'])
  for k in ['public','fixed']:
   s[k+'_area']+=sum(x['area_m2']for x in r[k+'_hits']);s['max_'+k+'_delta']=max([x['height_difference_m']for x in r[k+'_hits']]+[s['max_'+k+'_delta']])
 for h,v in group.items():v['roads']=sorted(v['roads']);print(h,v,flush=True)
if __name__=='__main__':run()
