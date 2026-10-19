from pathlib import Path
import argparse,hashlib,json,shutil,sys,time
from author import HERE,LILY,COMMON,dump
from assemble import assemble,sha
sys.path.insert(0,str(COMMON/'animation'))
from build_render import make_animated_render
from core import digest

def build(preset,output,pitch=.0125):
 preset=Path(preset).resolve();output=Path(output).resolve()
 if output.exists():raise FileExistsError('New immutable output directory required')
 if pitch not in [.0125,.02]:raise ValueError('Unqualified pitch')
 source=assemble(json.loads(preset.read_text()));m=source['master.json'];rig=source['rig.json'];t=time.perf_counter()
 render=make_animated_render(m,source['bind.json'],pitch,max_candidates=rig['limits']['maximum_candidate_cells_per_layer'])
 assert render['cell_count']<rig['limits']['reference_max_cells'];assert render['quad_count']<rig['limits']['reference_max_quads']
 output.mkdir(parents=True)
 for n,v in source.items():dump(output/('derived.master.json' if n=='master.json' else n),v)
 (output/'lily.render.json').write_text(json.dumps(render,sort_keys=True,separators=(',',':'))+'\n')
 (output/'common').mkdir()
 for path in [COMMON/'preview/RenderData.gd',COMMON/'animation/TransformTracks.gd']:shutil.copyfile(path,output/'common'/path.name)
 manifest={'schema':'riverstone.character.cache.v1','source_master_hash':digest(m),'source_id':m['id'],'preset_path':str(preset.relative_to(HERE)),'preset_sha256':sha(preset),'pitch_m':pitch,'parts':len(render['rigid_parts']),'cells':render['cell_count'],'quads':render['quad_count'],'bounds_m':render['bounds'],'seconds':round(time.perf_counter()-t,3),'assembly_layers':m['extensions']['assembly']['layers'],'capsule':rig['capsule'],'art_acceptance':'pending actual image inspection','files':{str(p.relative_to(output)):sha(p) for p in sorted(output.rglob('*')) if p.is_file()}}
 dump(output/'manifest.json',manifest);print(json.dumps({k:v for k,v in manifest.items() if k not in ['files','assembly_layers']},indent=2));return manifest
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--preset',type=Path,default=HERE/'data/presets/lily_original.json');p.add_argument('--output',type=Path,required=True);p.add_argument('--pitch',type=float,default=.0125);a=p.parse_args();build(a.preset,a.output,a.pitch)
