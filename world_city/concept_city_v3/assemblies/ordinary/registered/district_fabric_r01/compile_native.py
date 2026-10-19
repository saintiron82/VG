"""Serial unchanged common compiler, hash-bound source and face equivalence."""
import time,resource
from .design import *
from voxel_character.common import core,coordinate_planes,render_data
from world_city.concept_city_v3.assemblies.ordinary.registered.r1.finalize_rows import face_bijection

def run():
 budget=load(HERE/'compile_budget.json');out={};progress=[];start=time.monotonic()
 for key,v in budget['variants'].items():
  assert ref(ROOT/v['master']['path'])==v['master'];m=load(ROOT/v['master']['path']);t=time.monotonic()
  c=coordinate_planes.compile_master(m,{'pitch':v['pitch_m']},max_candidate_cells=v['candidate_cap'],max_output_cells=v['output_cap']);assert c['valid'],c['constraints'];assert c['candidate_cells']==v['predicted_candidate_cells']
  r=render_data.make_render_data(c);proof=face_bijection(c,r);assert core.digest(c['cells'])==c['payload_hash']==r['payload_hash']
  cp=HERE/'cache'/f'{key}.compiled.json';rp=HERE/'cache'/f'{key}.render.json';write(cp,c);write(rp,r)
  out[key]=dict(key=key,master_path=v['master']['path'],master_sha256=v['master']['sha256'],render_path=ref(rp)['path'],render_sha256=ref(rp)['sha256'],compiled_path=ref(cp)['path'],compiled_sha256=ref(cp)['sha256'],bounds=r['bounds'],cell_count=r['cell_count'],quad_count=r['quad_count'],pitch_m=v['pitch_m'],native_metadata=m.get('metadata',{}),face_bijection=proof,constraints=c['constraints'])
  progress.append(dict(key=key,seconds=time.monotonic()-t,candidate_cells=c['candidate_cells'],cells=r['cell_count'],quads=r['quad_count'],**proof));print(json.dumps(progress[-1]),flush=True)
 report=dict(schema='riverstone.district_fabric.native_compile.v1',budget=ref(HERE/'compile_budget.json'),assets=out,progress=progress,total_seconds=time.monotonic()-start,peak_rss_mib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024,common_sources=[ref(Path(z.__file__))for z in (core,coordinate_planes,render_data)],new_engine=False,whole_house_scales=0,cell_edits=0);write(HERE/'compile_report.json',report);return report
if __name__=='__main__':run()
