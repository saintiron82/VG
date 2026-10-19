"""Sequential common compilation/export under the preannounced per-run budgets."""
from __future__ import annotations
import copy
import json
from pathlib import Path
import sys
import time
ROOT=Path(__file__).resolve().parents[4];sys.path.insert(0,str(ROOT))
from voxel_character.common import coordinate_planes,core,render_data
from world_city.concept_city_v3.assemblies.landmarks.author import HERE,ref,write,CANDIDATE_CAP,OUTPUT_CAP


def run():
    manifest=json.loads((HERE/'assemblies.json').read_text())
    requests=[(name,.5,name) for name in manifest['source_masters']]
    requests += [('fine_'+kind,.2,'fine_'+kind) for kind in manifest['fine_cache_kinds']]
    results=[]
    for name,pitch,key in requests:
        source=json.loads((HERE/'masters'/f'{name}.json').read_text());before=copy.deepcopy(source)
        start=time.monotonic()
        try:
            compiled=coordinate_planes.compile_master(source,{'pitch':pitch},max_candidate_cells=CANDIDATE_CAP,max_output_cells=OUTPUT_CAP)
            if source!=before:raise AssertionError('Compiler mutated source')
            row={'id':name,'pitch_m':pitch,'valid':compiled['valid'],'candidate_cells':compiled['candidate_cells'],
                 'output_cells':len(compiled['cells']),'master_hash':compiled['master_hash'],
                 'payload_hash':compiled['payload_hash'],'constraints':compiled['constraints'],
                 'compile_seconds':round(time.monotonic()-start,3)}
            if compiled['valid']:
                render=render_data.make_render_data(compiled)
                target=HERE/'cache'/f'{key}.pitch_{pitch:g}.render.json';write(target,render)
                row.update(render_quads=render['quad_count'],render_bounds=render['bounds'],render=ref(str(target.relative_to(ROOT))))
            else:row['failed_constraints']=[c for c in compiled['constraints'] if not c['pass']]
        except Exception as exc:
            row={'id':name,'pitch_m':pitch,'valid':False,'error':type(exc).__name__+': '+str(exc)}
        results.append(row)
        print(json.dumps({k:v for k,v in row.items() if k not in ('constraints','master_hash','payload_hash')}),flush=True)
    report={'status':'pass' if all(r['valid'] for r in results) else 'fail','requests':results,
            'compiler_sources':[ref('voxel_character/common/'+f) for f in ('coordinate_planes.py','core.py','render_data.py')],
            'author':ref('world_city/concept_city_v3/assemblies/landmarks/author.py'),
            'compile_script':ref('world_city/concept_city_v3/assemblies/landmarks/compile_smoke.py'),
            'manifest':ref(str((HERE/'assemblies.json').relative_to(ROOT))),
            'budget':manifest['compile_budget'],'visual_review':'not_run','runtime_motion':'not_run',
            'terrain_integrated':False,'whole_city_compiled':False}
    write(HERE/'evidence'/'compile_report.json',report)
    return report


if __name__=='__main__':sys.exit(0 if run()['status']=='pass' else 1)
