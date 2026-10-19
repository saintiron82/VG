#!/usr/bin/env python3
"""Independent frozen registered-water graph, finite joins and wall datum audit."""
import argparse,hashlib,importlib.util,json,math,sys
from pathlib import Path
from collections import defaultdict
import geometry as g
from check_registration import project_xyz
from check_hydrology import directed_cycles
HERE=Path(__file__).resolve().parent;CITY=HERE.parent;ROOT=CITY.parents[1]
sys.path.insert(0,str(ROOT))

def shared_edge(a,b,c,d):
 length=math.dist(a,b)
 if length<1e-8:return None
 ab=g.sub(b,a)
 if abs(g.cross(ab,g.sub(c,a)))/length>1e-6 or abs(g.cross(ab,g.sub(d,a)))/length>1e-6:return None
 den=length*length;tc=sum((c[k]-a[k])*ab[k] for k in (0,1))/den;td=sum((d[k]-a[k])*ab[k] for k in (0,1))/den
 lo=max(0,min(tc,td));hi=min(1,max(tc,td))
 if (hi-lo)*length<1e-6:return None
 return [[a[k]+t*ab[k] for k in (0,1)] for t in (lo,hi)]
def edge_height(point,a,b,ya,yb):
 _,_,t=g.closest_point(point,a,b);return ya+(yb-ya)*t

def main():
 parser=argparse.ArgumentParser();parser.add_argument('--plan',type=Path,default=CITY/'registered_source/plan.json');parser.add_argument('--contract',type=Path,default=CITY/'registered_topography/contract.json');parser.add_argument('--author',type=Path,default=CITY/'registered_topography/author.py');args=parser.parse_args()
 paths={'plan':args.plan.resolve(),'contract':args.contract.resolve(),'author':args.author.resolve(),'road_controls':CITY/'registered_source/road_controls.json','registration':CITY/'image_registration/controls.json','polygon_dependency':ROOT/'world_city/runtime_city/checks/placement.py'}
 raw={k:p.read_bytes() for k,p in paths.items()};hashes={k:hashlib.sha256(v).hexdigest() for k,v in raw.items()};c=json.loads(raw['contract']);plan=json.loads(raw['plan']);issues=[];warnings=[]
 def issue(code,**kw):issues.append({'code':code,**kw})
 for field,key in [('source_plan_sha256','plan'),('controls_sha256','registration'),('road_controls_sha256','road_controls')]:
  if c[field]!=hashes[key]:issue('contract_binding_mismatch',field=field)
 spec=importlib.util.spec_from_file_location('registered_water_audit_api',paths['author']);a=importlib.util.module_from_spec(spec);spec.loader.exec_module(a)
 if a.CONTROLS_SHA256!=hashes['registration'] or a.ROAD_CONTROLS_SHA256!=hashes['road_controls']:issue('imported_inputs_mismatch')
 domains=c['water_domain_polygons'];api_domains=a.finite_water_polygons()
 if domains!=api_domains:issue('contract_actual_api_domains_mismatch')
 # Nonoverlap is geometric, independent of the author's boolean implementation.
 overlaps=[];shared=[];boxes=[g.bounds(d['polygon_xz_m']) for d in domains]
 for i,d in enumerate(domains):
  p=d['polygon_xz_m']
  for j,e in enumerate(domains[:i]):
   if not g.bbox_overlap(boxes[i],boxes[j]):continue
   q=e['polygon_xz_m'];area=g.intersection_area(p,q)
   if area>1e-6:overlaps.append({'a':i,'b':j,'surface_a':d['surface_id'],'surface_b':e['surface_id'],'area_m2':area})
   for k,(v,w) in enumerate(zip(p,p[1:]+p[:1])):
    for l,(x,y) in enumerate(zip(q,q[1:]+q[:1])):
     edge=shared_edge(v,w,x,y)
     if edge:shared.append((i,j,k,l,edge))
 if overlaps:issue('positive_area_water_ownership_overlaps',records=overlaps)
 join_summary=defaultdict(lambda:{'segments':0,'sample_count':0,'length_m':0.,'maximum_api_head_delta_m':0.,'maximum_vertex_edge_interp_delta_m':0.})
 for i,j,k,l,edge in shared:
  d,e=domains[i],domains[j];key=' | '.join(sorted([d['surface_id'],e['surface_id']]));rec=join_summary[key];rec['segments']+=1;length=math.dist(*edge);rec['length_m']+=length
  p,q=d['polygon_xz_m'],e['polygon_xz_m'];n=max(1,math.ceil(length/.25))
  for station in range(n+1):
   point=[edge[0][h]+(edge[1][h]-edge[0][h])*station/n for h in (0,1)];y1=a.water_height_at(d['surface_id'],*point,d.get('segment_index',0));y2=a.water_height_at(e['surface_id'],*point,e.get('segment_index',0));rec['sample_count']+=1;rec['maximum_api_head_delta_m']=max(rec['maximum_api_head_delta_m'],abs(y1-y2))
   yy1=edge_height(point,p[k],p[(k+1)%len(p)],d['vertex_y_m'][k],d['vertex_y_m'][(k+1)%len(p)]);yy2=edge_height(point,q[l],q[(l+1)%len(q)],e['vertex_y_m'][l],e['vertex_y_m'][(l+1)%len(q)]);rec['maximum_vertex_edge_interp_delta_m']=max(rec['maximum_vertex_edge_interp_delta_m'],abs(yy1-yy2))
 for key,rec in join_summary.items():
  if rec['maximum_api_head_delta_m']>1e-5:issue('shared_water_boundary_api_discontinuity',surfaces=key,**rec)
  if rec['maximum_vertex_edge_interp_delta_m']>.001:warnings.append({'code':'contract_vertex_only_mesh_edge_discontinuity','surfaces':key,**rec})
 required=[('SPRING_VISIBLE','NORTHERN_RESERVOIR'),('NORTHERN_CHANNEL_VISIBLE','NORTHERN_RESERVOIR'),('CRAFT_CANAL_VISIBLE','EAST_CHANNEL_VISIBLE'),('EAST_CHANNEL_VISIBLE','MAIN_RIVER')]
 for pair in required:
  key=' | '.join(sorted(pair))
  if key not in join_summary:issue('required_full_width_water_join_missing',surfaces=pair)
 # API heights, not nominal drawing levels, determine the realized image trace.
 projection=[]
 for w in c['water_surfaces']:
  if 'trace_pixel_xy' not in w:continue
  err=[];stored=[]
  for i,(p,pixel) in enumerate(zip(w['polyline_xz_m'],w['trace_pixel_xy'])):
   y=a.water_height_at(w['id'],*p);err.append(math.dist(project_xyz(c['camera_model'],[p[0],y,p[1]]),pixel));stored.append(abs(y-w['resolved_world_xyz_m'][i][1]))
  row={'surface_id':w['id'],'maximum_api_height_projection_residual_px':max(err),'maximum_contract_api_height_delta_m':max(stored)};projection.append(row)
  if max(stored)>1e-7:issue('stored_realized_water_height_mismatch',**row)
  if max(err)>.001:warnings.append({'code':'actual_water_api_shifts_nominal_image_trace',**row})
 # Source graph reachability, head directions and explicit energy.
 nodes={n['id']:n for n in c['water_graph']['nodes']};edges=c['water_graph']['edges'];adj=defaultdict(list);incoming=defaultdict(list);drops=[]
 for index,e in enumerate(edges):
  if e['source'] not in nodes or e['target'] not in nodes:issue('unknown_graph_endpoint',edge=index);continue
  n,m=nodes[e['source']],nodes[e['target']];drop=n['head_y_m']-m['head_y_m'];mode=e['mode'];drops.append({'edge':index,'source':n['id'],'target':m['id'],'drop_m':drop,'mode':mode})
  if mode=='gravity' and drop<=0:issue('non_downhill_gravity_edge',edge=index,drop_m=drop)
  elif mode=='level_join' and abs(drop)>e.get('head_tolerance_m',0):issue('incompatible_level_join',edge=index,drop_m=drop)
  elif mode=='manual_lift' and not e.get('energy_source'):issue('unstated_lift_energy',edge=index)
  elif mode not in ['gravity','level_join','manual_lift']:issue('unknown_transfer_mode',edge=index,mode=mode)
  if n['network']=='industrial_nonpotable' and m['network'] in ['raw_source','raw_storage','protected_supply']:issue('dirty_to_clean_link',edge=index)
  adj[n['id']].append(m['id']);incoming[m['id']].append(n['id'])
 def reachable(seed):
  found={seed};todo=[seed]
  while todo:
   for target in adj[todo.pop()]:
    if target not in found:found.add(target);todo.append(target)
  return found
 cycles=directed_cycles(nodes,adj)
 if cycles:issue('directed_water_cycle',cycles=cycles)
 roots=[n for n in nodes if not incoming[n]];reaches={n:reachable(n) for n in roots};deliveries={n:sorted(r for r,v in reaches.items() if n in v) for n in nodes if n.endswith('_DRAW')}
 for n,rs in deliveries.items():
  if not rs:issue('draw_has_no_source',node=n)
 for n in nodes:
  if nodes[n]['network']=='industrial_nonpotable' and 'RIVER_OUTFALL' not in reachable(n):issue('industrial_node_has_no_outfall',node=n)
 outfall=nodes['RIVER_OUTFALL'];receiver=a.river_water_y(outfall['xz_m'][0]);delta=outfall['head_y_m']-receiver
 if delta<-.02:issue('outfall_below_normal_receiving_head',delta_m=delta)
 # Actual per-wall vertices and midpoint ground datums. Road/gate conflicts are
 # retained rather than assuming all wall anchors share a flat bench.
 wall=c['registered_wall'];xyz=wall['world_xyz_m'];wall_rows=[]
 for i,(p,q) in enumerate(zip(xyz,xyz[1:]+xyz[:1])):
  for t in [0,.25,.5,.75]:
   point=[p[k]+(q[k]-p[k])*t for k in range(3)];actual=a.land_height_at(point[0],point[2]);err=abs(actual-point[1]);wall_rows.append({'segment':i,'station':t,'point_xyz_m':point,'actual_ground_y_m':actual,'delta_m':err})
 max_wall=max(row['delta_m'] for row in wall_rows)
 if max_wall>1e-5:issue('wall_datum_ground_mismatch',maximum_delta_m=max_wall,worst=max(wall_rows,key=lambda r:r['delta_m']))
 # Verify finite bed ownership and bank top/bottom API values from the contract.
 banks=c['water_support']['exterior_banks'];bed_error=0.;bank_top_error=0.;bank_bottom_error=0.;minimum_freeboard=math.inf
 for bed in c['water_support']['beds']:
  for p,y in zip(bed['polygon_xz_m'],bed['vertex_y_m']):bed_error=max(bed_error,abs(y-(a.water_height_at(bed['surface_id'],*p)-bed['bed_depth_m'])))
 for bank in banks:
  for index,p in enumerate([bank['from_xz_m'],bank['to_xz_m']]):
   top=a.land_height_at(*p);water=a.water_height_at(bank['surface_id'],*p);bank_top_error=max(bank_top_error,abs(top-bank['top_y_m'][index]));minimum_freeboard=min(minimum_freeboard,top-water)
   depth=3 if bank['surface_id']=='MAIN_RIVER' else 2.4 if bank['surface_id']=='NORTHERN_RESERVOIR' else a.WATER_BY_ID[bank['surface_id']]['bed_depth_m'];bank_bottom_error=max(bank_bottom_error,abs(bank['bottom_y_m'][index]-(water-depth)))
 if max(bed_error,bank_top_error,bank_bottom_error)>1e-7:issue('water_support_contract_api_disagrees',bed_error_m=bed_error,bank_top_error_m=bank_top_error,bank_bottom_error_m=bank_bottom_error)
 if minimum_freeboard<0:issue('bank_top_below_normal_stage',minimum_freeboard_m=minimum_freeboard)
 sources={}
 for k,data in raw.items():
  snapshot=HERE/'evidence/sources'/('registered_water_'+k+'_'+hashes[k]+paths[k].suffix);snapshot.write_bytes(data);sources[k]={'path':str(paths[k].relative_to(ROOT)),'sha256':hashes[k],'snapshot':str(snapshot.relative_to(ROOT))}
  if paths[k].read_bytes()!=data:issue('input_changed_during_audit',input=k)
 checker=hashlib.sha256(Path(__file__).read_bytes()).hexdigest();report={'schema':'riverstone.registered_water.independent_audit.v1','status':'fail' if issues else 'pass_with_geometry_warnings' if warnings else 'pass','sources':sources,'checker_sha256':checker,'counts':{'domains':len(domains),'shared_edges':len(shared),'join_samples':sum(r['sample_count'] for r in join_summary.values()),'bank_segments':len(banks),'wall_samples':len(wall_rows),'graph_nodes':len(nodes),'graph_edges':len(edges)},'water_joins':dict(join_summary),'realized_water_projection':projection,'graph':{'head_drops':drops,'roots':roots,'draw_sources':deliveries,'cycles':cycles,'outfall_minus_receiving_stage_m':delta},'support':{'maximum_wall_datum_error_m':max_wall,'minimum_bank_freeboard_m':minimum_freeboard,'maximum_bed_error_m':bed_error,'maximum_bank_top_error_m':bank_top_error,'maximum_bank_bottom_error_m':bank_bottom_error},'issues':issues,'warnings':warnings,'limits':['Source API and finite contract geometry only; no common voxel terrain or collision pass.','Vertex-only water mesh interpolation is checked separately from the continuous API.','Hydraulic capacity, flooding/backwater, erosion and drinking-water quality remain unverified.','Gravity graph consistency does not prove a physically built covered conduit.']}
 out=HERE/'evidence'/('registered_water_'+hashes['contract'][:12]+'_'+checker[:12]+'.json');out.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({'status':report['status'],'report':str(out),'counts':report['counts'],'support':report['support'],'issues':issues,'warnings':warnings},indent=2));raise SystemExit(2 if issues else 0)

if __name__=='__main__':main()
