#!/usr/bin/env python3
"""Read-only bounded check of the proposed castle-road endpoint repair.

Does not edit source or certify capsule behavior. Proposed new gate link is a
6 m wide access reservation through the authored 10 m tower gap.
"""
import hashlib,importlib.util,json,math,sys
from pathlib import Path
import geometry as g
HERE=Path(__file__).resolve().parent;CITY=HERE.parent
sys.path.insert(0,str(CITY.parents[1]))

def check():
 path=CITY/'source/plan.json';raw=path.read_bytes();plan=json.loads(raw)
 author_path=CITY/'topography/author.py';author_raw=author_path.read_bytes();spec=importlib.util.spec_from_file_location('castle_proposal_height_target',author_path);author=importlib.util.module_from_spec(spec);spec.loader.exec_module(author)
 castle=next(a for a in plan['landmark_components'] if a['id']=='castle');anchor=castle['world_anchor_xyz_m']
 road=next(r for r in plan['roads'] if r['id']=='R_CASTLE')
 proposed=[[-300,-170]]+road['polyline_xz_m'][1:]
 paths=[{'id':'R_CASTLE_candidate','points':proposed,'width_m':road['width_m']},{'id':'actual_castle_gate_link_candidate','points':[[-300,-178],[-300,-170]],'width_m':6.0}]
 issues=[];overhead=[];intersections=[];minimum_tower_clearance=1e9
 for route in paths:
  for segment,(a,b) in enumerate(zip(route['points'],route['points'][1:])):
   strip=g.ribbon(a,b,route['width_m'])
   for mass in castle['masses']:
    if mass.get('bounds_baked_to_anchor_axes'):
     lo=[mass['bounds_local_m']['min'][i]+anchor[i] for i in range(3)];hi=[mass['bounds_local_m']['max'][i]+anchor[i] for i in range(3)]
     polygon=[[lo[0],lo[2]],[hi[0],lo[2]],[hi[0],hi[2]],[lo[0],hi[2]]]
    else:
     center=[mass['position_local_xyz_m'][i]+anchor[i] for i in range(3)];size=mass['size_xyz_m'];yaw=math.radians(mass.get('yaw_degrees',0));polygon=[[center[0]+x*math.cos(yaw)+z*math.sin(yaw),center[2]-x*math.sin(yaw)+z*math.cos(yaw)] for x,z in [(-size[0]/2,-size[2]/2),(size[0]/2,-size[2]/2),(size[0]/2,size[2]/2),(-size[0]/2,size[2]/2)]];lo=[0,center[1]-size[1]/2,0];hi=[0,center[1]+size[1]/2,0]
    if mass['id'].startswith('gate_tower'):
     distance=min(g.segment_distance(p,q,r,s)[0] for p,q in zip(strip,strip[1:]+strip[:1]) for r,s in zip(polygon,polygon[1:]+polygon[:1]));minimum_tower_clearance=min(minimum_tower_clearance,distance)
    overlap=g.intersection_area(strip,polygon)
    if overlap<1e-6:continue
    intersection=g.convex_intersection(strip,polygon)
    heights=[author.road_height_at('R_CASTLE',*p) for p in intersection]
    headroom=lo[1]-max(heights)
    row={'route_id':route['id'],'segment':segment,'component_id':mass['id'],'overlap_area_m2':overlap,'minimum_headroom_m':headroom,'component_y_range_m':[lo[1],hi[1]]};intersections.append(row)
    if headroom>=1.9:overhead.append(row)
    elif hi[1]>min(heights)+.05:issues.append(row)
 report={'schema':'riverstone.concept_city.castle_endpoint_proposal.v1','status':'pass' if not issues else 'fail','source_sha256':hashlib.sha256(raw).hexdigest(),'height_api_sha256':hashlib.sha256(author_raw).hexdigest(),'checker_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'source_applied':False,
 'proposal':{'existing_road_points':road['polyline_xz_m'],'candidate_road_points':proposed,'candidate_gate_link':paths[1],'authored_gate_tower_gap_width_m':10.0},
 'checks':{'candidate_paths':len(paths),'castle_component_envelopes':len(castle['masses']),'walking_height_conflicts':issues,'overhead_intersections':overhead,'minimum_candidate_strip_to_gate_tower_clearance_m':minimum_tower_clearance},
 'limitations':['Only the bounded proposed road endpoint and gate link against castle component envelopes.','Six-metre path corridor leaves two metres each side within the ten-metre tower gap.','No source edit, visual approval, actual collision or controller traversal result.','All other superseded landmark parent paths remain unresolved until replaced by actual access contracts.']}
 output=HERE/'evidence'/('castle_proposal_'+report['source_sha256'][:12]+'_'+report['checker_sha256'][:8]+'.json');output.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({'status':report['status'],'checks':report['checks'],'output':str(output)},indent=2))

if __name__=='__main__':check()
