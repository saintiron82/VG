#!/usr/bin/env python3
"""Bind producer handoff and explicit bounded throat probes without changing full routes."""
import argparse,json,pathlib,hashlib,copy
H=pathlib.Path(__file__).resolve().parent;ROOT=next(p for p in H.parents if(p/'voxel_character').is_dir())
def sha(p):
 with p.open('rb')as f:return hashlib.file_digest(f,'sha256').hexdigest()
def ref(p):return {'path':str(p.resolve().relative_to(ROOT)),'sha256':sha(p)}
def write(p,d):
 with p.open('x')as f:json.dump(d,f,indent=2);f.write('\n')
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--routes',type=pathlib.Path,required=True);ap.add_argument('--patch',type=pathlib.Path,required=True);ap.add_argument('--pack',action='append',type=pathlib.Path,default=[]);ap.add_argument('--base-index',type=pathlib.Path,required=True);ap.add_argument('--source',action='append',type=pathlib.Path,default=[]);ap.add_argument('--output',type=pathlib.Path,required=True);a=ap.parse_args();out=a.output.resolve();assert out.is_relative_to(H)and not out.exists();out.mkdir();producer=json.loads(a.routes.read_bytes());index=json.loads(a.base_index.read_bytes());index['packs']+=list(map(ref,a.pack));write(out/'index.json',index)
 request={'schema':'riverstone.r9.gate_runtime_request.v1','base_scene':producer['base_scene'],'finite_patch':ref(a.patch),'visual_index':ref(out/'index.json')if a.pack else ref(a.base_index),'gates':producer['gates'],'routes':[],'producer_sources':{'routes':ref(a.routes),'base_visual_index':ref(a.base_index)},'cart_fixture':json.loads((H/'INPUT_CONTRACT.json').read_bytes())['cart_fixture'],'collision_margin_m':6.0}
 request['producer_sources'].update(producer.get('producer_sources',{}))
 for n,p in enumerate(a.source):request['producer_sources']['additional_'+str(n)]=ref(p)
 for original in producer['routes']:
  r=copy.deepcopy(original)
  if 'gate_waypoint_index'in r:r['gate_id']=next(g['id']for g in producer['gates']if g['id']in r['source_road_ids'])
  r['provenance']='Unchanged exact immutable producer route';r['both_directions']=True;r['cart_test']=True;request['routes'].append(r)
 for g in producer['gates']:
  group='WEST'if g['id'].startswith('WEST')else'EAST';c=g['opening_center_xyz_m'];f=g['travel_unit_xz'];t=[-f[1],f[0]]
  def point(longitudinal,lateral):return [c[0]+f[0]*longitudinal+t[0]*lateral,c[1],c[2]+f[1]*longitudinal+t[1]*lateral]
  for offset,label in [(-1.5,'LEFT'),(1.5,'RIGHT')]:
   stations=[[-10,0],[-6,offset],[-3,offset],[0,offset],[3,offset],[6,offset],[10,0]]
   request['routes'].append({'id':group+'_GATE_THROAT_OFFSET_'+label,'group':group,'points':[point(*p)for p in stations],'source_road_ids':[g['id']],'test_scope':'Bounded lateral throat probe, gate-frame offset '+str(offset)+' m; not full-width certification.','both_directions':True,'cart_test':True,'provenance':'QA probe derived from exact source gate frame','gate_frame_stations_longitudinal_lateral_m':stations})
  stations=[[-9,1],[-9,0],[-4,0],[0,0],[4,0],[9,0],[9,-1]]
  request['routes'].append({'id':group+'_GATE_THROAT_TURNS','group':group,'points':[point(*p)for p in stations],'source_road_ids':[g['id']],'test_scope':'Bounded one-metre transverse turns 9 m inside/outside the actual opening, both directions. Rigid cart pivot clearance only; no steering dynamics claim.','both_directions':True,'cart_test':True,'provenance':'QA probe derived from exact source gate frame','gate_frame_stations_longitudinal_lateral_m':stations})
 write(out/'request.json',request);print(json.dumps({'request':ref(out/'request.json'),'index':ref(out/'index.json'),'producer_routes':len(producer['routes']),'positive_directional_cases':len(request['routes'])*2,'negative_controls_added_by_preparation':2},indent=2))
if __name__=='__main__':main()
