"""Read Lily source JSON -> bounded common-generated immutable runtime cache.
Outputs must be a NEW directory. Never edits common or source data.
"""
from pathlib import Path
import argparse,hashlib,json,shutil,sys,time
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT.parent/'common'/'animation'))
from build_render import make_animated_render
from core import digest
from appearance import derive_sources,load_sources

def build(output,pitch=.02,preset=None):
 if output.exists():raise FileExistsError('Use a new generated directory: '+str(output))
 source=derive_sources(json.loads(Path(preset).read_text())) if preset else load_sources()
 master=source['master.json'];rig=source['rig.json'];start=time.perf_counter()
 if pitch!=.02:raise ValueError('Only .02 m is qualified for this detailed source; coarse LOD requires explicit feature review')
 for value in source.values():
  if 'master_hash' in value:assert value['master_hash']==digest(master),'stale source binding'
 render=make_animated_render(master,source['bind.json'],pitch,max_candidates=rig['limits']['maximum_candidate_cells_per_layer'])
 assert render['cell_count']<=rig['limits']['reference_max_cells']
 assert render['quad_count']<=rig['limits']['reference_max_quads']
 output.mkdir(parents=True)
 (output/'derived.master.json').write_text(json.dumps(master,sort_keys=True,separators=(',',':'))+'\n')
 (output/'lily.render.json').write_text(json.dumps(render,sort_keys=True,separators=(',',':'))+'\n')
 for name,value in source.items():
  if name!='master.json':(output/name).write_text(json.dumps(value,sort_keys=True,separators=(',',':'))+'\n')
 (output/'common').mkdir()
 vendors={}
 for name,path in [('RenderData.gd',ROOT.parent/'common'/'preview'/'RenderData.gd'),('TransformTracks.gd',ROOT.parent/'common'/'animation'/'TransformTracks.gd')]:
  shutil.copyfile(path,output/'common'/name)
  vendors[name]={'source':str(path.relative_to(ROOT.parents[1])),'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
 files={str(p.relative_to(output)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(output.rglob('*')) if p.is_file()}
 manifest={'schema':'riverstone.character.cache.v1','source_master_hash':digest(master),'preset_file':str(preset) if preset else 'canonical_lily','preset_sha256':hashlib.sha256(Path(preset).read_bytes()).hexdigest() if preset else None,'source_hashes':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted((ROOT/'data').glob('*.json'))},'pitch_m':pitch,'parts':len(render['rigid_parts']),'cells':render['cell_count'],'quads':render['quad_count'],'mesh_groups':sum(len(p['groups']) for p in render['rigid_parts']),'bounds_m':render['bounds'],'source_modules':vendors,'files':files,'seconds':round(time.perf_counter()-start,3),'visual_review':'not performed by this build','known_absence':'B7 source is unavailable, not recovered'}
 (output/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
 print(json.dumps(manifest,indent=2));return manifest
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('--pitch',type=float,default=.02);p.add_argument('--preset',type=Path);a=p.parse_args();build(a.output,a.pitch,a.preset)
