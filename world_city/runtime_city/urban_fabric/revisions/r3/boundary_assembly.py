"""Union the existing short wall/post sources in one common solid on one world grid.

No mesh code. Per-module terrain Y remains explicit before ordinary common sampling.
"""
from __future__ import annotations
import copy,json,math
from pathlib import Path
from .author_overlay import HERE,ROOT,make_master,master_bounds,digest,yaw_basis,rect,World
from voxel_character.common import core
from voxel_character.common.coordinate_planes import compile_master
from world_city.runtime_city.checks.placement import positive_area_overlap,convex_intersection,polygon_area,_SpatialIndex
from .probe import offset


def make_boundary_assembly(data,property_id,placement_y_overrides=None,pitch_m=.5,scene=None):
 """Return a standard-common master; world placement lives in its metadata.

 `placement_y_overrides` maps individual source panel/post IDs to projected Y.
 Keep those ≤6 m source supports; combining sampling does not flatten their grade.
 """
 props={p['id']:p for p in data['property_records']};prop=props[property_id]
 ids=set(prop['wall_placement_ids']);items=[p for p in data['placements'] if p['id'] in ids]
 if len(items)!=len(ids):raise ValueError('Missing boundary source placements')
 points=prop['boundary_centerline_xz_m'];origin=[math.floor(sum(p[0] for p in points)/len(points)/pitch_m)*pitch_m,0,math.floor(sum(p[1] for p in points)/len(points)/pitch_m)*pitch_m]
 y_values=placement_y_overrides or {};unknown=set(y_values)-{p['id'] for p in data['placements']}
 if unknown:raise ValueError('Unknown projected source IDs: '+str(sorted(unknown)))
 ops=[];ledger=[];materials=None
 for p in items:
  master=make_master(p['spec']);materials=master['materials'];pos=p['position_m'][:];pos[1]=y_values.get(p['id'],pos[1])
  if not all(math.isfinite(v) for v in pos):raise ValueError('Non-finite projected pose')
  placement={'translation':[v-o for v,o in zip(pos,origin)],'basis':yaw_basis(p['yaw_rad'])};op_ids=[]
  for source_op in master['components'][0]['operations']:
   o=copy.deepcopy(source_op);o['id']=f'source_{len(ledger):03d}_{o["id"]}';o['part']='boundary_solid';o['transform']=core.compose(placement,core.transform(o.get('transform')));ops.append(o);op_ids.append(o['id'])
  ledger.append({'source_placement_id':p['id'],'source_master_key':p['master_key'],'source_spec':copy.deepcopy(p['spec']),'world_position_m':pos,'yaw_rad':p['yaw_rad'],'source_ground_anchor':copy.deepcopy(p['ground_anchor']),'operation_ids':op_ids})
 # A world-aligned sampled cube can extend half its diagonal beyond an oblique
 # source face. Clip source geometry against guarded immutable exclusions before
 # compilation. These are finite common-source polygon cuts, not cell/mesh repair.
 scene=scene or json.loads((ROOT/'world_city/runtime_city/generated/r2/scene.flat_property.json').read_text())
 world=World(scene);guard=pitch_m/math.sqrt(2)+.001;cut_ledger=[]
 estate_access=[a for a in data['access_reservations'] if a.get('gate_id','').startswith(property_id+':')]
 for p in items:
  support=offset(p['footprint_xz_m'],-guard);obstacles=[]
  for key in world.index.candidates(support):
   if world.items[key]['kind'] in ('building','road','river'):obstacles.append((key,world.items[key]['polygon']))
  obstacles.extend((g['id']+':full_gate_clearance',g['passage_polygon_xz_m']) for g in prop['gates'])
  for access in estate_access:
   obstacles.extend((access['id']+':'+str(i),q) for i,q in enumerate(access['ribbon_polygons_xz_m']))
  for target,poly in obstacles:
   expanded=offset(poly,-guard);clip=convex_intersection(support,expanded)
   if len(clip)<3 or polygon_area(clip)<1e-7:continue
   opid='clearance_'+str(len(cut_ledger)).zfill(4);py=y_values.get(p['id'],p['position_m'][1]);h=master_bounds(p['spec'])[2]
   shape={'kind':'extrusion','polygon':[[q[0]-origin[0],-(q[1]-origin[2])] for q in clip],'z_min':py-1.5,'z_max':py+h+.5}
   ops.append({'id':opid,'part':'boundary_solid','action':'cut','shape':shape,'transform':{'basis':[[1,0,0],[0,0,1],[0,-1,0]],'translation':[0,0,0]},'feature':'sampling_safe_immutable_clearance'})
   cut_ledger.append({'operation_id':opid,'source_placement_id':p['id'],'unchanged_exclusion_id':target,'guard_m':guard,'source_cut_polygon_xz_m':clip})
 master={'schema':'riverstone.voxel.master.v1','id':'uf_r3_boundary_'+property_id.lower()+'_'+digest(ledger)[:12],'revision':3,'axes':{'up':'+Y','front':'+Z','right':'+X'},'grid_origin':[0,0,0],'materials':materials,
         'components':[{'id':'boundary','parts':[{'id':'boundary_solid','pivot':[0,0,0]}],'operations':ops}],'instances':[{'id':'boundary_union','component':'boundary'}],
         'metadata':{'authoring':'existing_common_operations_composed_into_one_solid','property_id':property_id,'placement_position_m':origin,'placement_yaw_rad':0,'world_grid_origin_m':[0,0,0],'pitch_m':pitch_m,'source_placement_ids':[p['id'] for p in items],'source_operation_ledger':ledger,'clearance_cut_ledger':cut_ledger,'sampling_guard_m':guard,'gate_clearance_policy':'Original gate widths are minimum clear widths; guarded source cuts may flare mouths by at most one voxel diagonal.','gates':copy.deepcopy(prop['gates']),'boundary_centerline_xz_m':copy.deepcopy(prop['boundary_centerline_xz_m']),'source_overlay_digest':digest(data),'terrain_y_preprojected':bool(placement_y_overrides),'height_projection_contract':'Project each short source support first, pass Y map, then compile union; do not replace per-segment grade with one estate-wide flat anchor.'}}
 return master


def audit_sampled_boundary(master,result,scene,access_reservations):
 """Check actual occupied voxel squares against buildings/roads and gate access."""
 origin=master['metadata']['placement_position_m'];pitch=result['pitch'];world=World(scene);errors=[];access_index=_SpatialIndex(16);access_polys={}
 sourceids=set(master['metadata']['source_placement_ids']);property_id=master['metadata']['property_id']
 for a in access_reservations:
  for j,poly in enumerate(a['ribbon_polygons_xz_m']):
   key=a['id']+':'+str(j);access_index.add(key,poly);access_polys[key]=(a['id'],poly)
 squares={}
 for c in result['cells']:
  if (c[0],c[2]) in squares:continue
  x,z=origin[0]+(c[0]+.5)*pitch,origin[2]+(c[2]+.5)*pitch;squares[c[0],c[2]]=rect([x,z],pitch,pitch)
 for cell,poly in squares.items():
  hits=world.hits(poly,kinds=('building','road','river'))
  if hits:errors.append({'check':'sampled_boundary_source_obstacle','cell_xz':list(cell),'targets':hits})
  for key in access_index.candidates(poly):
   aid,q=access_polys[key]
   if positive_area_overlap(poly,q,.003):errors.append({'check':'sampled_boundary_access_obstruction','cell_xz':list(cell),'access_id':aid})
  for g in master['metadata']['gates']:
   if positive_area_overlap(poly,g['passage_polygon_xz_m'],.003):errors.append({'check':'sampled_gate_full_width_obstruction','cell_xz':list(cell),'gate_id':g['id']})
 # Exactly one connected arc between consecutive gates, with no stray wall islands.
 pending=set(squares);arc_sizes=[]
 while pending:
  queue=[pending.pop()];count=0
  while queue:
   x,z=queue.pop();count+=1
   for q in ((x+1,z),(x-1,z),(x,z+1),(x,z-1)):
    if q in pending:pending.remove(q);queue.append(q)
  arc_sizes.append(count)
 if len(arc_sizes)!=len(master['metadata']['gates']):errors.append({'check':'unexpected_sampled_boundary_arc_count','arc_sizes':arc_sizes})
 pending3={tuple(c[:3]) for c in result['cells']};solid_sizes=[]
 while pending3:
  queue=[pending3.pop()];count=0
  while queue:
   q=queue.pop();count+=1
   for n in core.neighbors(q):
    if n in pending3:pending3.remove(n);queue.append(n)
  solid_sizes.append(count)
 if len(solid_sizes)!=len(master['metadata']['gates']):errors.append({'check':'unexpected_3d_boundary_disconnection','solid_sizes':solid_sizes})
 return {'valid':not errors,'errors':errors,'source_modules':len(sourceids),'operations':len(master['components'][0]['operations']),'sampled_continuous_wall_arc_sizes':arc_sizes,'sampled_3d_connected_solid_sizes':solid_sizes,'expected_wall_arcs':len(master['metadata']['gates']),'occupied_cells':len(result['cells']),'candidate_cells':result['candidate_cells'],'single_instance':len({c[3] for c in result['cells']})==1,'single_solid_part':len({c[4] for c in result['cells']})==1,'one_cell_owner':len({tuple(c[:3]) for c in result['cells']})==len(result['cells'])}


def main():
 data=json.loads((HERE/'generated/overlay.json').read_text());base=json.loads((ROOT/'world_city/runtime_city/revisions/r3/urban_fabric.access_repaired.json').read_text());all_access=[a for a in base['access_reservations'] if a['id'] not in data['replacement_ledger']['remove_access_reservation_ids']]+data['access_reservations'];scene=json.loads((ROOT/'world_city/runtime_city/generated/r2/scene.flat_property.json').read_text());out=HERE/'generated/boundary_assemblies';out.mkdir(parents=True,exist_ok=True);reports={}
 for prop in data['property_records']:
  master=make_boundary_assembly(data,prop['id']);result=compile_master(master,{'pitch':.5},max_candidate_cells=250000,max_output_cells=100000);report=audit_sampled_boundary(master,result,scene,all_access);reports[prop['id']]=report
  (out/(prop['id']+'.master.json')).write_text(json.dumps(master,separators=(',',':'))+'\n')
 (out/'sampling_report.json').write_text(json.dumps(reports,indent=2)+'\n');print(json.dumps(reports,indent=2))
if __name__=='__main__':main()
