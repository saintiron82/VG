"""Bounded independent common sample builds; no whole-city compilation."""
import copy,json,time,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[4];sys.path.insert(0,str(ROOT))
from voxel_character.common import coordinate_planes,core,render_data
from world_city.concept_city_v3.assemblies.waterworks.author import HERE,KINDS,ref,write,CANDIDATE_CAP,OUTPUT_CAP


def run():
 rows=[]
 for kind in KINDS:
  path=HERE/'masters'/f'{kind}.json';source=json.loads(path.read_text());before=copy.deepcopy(source);pitch=source['extensions']['smoke_pitch_m'];start=time.monotonic()
  try:
   c=coordinate_planes.compile_master(source,{'pitch':pitch},max_candidate_cells=CANDIDATE_CAP,max_output_cells=OUTPUT_CAP)
   assert source==before,'Compiler mutated source'
   row={'id':kind,'pitch_m':pitch,'valid':c['valid'],'source':ref(str(path.relative_to(ROOT))),'master_hash':c['master_hash'],'payload_hash':c['payload_hash'],'candidate_cells':c['candidate_cells'],'output_cells':len(c['cells']),'constraints':c['constraints'],'seconds':round(time.monotonic()-start,4)}
   if c['valid']:
    render=render_data.make_render_data(c);target=HERE/'cache'/f'{kind}.pitch_{pitch:g}.render.json';write(target,render);row.update(render=ref(str(target.relative_to(ROOT))),quads=render['quad_count'],render_bounds=render['bounds'])
   else:row['failed_constraints']=[x for x in c['constraints'] if not x['pass']]
  except Exception as exc:row={'id':kind,'valid':False,'error':type(exc).__name__+': '+str(exc)}
  rows.append(row);print(json.dumps({k:v for k,v in row.items() if k not in ('constraints','master_hash','payload_hash')}),flush=True)
 report={'status':'pass' if all(r['valid'] for r in rows) else 'fail','requests':rows,'author':ref('world_city/concept_city_v3/assemblies/waterworks/author.py'),'compile_script':ref('world_city/concept_city_v3/assemblies/waterworks/compile_smoke.py'),'compiler_sources':[ref('voxel_character/common/'+f) for f in ('coordinate_planes.py','core.py','render_data.py')],'budget':{'candidates_per_compile':CANDIDATE_CAP,'outputs_per_compile':OUTPUT_CAP,'sequential':True},'whole_city_placed':False,'gui_run':False,'hydraulic_simulation':False}
 write(HERE/'evidence/compile_report.json',report);return report
if __name__=='__main__':sys.exit(0 if run()['status']=='pass' else 1)
