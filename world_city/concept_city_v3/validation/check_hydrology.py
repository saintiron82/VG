#!/usr/bin/env python3
"""Independent fictional water-graph/head and finite-surface consistency audit.
This is not hydraulic, flood, structural, capacity or water-quality certification.
"""
import argparse,hashlib,json,math
from collections import Counter,defaultdict
from pathlib import Path
import geometry as g
HERE=Path(__file__).resolve().parent;CITY=HERE.parent

def directed_cycles(nodes,adj):
 """Find back-edge cycles even when a cycle is reachable from a valid source."""
 state={};stack=[];cycles=[]
 def visit(node):
  state[node]=1;stack.append(node)
  for target in adj[node]:
   if state.get(target)==1:cycles.append(stack[stack.index(target):]+[target])
   elif not state.get(target):visit(target)
  stack.pop();state[node]=2
 for node in nodes:
  if not state.get(node):visit(node)
 return cycles

def check(path):
 raw=Path(path).read_bytes();sha=hashlib.sha256(raw).hexdigest();c=json.loads(raw);graph=c['water_graph'];nodes={v['id']:v for v in graph['nodes']};edges=graph['edges'];issues=[];warnings=[];adj=defaultdict(list);incoming=defaultdict(list)
 def issue(code,**data):issues.append({'code':code,**data})
 if len(nodes)!=len(graph['nodes']):issue('duplicate_water_node_ids')
 if len({v['id'] for v in edges})!=len(edges):issue('duplicate_water_edge_ids')
 drops=[]
 for edge in edges:
  if edge['source'] not in nodes or edge['target'] not in nodes:issue('unknown_water_edge_endpoint',edge_id=edge['id']);continue
  a,b=nodes[edge['source']],nodes[edge['target']];drop=a['head_y_m']-b['head_y_m'];mode=edge.get('mode','gravity')
  if mode in ('gravity','wheel_head_drop') and drop<=0:issue('non_downhill_gravity_edge',edge_id=edge['id'],drop_m=drop)
  elif mode=='manual_lift' and not edge.get('energy_source'):issue('manual_lift_missing_energy_source',edge_id=edge['id'])
  elif mode not in ('gravity','wheel_head_drop','manual_lift'):issue('unrecognized_water_transfer_mode',edge_id=edge['id'],mode=mode)
  if a['network'] in ('industrial_nonpotable','storm','contained_waste') and b['network'] in ('protected_supply','raw_clean_source'):issue('dirty_to_clean_network_connection',edge_id=edge['id'])
  adj[a['id']].append(b['id']);incoming[b['id']].append(a['id']);drops.append({'edge_id':edge['id'],'head_drop_m':drop,'mode':mode})
 def reachable(seed):
  found={seed};todo=[seed]
  while todo:
   for n in adj[todo.pop()]:
    if n not in found:found.add(n);todo.append(n)
  return found
 roots=[id for id in nodes if not incoming[id]];reach={root:reachable(root) for root in roots}
 cycles=directed_cycles(nodes,adj)
 if cycles:issue('directed_water_cycles',cycles=cycles)
 orphaned=[id for id in nodes if not any(id in ids for ids in reach.values())]
 if orphaned:issue('water_cycle_or_source_orphans',node_ids=orphaned)
 deliveries={id:sorted(root for root,ids in reach.items() if id in ids) for id,n in nodes.items() if 'draw' in n['kind']}
 for id,rs in deliveries.items():
  if not rs:issue('draw_has_no_source',node_id=id)
  if any(nodes[root]['network'] not in ('raw_clean_source','protected_supply') for root in rs):issue('draw_has_nonclean_source_ancestor',node_id=id,root_ids=rs)
 intakes=[id for id,n in nodes.items() if n['kind']=='river_intake'];outfalls=[id for id,n in nodes.items() if n['kind']=='river_outfall']
 for id in intakes:
  if not set(outfalls).intersection(reachable(id)):issue('intake_has_no_outfall',node_id=id)
 for id,n in nodes.items():
  if n['network']=='storm' and not set(outfalls).intersection(reachable(id)):issue('storm_node_has_no_outfall',node_id=id)
  if n['network']=='contained_waste' and set(outfalls).intersection(reachable(id)):issue('contained_waste_has_river_discharge',node_id=id)
 surfaces=c['water_surfaces'];river=next(v for v in surfaces if v['id']=='MAIN_RIVER')
 def river_head(p):
  a,b=river['polyline_xz_m'];d,q,t=g.closest_point(p,a,b);return river['levels_m'][0]+t*(river['levels_m'][1]-river['levels_m'][0]),d
 terminals=[]
 for id in intakes+outfalls:
  n=nodes[id];head,dist=river_head(n['xz_m']);delta=n['head_y_m']-head
  terminals.append({'node_id':id,'source_node_head_m':n['head_y_m'],'receiving_river_head_m':head,'delta_m':delta,'distance_to_river_center_m':dist})
  if dist>river['width_m']/2+1e-6:issue('river_terminal_outside_river',node_id=id)
  if n['kind']=='river_intake' and n['head_y_m']>head+.02:issue('intake_requires_unstated_lift',node_id=id,delta_m=delta)
  if n['kind']=='river_outfall' and n['head_y_m']<head-.02:issue('outfall_below_receiving_normal_stage',node_id=id,delta_m=delta)
 # Open water drawings with overlapping domains and differing heads need explicit
 # confluence/drop/liner review; monotonic graph heads alone cannot prove them.
 def samples(surface,spacing=2):
  if 'polyline_xz_m' not in surface:return []
  out=[]
  for i,(a,b) in enumerate(zip(surface['polyline_xz_m'],surface['polyline_xz_m'][1:])):
   n=max(1,math.ceil(math.dist(a,b)/spacing))
   out += [([a[0]+(b[0]-a[0])*j/n,a[1]+(b[1]-a[1])*j/n],surface['levels_m'][i]+(surface['levels_m'][i+1]-surface['levels_m'][i])*j/n) for j in range(n)]
  return out
 def head_at(surface,point):
  if 'polygon_xz_m' in surface:return surface['water_y_m'] if g.point_inside(point,surface['polygon_xz_m']) else None
  hits=[]
  for i,(a,b) in enumerate(zip(surface['polyline_xz_m'],surface['polyline_xz_m'][1:])):
   d,q,t=g.closest_point(point,a,b)
   if d<=surface['width_m']/2+1e-8:hits.append(surface['levels_m'][i]+t*(surface['levels_m'][i+1]-surface['levels_m'][i]))
  return max(hits) if hits else None
 for i,a in enumerate(surfaces):
  for b in surfaces[i+1:]:
   mismatches=[]
   for p,y in samples(a)+samples(b):
    ya,yb=head_at(a,p),head_at(b,p)
    if ya is not None and yb is not None and abs(ya-yb)>.05:mismatches.append({'point_xz_m':p,'a_head_m':ya,'b_head_m':yb,'difference_m':abs(ya-yb)})
   if mismatches:warnings.append({'code':'overlapping_open_water_head_mismatch','surface_a':a['id'],'surface_b':b['id'],'sample_count':len(mismatches),'maximum_difference_m':max(x['difference_m'] for x in mismatches),'worst_sample':max(mismatches,key=lambda x:x['difference_m']),'requires':'explicit finite inlet/outfall/drop geometry; not proof of hydraulic failure'})
 sourcepath=HERE/'evidence'/'sources'/('water_'+sha+'.json');sourcepath.parent.mkdir(parents=True,exist_ok=True);sourcepath.write_bytes(raw)
 return {'schema':'riverstone.concept_city.independent_hydrology_validation.v1','graph_status':'pass' if not issues else 'fail','status':'pass_with_geometry_warnings' if warnings and not issues else 'pass' if not issues else 'fail',
 'source':{'path':str(Path(path).resolve()),'sha256':sha,'snapshot':str(sourcepath)},'checker_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'geometry_sha256':hashlib.sha256((HERE/'geometry.py').read_bytes()).hexdigest(),
 'counts':{'nodes':len(nodes),'edges':len(edges),'issues':len(issues),'warnings':len(warnings)},'issues':issues,'warnings':warnings,
 'checks':{'head_drops':drops,'roots':roots,'cycles':cycles,'source_to_draw':deliveries,'river_terminals':terminals,'all_intakes_reach_outfall':all(set(outfalls)&reachable(id) for id in intakes)},
 'limitations':['Fictional graph/head consistency only, not hydraulic simulation.','Water quality, flood/backwater, drought yield, pressure/capacity, embankment safety and conduit alignments remain unverified.','Source-only stair hooks are not compiled/collision-tested stairs.']}
if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('--contract',type=Path,default=CITY/'topography/contract.json');ap.add_argument('--output',type=Path);a=ap.parse_args();r=check(a.contract);out=a.output or HERE/'evidence'/('water_'+r['source']['sha256'][:12]+'_'+r['checker_sha256'][:8]+'.json');out.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({'status':r['status'],'counts':r['counts'],'issues':r['issues'],'warnings':r['warnings'],'output':str(out)},indent=2));raise SystemExit(0 if r['graph_status']=='pass' else 2)
