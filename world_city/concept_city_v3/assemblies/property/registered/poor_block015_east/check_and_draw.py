"""Independent finite checks and genuine cached-roof projection for the draft."""
import json,math,hashlib
from pathlib import Path
from collections import Counter
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon
from PIL import Image,ImageDraw
from .author_density import HERE,ROOT,PLAN,PRIOR,ref,write,disjoint
from world_city.runtime_city.checks import placement as geo
from world_city.concept_city_v3.assemblies.ordinary.resolve_cached import transform,closest
from world_city.concept_city_v3.registered_source.author import Domain
from world_city.concept_city_v3.registered_topography import author as terrain

def run():
 d=json.loads((HERE/'candidate.json').read_text());old=json.loads(PRIOR.read_text());plan=json.loads(PLAN.read_text());roads={r['id']:r for r in plan['roads']};domain=Domain([d['block']['polygon_xz_m']]);members=d['placements'];oldids=set(d['replaced_placement_ids']);before=[p for p in old['placements'] if p['id'] in oldids];issues=[];internal_roof_overlap=0;bodyarea=0
 for i,p in enumerate(members):
  bodyarea+=geo.polygon_area(p['actual_body_footprint_xz_m'])
  if not domain.contains(p['actual_outer_footprint_xz_m']):issues.append({'kind':'outer_outside_block','id':p['id']})
  for q in members[:i]:
   body=geo.polygon_area(geo.convex_intersection(p['actual_body_footprint_xz_m'],q['actual_body_footprint_xz_m']))
   outer=geo.polygon_area(geo.convex_intersection(p['actual_outer_footprint_xz_m'],q['actual_outer_footprint_xz_m']))
   if body>1e-5:issues.append({'kind':'body_overlap','ids':[p['id'],q['id']],'area_m2':body})
   if outer>1e-5:
    if p['assembly_group_id']!=q['assembly_group_id']:issues.append({'kind':'external_roof_overlap','ids':[p['id'],q['id']],'area_m2':outer})
    else:internal_roof_overlap+=outer
 for path in d['access_proposals']:
  end=path['complete_proposed_connection_xz_m'][-1];road=roads[path['connects_source_path_or_road_id']];distance=closest(end,road['polyline_xz_m'])[0]
  if distance>1e-6:issues.append({'kind':'disconnected_door','id':path['id'],'distance_m':distance})
  for poly in path['reserved_connection_polygons_xz_m']:
   for p in members:
    if p['id']==path['source_mass_id']:continue
    overlap=geo.polygon_area(geo.convex_intersection(poly,p['actual_body_footprint_xz_m']))
    if overlap>1e-5:issues.append({'kind':'door_body_conflict','ids':[path['id'],p['id']],'area_m2':overlap})
 for path in d['court_paths']:
  for poly in path['reserved_polygons_xz_m']:
   for p in members:
    if geo.positive_area_overlap(poly,p['actual_outer_footprint_xz_m'],1e-5):issues.append({'kind':'court_link_roof_conflict','ids':[path['id'],p['id']]})
 # Common render hashes and genuine projected cached roof quads, with native pose.
 S=2;canvas=(1536*S,1024*S);ground=Image.new('1',canvas);ImageDraw.Draw(ground).polygon([tuple(S*v for v in terrain.project(p[0],2.5,p[1])) for p in d['block']['polygon_xz_m']],fill=1)
 projection={};masks={};renders={}
 for label,placements,assets in [('before',before,old['assets']),('after',members,d['assets'])]:
  roof=Image.new('1',canvas);body=Image.new('1',canvas);rd=ImageDraw.Draw(roof);bd=ImageDraw.Draw(body)
  for p in placements:
   a=assets[p['asset_key']]
   for kind in ('master','render'):
    if hashlib.sha256((ROOT/a[kind+'_path']).read_bytes()).hexdigest()!=a[kind+'_sha256']:issues.append({'kind':'cache_hash_mismatch','asset':p['asset_key']})
   if p['asset_key'] not in renders:renders[p['asset_key']]=json.loads((ROOT/a['render_path']).read_text())
   render=renders[p['asset_key']];origin=[p['position_m'][0],p['position_m'][2]];y=p['position_m'][1];yaw=p['yaw_rad']
   for group in render['groups']:
    target=rd if group['material'].startswith('slate') else bd
    for quad in group['quads']:
     points=[]
     for q in quad:
      x,z=transform([q[0],q[2]],origin,yaw);points.append(tuple(S*v for v in terrain.project(x,y+q[1],z)))
     target.polygon(points,fill=1)
  import PIL.ImageChops as ops
  inside=ops.logical_and(roof,ground);projection[label]={'actual_cached_roof_surface_union_px2':sum(bool(v) for v in roof.getdata())/(S*S),'actual_nonroof_surface_union_px2':sum(bool(v) for v in body.getdata())/(S*S),'roof_union_inside_projected_block_px2':sum(bool(v) for v in inside.getdata())/(S*S),'projected_block_ground_px2':sum(bool(v) for v in ground.getdata())/(S*S),'roof_union_inside_block_ratio':sum(bool(v) for v in inside.getdata())/sum(bool(v) for v in ground.getdata())};masks[label]=roof
 report={'schema':'riverstone.density_native_geometry_review.v1','candidate':ref(HERE/'candidate.json'),'issues':issues,'valid_horizontal_source':not issues,'actual_body_area_recomputed_m2':bodyarea,'intentional_internal_roof_intersection_pair_area_m2':internal_roof_overlap,'source_containment_and_path_tests':f"All{len(members)} actual native body envelopes and all{len(d['access_proposals'])} cached doorway links checked, plus2 court links. Roof intersections allowed only within a declared future common-union group.",'projection':projection,'projection_method':'Union raster of every immutable coarse-cache roof-material quad transformed at its native rigid pose, using the registered camera,2x pixel sampling. This is a genuine geometry projection, not concept-image segmentation; hidden-surface occlusion by nonroof objects is not removed.','limits':['Group common unions are not compiled yet.','Finished-floor ownership and capsule/cart traversal are not certified.']}
 write(HERE/'geometry_review.json',report)
 fig,axes=plt.subplots(1,2,figsize=(15,9),constrained_layout=True)
 for ax,label,placements in [(axes[0],'Before: tiny detached native houses',before),(axes[1],'After: native attached rows and connected courts',members)]:
  ax.add_patch(Polygon(d['block']['polygon_xz_m'],facecolor='#ddd4bb',edgecolor='#433e35',linewidth=1.5))
  for road in roads.values():
   for a,b in zip(road['polyline_xz_m'],road['polyline_xz_m'][1:]):ax.add_patch(Polygon(geo.road_ribbon(a,b,road['width_m']),facecolor='#f8f2de',edgecolor='none'))
  for p in placements:
   ax.add_patch(Polygon(p['actual_outer_footprint_xz_m'],facecolor='#bd7654',edgecolor='#75432d',alpha=.75,linewidth=.5));ax.add_patch(Polygon(p['actual_body_footprint_xz_m'],facecolor='#8d4b33',edgecolor='none',alpha=.85))
  if label.startswith('After'):
   for c in d['courts']:ax.add_patch(Polygon(c['polygon_xz_m'],facecolor='#a8b18a',edgecolor='#526043'));q=c['polygon_xz_m'];ax.text(sum(p[0] for p in q)/4,sum(p[1] for p in q)/4,'Shared\ncourt',fontsize=7,ha='center',va='center')
   for p in d['court_paths']:
    for poly in p['reserved_polygons_xz_m']:ax.add_patch(Polygon(poly,facecolor='#f7dc94',edgecolor='none'))
   for p in d['access_proposals']:
    xs,zs=zip(*p['complete_proposed_connection_xz_m']);ax.plot(xs,zs,color='#264c62',linewidth=.6)
  q=d['block']['polygon_xz_m'];ax.set_xlim(min(p[0] for p in q)-5,max(p[0] for p in q)+5);ax.set_ylim(max(p[1] for p in q)+5,min(p[1] for p in q)-5);ax.set_aspect('equal');ax.set_title(label)
 axes[0].text(.02,.02,f"Body {d['summary']['before_body_coverage']:.1%} | outer roof {d['summary']['before_outer_coverage']:.1%}",transform=axes[0].transAxes,bbox={'facecolor':'white','alpha':.8});axes[1].text(.02,.02,f"Body {d['summary']['after_body_coverage']:.1%} | outer roof {d['summary']['after_outer_coverage']:.1%}\nSource-only: native row unions still need compilation",transform=axes[1].transAxes,bbox={'facecolor':'white','alpha':.8});fig.suptitle('BLOCK_015_EAST | Registered streets preserved | Actual native module bounds',fontsize=15);fig.savefig(HERE/'block015_east_comparison.png',dpi=140);plt.close(fig)
 bb=ground.getbbox();crop=(bb[0]-40,bb[1]-60,bb[2]+40,bb[3]+30)
 for label,mask in masks.items():
  im=Image.new('RGB',canvas,'#eee8d6');im.paste('#d3c9ad',mask=ground);im.paste('#975536',mask=mask);im.crop(crop).save(HERE/f'roof_projection_{label}.png')
 print(json.dumps({'valid':not issues,'issue_count':len(issues),'projection':projection},indent=2))
if __name__=='__main__':run()
