"""Independent, bounded single-pass emitted-quad witnesses for B2.

Usage: python verify_emitted_geometry.py --self-test
       python verify_emitted_geometry.py --prepare-only
       python verify_emitted_geometry.py [--render PATH] [--manifest PATH]
Only emitted_geometry_qa.json is written, and only after an actual render scan.
No source compiler, predicates, GUI, mesh generation or source edits are used.
"""
from bisect import bisect_left
from collections import Counter, defaultdict
import argparse
import gzip
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import resource
import sys
import time
sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[6]
F = HERE.parents[1]
KEY = 'registered_cathedral_nave_aisles_transept'
STREAM_PATH = F/'composed_runtime/stream_render.py'
STREAM_SHA = '420b60d904701283aa18001592a13ef9dcb6e9a03b182824f1a01b0048c18262'
EPS = 1e-7
MAX_OUTPUT = 1024*1024
MAX_RSS_KIB = 192*1024


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda: f.read(1024*1024), b''): h.update(block)
    return h.hexdigest()


def load(path):
    p = Path(path)
    with (gzip.open(p, 'rt') if p.suffix == '.gz' else p.open()) as f: return json.load(f)


def ref(path):
    p = Path(path).resolve()
    try: name = str(p.relative_to(ROOT))
    except ValueError: name = str(p)
    return {'path': name, 'sha256': sha(p), 'bytes': p.stat().st_size}


def close(a, b): return abs(a-b) < EPS


def merged(intervals):
    result = []
    for lo, hi in sorted(intervals):
        if hi-lo < EPS: continue
        if result and lo <= result[-1][1]+EPS: result[-1][1] = max(result[-1][1], hi)
        else: result.append([lo, hi])
    return result


def same_intervals(actual, expected):
    a, b = merged(actual), merged(expected)
    return len(a) == len(b) and all(close(x, y) for r, s in zip(a, b) for x, y in zip(r, s))


def snapped_edge(x, pitch, origin=0):
    # Nearest cell boundary for these non-half-cell-tied continuous surfaces.
    scaled = (x-origin)/pitch
    if close(scaled-math.floor(scaled), .5):
        raise ValueError('Ambiguous half-cell source boundary requires explicit sampling policy')
    return origin+math.floor(scaled+.5)*pitch


def cell_center(x, pitch, origin=0): return origin+(math.floor((x-origin)/pitch)+.5)*pitch


def transform(t, p):
    return [sum(t['basis'][i][j]*p[j] for j in range(3))+t['translation'][i] for i in range(3)]


def plane_depth(t, x): return t['basis'][0][2]*(x-t['translation'][0])


def expected_depth(t, local_depth, pitch, origin):
    return plane_depth(t, snapped_edge(transform(t,[0,0,local_depth])[0],pitch,origin[0]))


def interval_at(t, lo, hi, pitch, origin):
    ends = sorted(transform(t,[x,0,0])[2] for x in (lo,hi))
    return [snapped_edge(x,pitch,origin[2]) for x in ends]


def load_context():
    if sha(STREAM_PATH) != STREAM_SHA: raise ValueError('Frozen stream_render hash mismatch')
    spec = importlib.util.spec_from_file_location('b2_frozen_stream', STREAM_PATH)
    stream = importlib.util.module_from_spec(spec); spec.loader.exec_module(stream)
    catalog = load(HERE/'catalog.json')
    contract = load(HERE/'replacement.b2.json.gz')
    qa = load(HERE/'structural_qa.json')
    for name in ('replacement.b2.json.gz','structural_qa.json','windows.b2.authored.master.json.gz','revision_rules.json'):
        if sha(HERE/name) != catalog['files'][name]['sha256']: raise ValueError('Source handoff hash mismatch: '+name)
    if qa['status'] != 'pass_source_candidate_not_compiled': raise ValueError('Source QA has no passing status')
    plan = load(HERE/'runtime.plan.json')
    if plan['canonical_master_sha256'] != contract['authored_master_sha256']: raise ValueError('Plan canonical mismatch')
    if plan['replacement_contract_sha256'] != sha(HERE/'replacement.b2.json.gz'): raise ValueError('Plan contract mismatch')
    if plan['source_revision'] != contract['source_revision']: raise ValueError('Plan source revision mismatch')
    window = load(HERE/'windows.b2.authored.master.json.gz')
    ops = {o['id']:o for c in window['components'] for o in c['operations']}
    rules = load(HERE/'revision_rules.json')
    frozen_rules = load(ROOT/rules['inputs']['frozen_rules']['path'])
    if sha(ROOT/rules['inputs']['frozen_rules']['path']) != rules['inputs']['frozen_rules']['sha256']: raise ValueError('Frozen window grammar mismatch')
    return stream, contract, qa, plan, rules, frozen_rules, ops


def build_queries(contract, source_qa, rules, grammar, ops):
    pitch, origin = contract['fine_pitch_m'], contract['grid_origin']
    patches = {p['id']:p for p in contract['patches']}
    records = {p['patch_id']:p for p in contract['relocated_windows']}
    rays, sections, windows = [], [], []
    def add(item, kind, t, x, y, materials, depth, suffix):
        world = transform(t,[x,y,0])
        world[1] = cell_center(world[1],pitch,origin[1]); world[2] = cell_center(world[2],pitch,origin[2])
        q = {'id':item['patch_id']+'__'+kind+'__'+suffix,'patch_id':item['patch_id'],'kind':kind,
             'side':item['side'],'transform':t,'sample_master_yz_m':world[1:],
             'requested_window_xy_m':[x,y], 'expected_materials':materials,
             'expected_front_depth_m':expected_depth(t,depth,pitch,origin), 'hits':[]}
        rays.append(q); return q
    for item in rules['relocations']:
        pid=item['patch_id']; t=patches[pid]['local_to_master']; old_t=records[pid]['old_transform']
        pane=ops[item['window']+'_pane']; frame=ops[item['window']+'_surround']; poly=pane['shape']['polygon']
        glass=ops[pid+'_glass']; mullion=ops[pid+'_mullion']; sill=ops[pid+'_sill']
        xmin,xmax=min(p[0] for p in poly),max(p[0] for p in poly)
        center=(xmin+xmax)/2; halfbar=grammar['mullion_width_m']/2
        outermin,outermax=min(p[0] for p in frame['shape']['polygon']),max(p[0] for p in frame['shape']['polygon'])
        ybase=min(p[1] for p in poly)
        for yi,y in enumerate((6.,8.,10.)):
            for xi,x in enumerate((-.6,.6)):
                ray=add(item,'pane',t,x,y,[glass['material']],glass['shape']['z_max'],f'{yi}_{xi}')
                ray['expected_back_depth_m']=expected_depth(t,glass['shape']['z_min'],pitch,origin)
                ray['expected_backing_depth_m']=expected_depth(t,-grammar['cavity_depth_m'],pitch,origin)
                ray['expected_backing_material']=pane['material']
            add(item,'mullion',t,center,y,[mullion['material']],mullion['shape']['z_max'],str(yi))
            for xi,x in enumerate(((outermin+xmin)/2,(outermax+xmax)/2)):
                add(item,'frame',t,x,y,[frame['material']],frame['shape']['z_max'],f'{yi}_{xi}')
            Y=cell_center(y,pitch,origin[1])
            sections.append({'id':pid+'__section__'+str(yi),'patch_id':pid,'side':item['side'],'transform':t,'y_m':Y,
                             'frame_depth_m':expected_depth(t,0,pitch,origin),
                             'glass_depth_m':expected_depth(t,glass['shape']['z_max'],pitch,origin),
                             'mullion_depth_m':expected_depth(t,mullion['shape']['z_max'],pitch,origin),
                             'glass_material':glass['material'],'frame_material':frame['material'],
                             'frame_envelope_z_m':interval_at(t,outermin,outermax,pitch,origin),
                             'expected_glass_intervals_z_m':sorted([interval_at(t,xmin,center-halfbar,pitch,origin),interval_at(t,center+halfbar,xmax,pitch,origin)]),
                             'expected_frame_intervals_z_m':sorted([interval_at(t,outermin,xmin,pitch,origin),interval_at(t,xmax,outermax,pitch,origin)]),
                             'expected_mullion_intervals_z_m':[interval_at(t,center-halfbar,center+halfbar,pitch,origin)],
                             'actual':{'glass':[],'frame':[],'mullion':[]}})
        for yi,y in enumerate((ybase+.025,ybase+.075)):
            add(item,'sill',t,.5,y,[sill['material']],sill['shape']['z_max'],str(yi))
        ray=add(item,'sill_above',t,.5,ybase+grammar['sill_height_m']+.05,[glass['material']],glass['shape']['z_max'],'0')
        ray['expected_back_depth_m']=expected_depth(t,glass['shape']['z_min'],pitch,origin)
        ray['expected_backing_depth_m']=expected_depth(t,-grammar['cavity_depth_m'],pitch,origin)
        ray['expected_backing_material']=pane['material']
        for xi,x in enumerate((-.6,.6)):
            add(item,'old_restoration',old_t,x,8.,['stone','stone_light'],0,str(xi))
        windows.append({'patch_id':pid,'window':item['window'],'axis_index':item['axis_index'],'side':item['side'],
                        'frame_envelope_z_m':interval_at(t,outermin,outermax,pitch,origin)})
    # The 0.10 m spaces are masonry strips, not empty air holes.
    for side in (-1,1):
        pair=sorted([w for w in windows if w['side']==side and w['axis_index'] in rules['pair_indices']],key=lambda w:w['frame_envelope_z_m'][0])
        t=patches[pair[0]['patch_id']]['local_to_master']; gap=(pair[0]['frame_envelope_z_m'][1]+pair[1]['frame_envelope_z_m'][0])/2
        local_x=(gap-t['translation'][2])/t['basis'][2][0]
        for yi,y in enumerate((6.,8.,10.)):
            item={'patch_id':pair[0]['patch_id'],'side':side}
            add(item,'end_pair_gap',t,local_x,y,['stone'],0,str(yi))
    return rays,sections,windows


class Collector:
    def __init__(self,rays,sections):
        self.rays=rays;self.sections=sections;self.count=0;self.kept=0
        self.by_y=defaultdict(list);self.sections_by_y=defaultdict(list)
        for r in rays:self.by_y[r['sample_master_yz_m'][0]].append(r)
        for s in sections:self.sections_by_y[s['y_m']].append(s)
        self.ys=sorted(set(self.by_y)|set(self.sections_by_y))
    def consume(self,gi,qi,material,q):
        self.count+=1
        if len(q)!=4 or any(len(v)!=3 for v in q):raise ValueError('Malformed emitted quad')
        if not all(abs(v[0]-q[0][0])<EPS for v in q):return
        X=q[0][0]
        if not 13.3<abs(X)<18.7:return
        y0,y1=min(v[1] for v in q),max(v[1] for v in q)
        j0,j1=bisect_left(self.ys,y0),bisect_left(self.ys,y1)
        if j0==j1:return
        z0,z1=min(v[2] for v in q),max(v[2] for v in q)
        if y1-y0<EPS or z1-z0<EPS:raise ValueError('Degenerate witness quad')
        u=[q[1][j]-q[0][j] for j in range(3)];v=[q[2][j]-q[1][j] for j in range(3)]
        cross=u[1]*v[2]-u[2]*v[1]
        sign=1 if cross>0 else -1
        touched=False
        for Y in self.ys[j0:j1]:
            for r in self.by_y[Y]:
                Z=r['sample_master_yz_m'][1]
                if not z0<=Z<z1:continue
                depth=plane_depth(r['transform'],X)
                if not -.8<depth<4:continue
                hit={'depth_m':round(depth,12),'normal_outward':sign*r['side'],'material':material,'group_index':gi,'quad_index':qi,'world_x_m':X}
                r['hits'].append(hit);touched=True
                if len(r['hits'])>64:raise ValueError('Witness ray exceeds 64 hits: '+r['id'])
            for s in self.sections_by_y[Y]:
                depth=plane_depth(s['transform'],X)
                lo,hi=s['frame_envelope_z_m'];a0,b0=max(z0,lo),min(z1,hi)
                if b0-a0<EPS or sign*s['side']!=1:continue
                for kind in ('glass','frame','mullion'):
                    expected_material=s['glass_material'] if kind=='glass' else s['frame_material']
                    if close(depth,s[kind+'_depth_m']) and material==expected_material:
                        s['actual'][kind].append([a0,b0]);touched=True
        self.kept+=bool(touched)


def validate_ray(r):
    hits=sorted(r['hits'],key=lambda x:(-x['depth_m'],x['normal_outward'],str(x['material'])))
    problems=[];kind=r['kind'];expected=r['expected_front_depth_m']
    at=lambda d:[h for h in hits if close(h['depth_m'],d)]
    duplicates=Counter((h['depth_m'],h['normal_outward'],str(h['material'])) for h in hits)
    if any(n>1 for n in duplicates.values()):problems.append('duplicate_coincident_ray_hits')
    face=at(expected)
    if len(face)!=1 or face[0]['material'] not in r['expected_materials'] or face[0]['normal_outward']!=1:
        problems.append('missing_or_wrong_front_surface')
    if kind in ('pane','sill_above'):
        for name,normal,material in [('back',-1,r['expected_materials'][0]),('backing',1,r['expected_backing_material'])]:
            f=at(r['expected_'+name+'_depth_m'])
            if len(f)!=1 or f[0]['normal_outward']!=normal or f[0]['material']!=material:problems.append('missing_or_wrong_'+name+'_surface')
        expected_depths=[expected,r['expected_back_depth_m'],r['expected_backing_depth_m']]
        prefix=[h for h in hits if h['depth_m']>=expected_depths[-1]-EPS]
        if len(prefix)!=3 or not all(close(h['depth_m'],d) for h,d in zip(prefix,expected_depths)):
            problems.append('front_to_glass_to_backing_hit_order')
        thickness=expected-r['expected_back_depth_m'];gap=r['expected_back_depth_m']-r['expected_backing_depth_m']
        if not close(thickness,.05) or not close(gap,.05):problems.append('glass_thickness_or_rear_air_gap_not_005')
    elif kind=='old_restoration':
        if any(h['material']=='glass' and -.35-EPS<=h['depth_m']<=.1+EPS for h in hits):problems.append('stale_glass_or_old_cavity_surface')
        # Original fixed buttress/transept may precede this restored wall.
    elif any(h['depth_m']>expected+EPS for h in hits):
        problems.append('unexpected_front_occluder')
    result={k:v for k,v in r.items() if k not in ('transform','hits')}
    result.update({'pass':not problems,'problems':problems,'ordered_hits':hits})
    if kind in ('pane','sill_above'):
        result['emitted_glass_front_recess_from_source_frame_m']=round(expected_depth(r['transform'],0,.05,[0,0,0])-hits[0]['depth_m'],12) if hits else None
    return result


def validate_sections(sections,windows,rules):
    results=[]
    for s in sections:
        actual={k:merged(v) for k,v in s['actual'].items()}
        problems=[k+'_section_width_or_location' for k in actual if not same_intervals(actual[k],s['expected_'+k+'_intervals_z_m'])]
        result={k:v for k,v in s.items() if k not in ('transform','actual')}
        result.update({'actual':actual,'pass':not problems,'problems':problems,
                       'emitted_glass_half_widths_m':[round(b-a,10) for a,b in actual['glass']],
                       'emitted_mullion_width_m':round(sum(b-a for a,b in actual['mullion']),10)})
        results.append(result)
    gaps=[]
    for side in (-1,1):
        pair=sorted([w for w in windows if w['side']==side and w['axis_index'] in rules['pair_indices']],key=lambda w:w['frame_envelope_z_m'][0])
        for Y in sorted({s['y_m'] for s in sections}):
            first=next(s for s in results if s['patch_id']==pair[0]['patch_id'] and s['y_m']==Y)
            second=next(s for s in results if s['patch_id']==pair[1]['patch_id'] and s['y_m']==Y)
            left=first['actual']['frame'];right=second['actual']['frame']
            end=max((b for a,b in left),default=None);start=min((a for a,b in right),default=None)
            gap=None if start is None or end is None else start-end
            gaps.append({'side':side,'y_m':Y,'first_emitted_frame_end_z_m':end,'second_emitted_frame_start_z_m':start,
                         'emitted_gap_m':None if gap is None else round(gap,12),
                         'expected_gap_m':rules['expected_pair_frame_gap_m'],'pass':gap is not None and close(gap,rules['expected_pair_frame_gap_m']),
                         'meaning':'Clear separation of stone_light frame bands; the intervening strip is solid stone wall.'})
    return results,gaps


def self_test():
    t={'basis':[[0,0,1],[0,1,0],[-1,0,0]],'translation':[14.62,0,0]}
    base={'id':'test','patch_id':'test','kind':'pane','side':1,'transform':t,'sample_master_yz_m':[8.025,.625],
          'expected_materials':['glass'],'expected_front_depth_m':-.22,'expected_back_depth_m':-.27,
          'expected_backing_depth_m':-.32,'expected_backing_material':'glass','hits':[]}
    c=Collector([base],[])
    def quad(x,normal):
        q=[[x,8,0],[x,8.05,0],[x,8.05,1],[x,8,1]]
        return q if normal==1 else q[::-1]
    for i,(x,normal) in enumerate(((14.4,1),(14.35,-1),(14.3,1))):c.consume(0,i,'glass',quad(x,normal))
    assert validate_ray(base)['pass']
    saved=list(base['hits']);base['hits']=saved[:-1];assert not validate_ray(base)['pass']
    base['hits']=saved+[saved[0]];assert not validate_ray(base)['pass']
    base['hits']=saved+[{'depth_m':.03,'normal_outward':1,'material':'stone','group_index':1,'quad_index':0,'world_x_m':14.65}]
    assert 'front_to_glass_to_backing_hit_order' in validate_ray(base)['problems']
    assert same_intervals([[0,.3],[.3,.7]],[[0,.7]])
    assert not same_intervals([[0,.25],[.3,.7]],[[0,.7]])
    west={'basis':[[0,0,-1],[0,1,0],[1,0,0]],'translation':[-14.62,0,0]}
    assert close(expected_depth(west,-.2,.05,[0,0,0]),-.22)
    assert close(expected_depth(t,-.2,.05,[0,0,0]),-.22)
    return {'status':'pass','tests':['correct_ray','missing_backing_rejected','duplicate_rejected','front_occlusion_rejected','subdivision_equivalence','section_gap_rejected','mirrored_depths'],'actual_render_tested':False}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--render',type=Path,default=HERE/'runtime'/(KEY+'.b2.candidate.render.json.gz'))
    parser.add_argument('--manifest',type=Path)
    parser.add_argument('--prepare-only',action='store_true')
    parser.add_argument('--self-test',action='store_true')
    args=parser.parse_args()
    if args.self_test:print(json.dumps(self_test(),indent=2));return 0
    start=time.monotonic();stream,contract,source_qa,plan,rules,grammar,ops=load_context()
    rays,sections,windows=build_queries(contract,source_qa,rules,grammar,ops)
    if args.prepare_only:
        print(json.dumps({'status':'cli_prepared_actual_render_not_tested','rays':dict(Counter(r['kind'] for r in rays)),
                          'window_count':len(windows),'sections':len(sections),'end_pair_gap_measurements':6,
                          'render_expected':str(args.render),'render_exists':args.render.exists(),'compile_calls':0},indent=2));return 0
    if not args.render.is_file():raise FileNotFoundError('Final emitted render is not available; no geometry QA has run: '+str(args.render))
    render_ref=ref(args.render);manifest_ref=None
    if args.manifest:
        manifest=load(args.manifest);manifest_ref=ref(args.manifest)
        if manifest.get('render_sha256') != render_ref['sha256']:raise ValueError('Manifest render SHA mismatch')
        if manifest.get('source_revision') != contract['source_revision']:raise ValueError('Manifest source revision mismatch')
    before_stat=(args.render.stat().st_size,args.render.stat().st_mtime_ns)
    collector=Collector(rays,sections)
    ordered_digest=hashlib.sha256()
    # Exactly one geometry-iterator invocation. Material IDs must remain the
    # source semantic slots; unsupported aliases fail the witness comparisons.
    for gi,qi,material,q in stream.iter_indexed_quads(args.render):
        ordered_digest.update(json.dumps([material,q],separators=(',',':')).encode())
        collector.consume(gi,qi,material,q)
        if collector.count%10000==0 and resource.getrusage(resource.RUSAGE_SELF).ru_maxrss>=MAX_RSS_KIB:raise MemoryError('RSS budget exceeded')
    if (args.render.stat().st_size,args.render.stat().st_mtime_ns)!=before_stat:raise ValueError('Render changed during verification')
    ray_results=[validate_ray(r) for r in rays]
    section_results,gaps=validate_sections(sections,windows,rules)
    failures=[{'kind':'ray','id':r['id'],'problems':r['problems']} for r in ray_results if not r['pass']]
    failures += [{'kind':'section','id':r['id'],'problems':r['problems']} for r in section_results if not r['pass']]
    failures += [{'kind':'end_pair_gap','side':r['side'],'y_m':r['y_m'],'actual_gap_m':r['emitted_gap_m']} for r in gaps if not r['pass']]
    summary_counts={kind:{'total':sum(r['kind']==kind for r in ray_results),'passed':sum(r['kind']==kind and r['pass'] for r in ray_results)} for kind in sorted({r['kind'] for r in ray_results})}
    summary_counts.update({'sections':{'total':len(section_results),'passed':sum(r['pass'] for r in section_results)},'end_pair_gap_measurements':{'total':len(gaps),'passed':sum(r['pass'] for r in gaps)},'failures':len(failures)})
    result={'schema':'riverstone.cathedral.b2.emitted_geometry_qa.v1','all_pass':not failures,'render_sha256':render_ref['sha256'],
            'source_structural_qa_path':str((HERE/'structural_qa.json').relative_to(ROOT)),'source_structural_qa_sha256':sha(HERE/'structural_qa.json'),
            'quad_count':collector.count,'ordered_material_quad_digest':ordered_digest.hexdigest(),'summary_counts':summary_counts,'status':'pass_emitted_geometry_witnesses' if not failures else 'fail_emitted_geometry_witnesses',
            'actual_render_tested':True,'visual_review_pass':False,'compile_calls':0,'geometry_edits':0,'runtime_edits':0,
            'render':render_ref,'manifest':manifest_ref,'verifier':ref(Path(__file__)),'stream_reader':ref(STREAM_PATH),
            'source_qa_reference':ref(HERE/'structural_qa.json'),'source_contract_reference':ref(HERE/'replacement.b2.json.gz'),
            'runtime_plan_reference':ref(HERE/'runtime.plan.json'),'source_equality_scope':'The unchanged 17 upper/great windows and source revision equality are hash-referenced to source QA; this emitted test does not independently prove them.',
            'streamed_quad_count':collector.count,'quads_touching_witnesses':collector.kept,'geometry_iterator_passes':1,
            'window_count':len(windows),'ray_counts':dict(Counter(r['kind'] for r in rays)),
            'ray_results':ray_results,'section_results':section_results,'end_pair_gaps':gaps,'failures':failures,
            'backing_semantics':'The frozen author cuts to -0.30 m. Original pane paint remains from -0.50 to -0.30 m over masonry; expected cavity backing is glass material. The new 0.05 m pane is separated from that backing by 0.05 m air. A stone-colored backing is not asserted.',
            'old_restoration_semantics':'Restored emitted stone/stone_light at the original wall face, with stale cavity glass absent. Some rays may first hit unchanged transept/support surfaces. Mesh material cannot identify a hidden masonry owner; ownership restoration is source-QA evidence.',
            'sampling':'Master-local orthographic X rays at nearest fine-cell-center Y/Z, both clear pane halves at Y approximately 6, 8, 10 m. Faces are ordered from exterior to interior, including winding signs and material. Frame/glass/mullion section widths and end gaps are measured from actual quads.',
            'limits':'Finite emitted-quad witnesses, not whole-mesh watertightness, GUI/pixel appearance, camera occlusion, historical correctness, or runtime activation proof. A passing result is not visual PASS.',
            'max_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'elapsed_seconds':round(time.monotonic()-start,3)}
    payload=(json.dumps(result,sort_keys=True,separators=(',',':'))+'\n').encode()
    if len(payload)+Path(__file__).stat().st_size>MAX_OUTPUT:raise ValueError('Output budget exceeded; refusing truncated QA')
    (HERE/'emitted_geometry_qa.json').write_bytes(payload)
    print(json.dumps({k:result[k] for k in ('status','actual_render_tested','streamed_quad_count','quads_touching_witnesses','window_count','ray_counts','max_rss_kib','elapsed_seconds')},indent=2))
    print(json.dumps({'failure_count':len(failures),'report_path':str(HERE/'emitted_geometry_qa.json')},indent=2))
    return 1 if failures else 0


if __name__=='__main__':
    try:sys.exit(main())
    except (ValueError,FileNotFoundError,MemoryError,AssertionError) as exc:
        print(json.dumps({'status':'verification_not_completed','error':str(exc),'visual_review_pass':False}),file=sys.stderr);sys.exit(2)
