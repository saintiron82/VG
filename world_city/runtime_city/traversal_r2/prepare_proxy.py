#!/usr/bin/env python3
"""Finite exact source-grade collision candidate; visual common-voxel meshes unchanged."""
import argparse,copy,json,math,sys
from pathlib import Path
import prepare as base
from prepare_candidate import control_asset
ROOT=base.ROOT;HERE=base.HERE
sys.path.insert(0,str(ROOT))
from world_city.runtime_city.topography import author as a

def visual_error(layer,field,bounds):
 columns={};maximum=0.;worst=None
 for placement in layer['placements']:
  if placement['category']!='fine_walk_surface':continue
  asset=layer['assets'][placement['asset_key']];path=ROOT/asset['render_path']
  if base.digest(path)!=asset['render_sha256']:raise ValueError('Fine visual asset changed')
  render=base.read(path);pitch=render['pitch']
  for group in render['groups']:
   for q in group['quads']:
    if max(v[1] for v in q)-min(v[1] for v in q)>1e-8:continue
    u,v,w=q[:3];crossy=(v[2]-u[2])*(w[0]-u[0])-(v[0]-u[0])*(w[2]-u[2])
    if crossy<=0:continue
    x0,x1=round(min(v[0] for v in q)/pitch),round(max(v[0] for v in q)/pitch)
    z0,z1=round(min(v[2] for v in q)/pitch),round(max(v[2] for v in q)/pitch)
    for ix in range(x0,x1):
     for iz in range(z0,z1):
      x,z=(ix+.5)*pitch,(iz+.5)*pitch;y=u[1]
      if not bounds[0]<x<bounds[2] or not bounds[1]<z<bounds[3]:raise ValueError('Visual cap outside proxy bounds')
      if (ix,iz) in columns:raise ValueError('Duplicate visible cap column')
      columns[ix,iz]=y;error=abs(y-field.height(x,z))
      if error>maximum:maximum=error;worst=[x,z,y,field.height(x,z)]
 expected=round((bounds[2]-bounds[0])*(bounds[3]-bounds[1])/.01)
 if len(columns)!=expected:raise ValueError('Fine visible surface column gap')
 if maximum>.0500001:raise ValueError('Proxy/visual sampled error exceeds .05m')
 return {'visual_sampled_column_count':len(columns),'visual_column_missing_count':expected-len(columns),
         'max_source_proxy_vs_visual_center_error_m':maximum,'worst_sample_x_z_visual_y_proxy_y':worst,
         'sampling':'every actual upward fine render quad at global .1m cell centers; independent of cached source statistics'}

def prepare(scene_path,layer_path,out_path):
 p=base.prepare(scene_path,layer_path,out_path,True);layer=base.read(layer_path)
 source=base.read(ROOT/layer['source_plan_path']);field=a.GradeField(source['regions']);bounds=layer['tested_fine_region']['bounds_xz_m']
 facets=field.facets(a._rect(bounds));triangles=[];area=0.
 for facet in facets:
  poly=facet['polygon_xz_m'];area+=abs(a._area(poly));plane=facet['plane']
  verts=[[x,plane[0]*x+plane[1]*z+plane[2],z] for x,z in poly]
  # XZ counter-clockwise polygons have Godot clockwise upper front faces.
  for i in range(1,len(verts)-1):triangles.append([verts[0],verts[i],verts[i+1]])
 if abs(area-1024)>1e-6:raise ValueError('Proxy is not exact finite sample cover')
 stats=visual_error(layer,field,bounds)
 proxy={'schema':'riverstone.city.source_grade_collision_proxy.v1','optional_collision_only':True,'visual_meshes_changed':False,
   'bounds_xz_m':bounds,'area_m2':area,'triangles':triangles,'facets':facets,'source_plan_path':layer['source_plan_path'],
   'source_plan_sha256':layer['source_plan_sha256'],'source_layer_path':str(Path(layer_path).resolve()),
   'source_layer_sha256':base.digest(layer_path),'validation':stats,
   'policy':'Exact finite H facets. No analytic runtime movement, infinite plane, holes bridged, source stairs flattened, or common visual mesher changes.',
   'excluded_scope':'Outside fine sample; buildings, river masks and authored stairs must retain separate actual collision before any wider deployment.'}
 path=HERE/'proxy'/'fine_source_grade.json';base.write(path,proxy)
 visuals=copy.deepcopy(p['assets']);p['assets']={};p['placements']={};p['buildings']={}
 key='FINITE_FINE_SOURCE_GRADE';p['assets'][key]={'render_path':str(path.relative_to(ROOT)),'render_sha256':base.digest(path),'collision_format':'source_grade_proxy_triangles','triangle_count':len(triangles)}
 id='PROXY:'+key;p['placements'][id]={'id':id,'asset_key':key,'position_m':[0,0,0],'yaw_deg':0,'category':'source_grade_proxy','collision_layer':1}
 for route in p['routes']:route.update(placement_ids=[id],building_ids=[],test_scope='finite optional source-grade proxy; original no-step capsule')
 # Isolated actual-voxel obstacles test the candidate cannot erase real steps/walls.
 for rid,key,rise in [('NEGATIVE_AUTHORED_STEP_0P25','proxy_actual_step025',.25),('NEGATIVE_ACTUAL_SOLID_WALL','proxy_actual_wall',2.)]:
  p['assets'][key]=control_asset(key,[([-2,-.2,-2],[2,0,2]),([0,0,-2],[2,rise,2])]);ident='CONTROL:'+key
  p['placements'][ident]={'id':ident,'asset_key':key,'position_m':[0,0,0],'yaw_deg':0,'category':'isolated_actual_voxel_control','collision_layer':1}
  route=base.route_record(rid,[[-1,0],[1,0]],'negative_control',[],expected_failure='blocked',expected_contact_id=ident,
      test_scope='actual common-voxel obstacle; separate isolated fixture not covered by terrain proxy')
  route.update(placement_ids=[ident],building_ids=[]);p['routes'].append(route)
 for rid,xz in [('NEGATIVE_OUTSIDE_FINITE_PROXY',[[-580,-240],[-578,-240]]),('NEGATIVE_RIVER_HAS_NO_INFINITE_FLOOR',[[-700,490],[-698,490]])]:
  route=base.route_record(rid,xz,'negative_control',source['regions'],expected_failure='spawn_not_grounded',
      test_scope='finite proxy does not cover outside bounds or river')
  route.update(placement_ids=[id],building_ids=[]);p['routes'].append(route)
 p['schema']='riverstone.city.r2_source_grade_proxy_suite.v1'
 p['assumptions']['actual_ground']='optional exact finite source-grade collision proxy over same 1024m²; visual meshes unchanged; actual voxel controls remain actual'
 p['assumptions']['controller']='original generic capsule, no step-up'
 p['assumptions']['test_collision_policy']='source-grade proxy only inside declared sample; no wider deployment'
 p['proxy_validation']=stats;p['tested_visual_assets']=visuals
 for key in ['SourceGradeProxy.gd','SourceGradeProxy.tscn','prepare_proxy.py','prepare_candidate.py']:
  path=HERE/key;p['implementation_hashes'][str(path.relative_to(ROOT))]=base.digest(path)
 p['coverage']['route_count']=len(p['routes']);p['coverage']['proxy_area_m2']=area;p['coverage']['proxy_triangle_count']=len(triangles)
 p['coverage']['selected_collision_assets']=len(p['assets']);p['coverage']['selected_placements']=len(p['placements']);p['coverage']['selected_buildings']=0
 base.write(out_path,p);return p
if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('--scene',type=Path,default=ROOT/'world_city/runtime_city/generated/r2/scene.flat_property.json')
 ap.add_argument('--layers',type=Path,default=ROOT/'world_city/runtime_city/generated/r2_topography/fine_sample_manifest.json')
 ap.add_argument('--output',type=Path,default=HERE/'prepared.proxy.json');args=ap.parse_args();p=prepare(args.scene,args.layers,args.output)
 print(json.dumps({'coverage':p['coverage'],'validation':p['proxy_validation'],'sources':p['sources']},indent=2))
