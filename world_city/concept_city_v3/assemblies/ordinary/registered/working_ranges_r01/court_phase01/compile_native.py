"""Bounded sequential common-native court compilation; no scene writes."""
import time,resource
from .author import *
from voxel_character.common import render_data
from world_city.concept_city_v3.assemblies.ordinary.registered.r1.finalize_rows import face_bijection

def run():
 b=load(HERE/'compile_budget.json');assets={};progress=[];start=time.monotonic()
 for key,s in b['variants'].items():
  assert ref(ROOT/s['master']['path'])==s['master'];m=load(ROOT/s['master']['path']);t=time.monotonic();c=coordinate_planes.compile_master(m,{'pitch':PITCH},max_candidate_cells=s['candidate_cap'],max_output_cells=s['output_cap']);assert c['valid'];assert c['candidate_cells']==s['predicted_candidate_visits'];r=render_data.make_render_data(c);proof=face_bijection(c,r);assert core.digest(c['cells'])==c['payload_hash']==r['payload_hash'];cp=HERE/'cache'/f'{key}.compiled.json';rp=HERE/'cache'/f'{key}.render.json';write(cp,c);write(rp,r);assets[key]=dict(key=key,master_path=s['master']['path'],master_sha256=s['master']['sha256'],render_path=str(rp.relative_to(ROOT)),render_sha256=ref(rp)['sha256'],compiled_path=str(cp.relative_to(ROOT)),compiled_sha256=ref(cp)['sha256'],bounds=r['bounds'],cell_count=r['cell_count'],quad_count=r['quad_count'],pitch_m=PITCH,face_bijection=proof,constraints=c['constraints']);progress.append(dict(key=key,candidate_cells=c['candidate_cells'],cell_count=r['cell_count'],quad_count=r['quad_count'],seconds=time.monotonic()-t,**proof));print(json.dumps(progress[-1]),flush=True)
 o=dict(schema='riverstone.court_phase01.native_compile.v1',budget=ref(HERE/'compile_budget.json'),assets=assets,progress=progress,total_seconds=time.monotonic()-start,peak_rss_mib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024,common_compiler=ref(ROOT/'voxel_character/common/core.py'),coordinate_planes=ref(ROOT/'voxel_character/common/coordinate_planes.py'),render_data=ref(ROOT/'voxel_character/common/render_data.py'),cell_edits=0,new_voxel_engine=False);write(HERE/'compile_report.json',o);return o
if __name__=='__main__':run()
