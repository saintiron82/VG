"""Public finite-profile joins and actual nearby door preservation."""
import json,math,collections
from . import author as a
def run():
 records=[];b=a.COLLAR_BOUNDS
 for x in range(math.floor(b[0]/8)*8,math.ceil(b[2]/8)*8,8):
  for z in range(math.floor(b[1]/8)*8,math.ceil(b[3]/8)*8,8):records.extend(a.surface_domains([x,z,x+8,z+8]))
 edges=collections.defaultdict(list)
 for r in records:
  if not r.get('render_land',True):continue
  p=r['polygon_xz_m']
  for p,q in zip(p,p[1:]+p[:1]):
   if math.dist(p,q)<1e-7:continue
   key=tuple(sorted(tuple(round(v,7) for v in pt) for pt in (p,q)))
   edges[key].append((r,p,q))
 groups={};failures=[]
 for es in edges.values():
  if len(es)!=2:continue
  if es[0][0]['kind']!='r14_public_profile' and es[1][0]['kind']!='r14_public_profile':continue
  r,p,q=es[0];s=es[1][0];kind='/'.join(sorted([r['kind'],s['kind']]))
  g=groups.setdefault(kind,dict(edge_count=0,max_height_difference_m=0));g['edge_count']+=1
  maximum=0;old_maximum=0;maximum_increase=0;rendered_maximum=0
  def before(o,x,z):
   while o['kind'] in ('r14_public_profile','r14_merchant_transition'):o=o['underlying_record']
   return a.prior.surface_height_at(o,x,z) if not o['kind'].startswith('r14_') else a.surface_height_at(o,x,z)
  for i in range(5):
   pt=[p[k]+i/4*(q[k]-p[k]) for k in (0,1)];new_delta=abs(a.surface_height_at(r,*pt)-a.surface_height_at(s,*pt));old_delta=abs(before(r,*pt)-before(s,*pt));maximum=max(maximum,new_delta);old_maximum=max(old_maximum,old_delta);maximum_increase=max(maximum_increase,new_delta-old_delta)
  rendered_maximum=max(abs(a.surface_height_at(r,*pt)-a.surface_height_at(s,*pt)) for pt in (p,q))
  rendered_worsening=max(abs(a.surface_height_at(r,*pt)-a.surface_height_at(s,*pt))-abs(before(r,*pt)-before(s,*pt)) for pt in (p,q))
  classification='analytic_evaluator_vs_shared_linear_preview_only' if rendered_maximum<1e-6 else ('inherited_unchanged_or_reduced' if rendered_worsening<1e-8 else 'new_rendered_seam_failure')
  g['maximum_rendered_linear_edge_difference_m']=max(g.get('maximum_rendered_linear_edge_difference_m',0),rendered_maximum)
  g['max_height_difference_m']=max(g['max_height_difference_m'],maximum)
  if maximum>1e-6 and ('door' in kind or 'gate' in kind or kind in ('r14_public_profile/r14_public_profile','r14_public_profile/road','r14_public_profile/road_shoulder')):failures.append(dict(left=r['owner_id'],right=s['owner_id'],kind=kind,segment_xz_m=[p,q],maximum_height_difference_m=maximum,maximum_rendered_linear_edge_difference_m=rendered_maximum,baseline_maximum_difference_m=old_maximum,maximum_worsening_m=maximum_increase,maximum_rendered_worsening_m=rendered_worsening,classification=classification))
 ordinary=json.loads((a.CITY/'assemblies/ordinary/registered/resolved_placements.json').read_bytes());door=next(d for d in ordinary['access_proposals'] if d['source_mass_id']=='B_REG_0279');samples=[]
 for poly in door['reserved_connection_polygons_xz_m']:
  for p,q in zip(poly,poly[1:]+poly[:1]):
   for i in range(9):
    x,z=[p[k]+i/8*(q[k]-p[k]) for k in (0,1)];r=a.owner_at(x,z);old=a.prior.owner_at(x,z)
    bounds=[math.floor(x/8)*8,math.floor(z/8)*8,math.floor(x/8)*8+8,math.floor(z/8)*8+8]
    samples.append(dict(point_xz_m=[x,z],old_source_y_m=a.prior.source_surface_height_at(old,x,z),source_y_m=a.source_surface_height_at(r,x,z),old_preview_y_m=a.prior.surface_height_at(dict(old,review_tile_bounds_xz_m=bounds),x,z),preview_y_m=a.surface_height_at(dict(r,review_tile_bounds_xz_m=bounds),x,z),owner_id=r['owner_id']))
 result=dict(author_sha256=a.R04.sha(a.HERE/'author.py'),profile_sha256=a.collar.SHA256,shared_edges=groups,public_seam_failures=failures,retained_neighbour_door=dict(source_mass_id=door['source_mass_id'],actual_door_xyz_m=door['actual_door_xyz_m'],maximum_source_height_change_m=max(abs(r['old_source_y_m']-r['source_y_m']) for r in samples),maximum_preview_departure_m=max(abs(r['old_source_y_m']-r['preview_y_m']) for r in samples),maximum_preview_change_m=max(abs(r['old_preview_y_m']-r['preview_y_m']) for r in samples),samples=samples),limitations=['Different terrain/terrace heights are retaining interfaces, not implicitly walkable edges.','The continuous analytic source and bounded preview field remain separately declared.'])
 (a.HERE/'profile_interfaces.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items() if k!='retained_neighbour_door'},indent=2));print({k:v for k,v in result['retained_neighbour_door'].items() if k!='samples'});return result
if __name__=='__main__':run()
