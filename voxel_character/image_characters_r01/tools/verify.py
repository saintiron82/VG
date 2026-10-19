"""Verify source->master->selective common occupancy->render exact provenance.
No visual score is inferred from cell counts or these structural tests.
"""
from pathlib import Path
from collections import deque,Counter
import argparse,copy,gzip,hashlib,json,sys
from build import ROOT,COMMON,Author,read,sha,dump
from core import compile_master,digest,neighbors
from build_render import isolate
from render_data import make_render_data

def verify(directory,recompile=False):
 m=read(directory/'master.json');rig=read(directory/'rig.json');bind=read(directory/'bind.json');render=read(directory/'character.render.json');manifest=read(directory/'manifest.json')
 assert digest(m)==manifest['master_hash']==rig['master_hash']==bind['master_hash']==render['master_hash']
 assert sha(directory/'character.render.json')==manifest['render_sha256']
 p=m['extensions']['provenance'];assert sha(ROOT/p['reference']['file'])==p['reference']['sha256']
 for source,value in p['source_modules'].items():assert sha(ROOT.parent/source)==value,'Preserved source changed: '+source
 assert sha(COMMON/'preview/RenderData.gd')==sha(ROOT/'runtime/common/RenderData.gd')
 for path,value in manifest['files'].items():assert sha(directory/path)==value,'Cache file changed: '+path
 parts={q['id']:q for q in rig['parts']};assert len(parts)==len(rig['parts'])
 for q in parts.values():assert q['parent'] is None or q['parent'] in parts
 for socket in rig['sockets'].values():assert socket['part'] in parts
 layers=[];total=0;detail=set(m['extensions']['sampling']['detail_operation_ids']);micro=set(m['extensions']['sampling'].get('micro_operation_ids',[]));bounds=[];expected_groups={}
 for row in render['provenance']['layers']:
  f=directory/row['compiled_file'];assert sha(f)==row['compiled_sha256'];compiled=json.loads(gzip.decompress(f.read_bytes()))
  assert compiled['valid'] and digest(compiled['cells'])==compiled['payload_hash']==row['payload_hash']
  assert len({tuple(x[:3]) for x in compiled['cells']})==len(compiled['cells'])
  assert compiled['pitch'] in [.025,.0125,.00625]
  assert compiled['compiler_source_hash']==sha(COMMON/'core.py')
  assert row['common_provenance']['exporter_sha256']==sha(COMMON/'render_data.py')
  assert row['common_provenance']['mesher_sha256']==sha(ROOT.parent/'tools/mesh.py')
  part=row['part'];sub=isolate(m,{('character',part)},True)
  for component in sub['components']:
   component['operations']=[op for op in component['operations'] if (op['action']!='cut' or op.get('selector',{}).get('part',part)==part) and (op['action']=='cut' or ('micro' if op['id'] in micro else 'detail' if op['id'] in detail else 'bulk')==row['sampling'])]
  assert digest(sub)==row['derived_master_hash']==compiled['master_hash']
  if recompile:
   again=compile_master(sub,{'pitch':compiled['pitch']},max_candidate_cells=800000,max_output_cells=90000)
   assert again['payload_hash']==compiled['payload_hash'],'Non-deterministic common compile'
  r=make_render_data(compiled);assert r['cell_count']==row['cell_count'];total+=r['cell_count'];expected_groups.setdefault(part,[]).extend(r['groups'])
  xyz={tuple(x[:3]) for x in compiled['cells']};remaining=set(xyz);components=[]
  while remaining:
   queue=deque([remaining.pop()]);count=0
   while queue:
    point=queue.popleft();count+=1
    for neighbor in neighbors(point):
     if neighbor in remaining:remaining.remove(neighbor);queue.append(neighbor)
   components.append(count)
  components.sort(reverse=True)
  layers.append({'part':part,'sampling':row['sampling'],'cells':len(xyz),'connected_components':len(components),'largest_component_cells':components[0],'three_axis_extent_cells':[max(x[i] for x in xyz)-min(x[i] for x in xyz)+1 for i in range(3)],'payload_hash':row['payload_hash']})
 for part in render['rigid_parts']:
  assert digest(part['groups'])==digest(expected_groups[part['selector']['part']]),'Render mesh deviates from common cell export'
 assert total==render['cell_count']==manifest['cell_count']
 # Cell counts cannot measure selective-resolution scope: one coarse cell equals 64 micro cells.
 bulk_volume=sum(q['cell_count']*q['pitch_m']**3 for q in render['provenance']['layers'] if q['sampling']=='bulk')
 fine_volume=sum(q['cell_count']*q['pitch_m']**3 for q in render['provenance']['layers'] if q['sampling']!='bulk')
 assert bulk_volume>fine_volume,'Fine sampling dominates physical occupancy volume'
 assert all(q['sampling']=='bulk' for q in layers if q['part'].startswith(('skirt','pelvis','thigh','shin','foot','upper_arm','forearm'))),'Whole-body fine sampling is forbidden'
 assert all(q['part'] in ['head','hair','brow_left','brow_right'] for q in layers if q['sampling']=='micro'),'Micro sampling escaped selected face/fringe parts'
 from PIL import Image
 ref=ROOT/p['reference']['file'];png=ref.with_suffix('.png');a=Image.open(ref).convert('RGB');b=Image.open(png).convert('RGB');assert a.size==b.size and a.tobytes()==b.tobytes()
 return {'cache':str(directory.relative_to(ROOT)),'pass':True,'master_hash':digest(m),'reference_sha256':p['reference']['sha256'],'reference_actual_format':Image.open(ref).format,'comparison_png_sha256':sha(png),'comparison_pixels_unchanged':True,'common_recompile_verified':recompile,'parts':len(parts),'sockets':len(rig['sockets']),'cells':total,'selective_resolution_volume_m3':{'bulk':bulk_volume,'fine':fine_volume},'layers':layers,'visual_acceptance':'Not established by structural tests; inspect actual Godot comparison images.'}
if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('caches',nargs='+',type=Path);ap.add_argument('--recompile',action='store_true');ap.add_argument('--output',required=True,type=Path);a=ap.parse_args();results=[verify(p.resolve(),a.recompile) for p in a.caches];dump(a.output,{'schema':'riverstone.reference_character.verification.v1','pass':True,'results':results});print(json.dumps({'pass':True,'caches':[r['cache'] for r in results]}))
