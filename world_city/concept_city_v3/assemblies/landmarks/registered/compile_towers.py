"""Two isolated registered bell-tower exterior caches, common compiler only."""
import json
from pathlib import Path
import resource
import time
from build_audit import HERE,LANDMARKS,ROOT,ref,write,estimate_candidates
from voxel_character.common import coordinate_planes,core,render_data


def main():
    rows=[]
    for name in ('cathedral_bell_tower_128m','monastery_bell_tower_84m'):
        p=HERE/'masters'/f'{name}.json';source=json.loads(p.read_text());before=core.digest(source)
        est=estimate_candidates(source,.5);start=time.monotonic()
        compiled=coordinate_planes.compile_master(source,{'pitch':.5},max_candidate_cells=400000,max_output_cells=200000)
        assert core.digest(source)==before
        assert compiled['candidate_cells']==est['candidate_cells_exact_aabb_visits']
        assert compiled['valid'],compiled['constraints']
        render=render_data.make_render_data(compiled);out=HERE/'cache'/f'{name}.pitch_0.5.render.json';write(out,render)
        row={'id':name,'source':ref(p),'cache':ref(out),'pitch_m':.5,'candidate_cells':compiled['candidate_cells'],
             'output_cells':len(compiled['cells']),'quad_count':render['quad_count'],'valid':compiled['valid'],
             'constraints':compiled['constraints'],'render_bounds':render['bounds'],'master_hash':compiled['master_hash'],
             'compile_seconds':round(time.monotonic()-start,3),'process_peak_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
             'actual_city_placement':False,'actual_visual_review':False}
        rows.append(row);print(json.dumps({k:v for k,v in row.items() if k not in ('constraints','source','cache','render_bounds')}),flush=True)
    report={'schema':'riverstone.city.registered_tower_compile_report.v1','status':'pass','requests':rows,
            'budget':{'candidate_cells_per_compile':400000,'output_cells_per_compile':200000,'sequential_only':True},
            'compiler_sources':[ref(ROOT/'voxel_character/common'/n) for n in ('core.py','coordinate_planes.py','render_data.py')],
            'memory_note':'Linux ru_maxrss is the cumulative process high-water mark, not a separate per-module peak.',
            'whole_city_compile':False,'scene_placement':False,'fine_detail_compile':False}
    write(HERE/'evidence/tower_compile_report.json',report)


if __name__=='__main__':main()
