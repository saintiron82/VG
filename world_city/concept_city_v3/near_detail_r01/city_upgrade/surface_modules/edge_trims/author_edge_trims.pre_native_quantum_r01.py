"""Measured source-quad boundary demand -> unchanged safe common surface compiler.

No global module placement expansion. Only one <=1 m occupancy master is held
per compile. Output stays inside this owned directory and below 15 MB.
"""
from __future__ import annotations
import argparse
from collections import Counter,defaultdict
import copy
import hashlib
import itertools
import json
import math
from pathlib import Path
import resource
import sys
import time
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
SURFACES=HERE.parent
sys.path.insert(0,str(SURFACES))
import author_surfaces as common
ROOT=common.ROOT
EPS=1e-6
LIMIT=15_000_000


def read(path): return json.loads(Path(path).read_text())
def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def payload(value): return common.payload(value)
def require(ok,message): common.require(ok,message)
def qint(value):
    n=round(value*4)
    require(math.isfinite(value) and abs(value*4-n)<EPS,'non-quarter coordinate; no rounding fallback')
    return int(n)
def key(trim):
    return 'w%d_h%d_x%d_y%d'%(qint(trim['width_m']),qint(trim['height_m']),qint(trim['offset_m'][0]),qint(trim['offset_m'][1]))

def axis_patterns(low,high):
    """Analytical interval counts, never enumerate a long wall's metre cells."""
    lo=qint(low);hi=qint(high);require(hi>lo,'positive source interval required')
    first=lo//4;last=(hi-1)//4
    if first==last:return {(lo-first*4,hi-lo):1}
    out=Counter({(lo-first*4,(first+1)*4-lo):1})
    out[(0,hi-last*4)]+=1
    if last-first>1:out[(0,4)]+=last-first-1
    return dict(out)

def rectangle(quad):
    if len(quad)!=4 or any(len(p)!=3 or not all(type(v) in (int,float) and math.isfinite(v) for v in p) for p in quad):return None,'nonfinite_or_bad_quad'
    e=[quad[1][i]-quad[0][i] for i in range(3)];f=[quad[2][i]-quad[0][i] for i in range(3)]
    n=[e[1]*f[2]-e[2]*f[1],e[2]*f[0]-e[0]*f[2],e[0]*f[1]-e[1]*f[0]]
    ax=max(range(3),key=lambda i:abs(n[i]))
    if abs(n[ax])<1e-12:return None,'degenerate'
    if ax==1:return None,'horizontal'
    if any(abs(n[i])>EPS*abs(n[ax]) for i in range(3) if i!=ax):return None,'nonaxis'
    sign=1 if n[ax]>0 else -1
    normal=[0,0,0];normal[ax]=sign
    u=[sign,0,0] if ax==2 else [0,0,-sign];v=[0,1,0]
    dot=lambda a,b:sum(x*y for x,y in zip(a,b))
    plane=dot(normal,quad[0])
    if any(abs(dot(normal,p)-plane)>EPS for p in quad):return None,'nonplanar'
    uv=[[dot(u,p),dot(v,p)] for p in quad]
    low=[min(p[i] for p in uv) for i in (0,1)];high=[max(p[i] for p in uv) for i in (0,1)]
    if min(high[i]-low[i] for i in (0,1))<.25-EPS:return None,'smaller_than_quarter'
    if any(abs(x*4-round(x*4))>=EPS for x in low+high):return None,'nonquarter_boundary'
    # Four unique rectangular corners, no AABB approximation of a skew polygon.
    expected={(qint(x),qint(y)) for x in (low[0],high[0]) for y in (low[1],high[1])}
    if {(qint(p[0]),qint(p[1])) for p in uv}!=expected:return None,'not_rectangle'
    for a,b in zip(uv,uv[1:]+uv[:1]):
        if abs(a[0]-b[0])>EPS and abs(a[1]-b[1])>EPS:return None,'crossed_rectangle'
    return {'u':u,'v':v,'normal':normal,'plane_m':plane,'rect_uv_m':low+high},None

def demand_for_rect(rect):
    x0,y0,x1,y1=rect
    out=[]
    for (ox,w),nx in sorted(axis_patterns(x0,x1).items()):
        for (oy,h),ny in sorted(axis_patterns(y0,y1).items()):
            trim={'width_m':w/4,'height_m':h/4,'offset_m':[ox/4,oy/4]}
            out.append((trim,nx*ny))
    return out

def intersection_patch(rect,grid_x,grid_y):
    """Runtime data contract reference; the global 1 m anchor never changes."""
    require(type(grid_x) is int and type(grid_y) is int,'integer full-grid anchor required')
    for value in rect:qint(value)
    x0,y0,x1,y1=rect;require(x1>x0 and y1>y0,'positive rectangular source required')
    a,b=max(x0,grid_x),max(y0,grid_y);c,d=min(x1,grid_x+1),min(y1,grid_y+1)
    if c<=a or d<=b:return None
    trim={'width_m':c-a,'height_m':d-b,'offset_m':[a-grid_x,b-grid_y]}
    return {'grid_xy_m':[grid_x,grid_y],'trim':trim,'trim_key':key(trim),'local_translation_from_full_anchor_m':[trim['offset_m'][0],trim['offset_m'][1],.0375]}

def scan():
    rules=read(HERE/'scan_rules.v1.json')
    require(rules.get('schema')=='riverstone.shared_surface.edge_scan_rules.v1','unsupported scan rules')
    require(rules['boundary_quantum_m']==.25 and rules['nominal_module_size_m']==[1,1],'quarter boundaries and original 1m grid required')
    require(rules['output_budget_bytes']==LIMIT,'this revision is capped at exactly the approved 15 MB envelope')
    require(rules['kinds']==['ashlar','planks'],'only measured wall material families supported in this scan revision')
    require(all((ROOT/rules[k]).resolve().is_relative_to(ROOT.resolve()) for k in ('source_catalog','source_city_index')),'source paths must stay inside repository')
    catalog_path=ROOT/rules['source_catalog'];index_path=ROOT/rules['source_city_index'];catalog=read(catalog_path);index=read(index_path)
    require(catalog['schema']=='riverstone.city.shared_surface_catalog.v1','wrong parent catalog schema')
    require(catalog['source_city_index_sha256']==sha(index_path),'source city identity mismatch')
    require(len(catalog['assets'])==rules['expected_candidate_assets'],'candidate asset scope changed; review input JSON')
    required={};assets={};counts=Counter();examples=[]
    for asset,record in sorted(catalog['assets'].items()):
        source=index['common_assets'][asset];path=ROOT/source['render_path']
        require(sha(path)==record['source_render_sha256']==source['render_sha256'],'source asset changed: '+asset)
        data=read(path);ac=Counter();patterns=set()
        for gi,group in enumerate(data['groups']):
            kind=record['slots'].get(group['material'])
            if kind not in rules['kinds']:continue
            for qi,quad in enumerate(group['quads']):
                counts['candidate_material_quads']+=1
                face,reason=rectangle(quad)
                if reason:
                    counts['excluded/'+reason]+=1;ac['excluded/'+reason]+=1
                    if reason=='nonquarter_boundary' and len(examples)<16:examples.append({'asset':asset,'group_index':gi,'quad_index':qi,'reason':reason})
                    continue
                counts['quarter_grid_vertical_rectangles']+=1;ac['quarter_grid_vertical_rectangles']+=1
                for trim,count in demand_for_rect(face['rect_uv_m']):
                    if trim=={'width_m':1,'height_m':1,'offset_m':[0,0]}:
                        counts['analytical_full_patches']+=count;continue
                    tk=key(trim);rk=kind+'/'+tk;patterns.add(rk);counts['analytical_edge_patches']+=count
                    if rk not in required:required[rk]={'kind':kind,'trim_key':tk,'trim':trim,'source_quad_count':0,'analytical_patch_count':0,'examples':[]}
                    item=required[rk];item['source_quad_count']+=1;item['analytical_patch_count']+=count
                    if len(item['examples'])<2:item['examples'].append({'asset':asset,'group_index':gi,'quad_index':qi,'material':group['material'],**face})
        assets[asset]={'source_render_path':source['render_path'],'source_render_sha256':record['source_render_sha256'],'slots':record['slots'],'counts':dict(ac),'required_kind_trim_keys':sorted(patterns)}
    result={'schema':'riverstone.shared_surface.edge_demand.v1','source_catalog':{'path':rules['source_catalog'],'observed_sha256':sha(catalog_path),'semantic_asset_map_hash':common.digest(catalog['assets'])},'source_city_index':{'path':rules['source_city_index'],'sha256':sha(index_path)},'safe_rules':{'path':str((SURFACES/'inputs/safe_offset_rules.v1.json').relative_to(ROOT)),'sha256':sha(SURFACES/'inputs/safe_offset_rules.v1.json')},'candidate_assets':len(assets),'counts':dict(counts),'required_kind_trim_count':len(required),'required_module_count':len(required)*3,'requirements':[required[k] for k in sorted(required)],'assets':assets,'unsupported_boundary_examples':examples,'global_placement_data_expanded':False,'whole_city_coverage_pass':False}
    # Parent can add edge module references to its catalog while this source
    # asset/slot mapping stays unchanged. Preserve the historical observed hash;
    # current asset semantic identity, original index and source renders stay checked.
    if (HERE/'edge_demand.v1.json').exists():
        previous=read(HERE/'edge_demand.v1.json')
        require(previous['source_catalog']['semantic_asset_map_hash']==result['source_catalog']['semantic_asset_map_hash'],'source asset mapping changed; new reviewed scan revision required')
        result['source_catalog']['observed_sha256']=previous['source_catalog']['observed_sha256']
    common.write_exact(HERE/'edge_demand.v1.json',payload(result))
    return result

def author_exact_crop(spec,kind,seed):
    """Keep original coordinates and sample decisions; clip with common cuts."""
    common.validate_rules(spec)
    require(spec.get('variant_family')=='safe_offset_r01' and not spec['holes'],'safe rectangle-only source rules required')
    require(not spec['geometry']['planks']['nails'] and all(spec['geometry'][k]['face_z_choices_m']==[0] for k in ('ashlar','rubble','paving')),'safe zero-front source geometry required')
    key(spec['trim']) # fail closed on non-quarter dimensions or offsets
    full=copy.deepcopy(spec);full['trim']={'width_m':1,'height_m':1,'offset_m':[0,0]};full['holes']=[]
    master,_=common.author(full,kind,seed)
    _,contract=common.author(spec,kind,seed)
    source_master_hash=common.digest(master)
    trim=spec['trim'];ox,oy=trim['offset_m'];w,h=trim['width_m'],trim['height_m']
    master['id']=master['id']+'_edgecrop_'+common.digest(trim)[:10]
    master['extensions']['shared_surface']['trim']=copy.deepcopy(trim)
    master['extensions']['shared_surface']['rules_hash']=common.digest(spec)
    master['extensions']['shared_surface']['sampling_contract']='full source tile coordinates with common assembly cuts; no translated polygon resampling'
    master['extensions']['shared_surface']['full_source_master_hash']=source_master_hash
    master['extensions']['shared_surface']['master_to_render_translation_m']=[-ox,-oy,0]
    for name,rect in [('left',[0,0,ox,1]),('right',[ox+w,0,1,1]),('bottom',[ox,0,ox+w,oy]),('top',[ox,oy+h,ox+w,1])]:
        a,b,c,d=rect
        if c<=a or d<=b:continue
        shape={'kind':'box','min':[a,b,-.0375],'max':[c,d,.0125]}
        master['assembly_cuts'].append({'id':'edge_crop_'+name,'shape':shape,'selector':{}})
    contract['module_id']=master['id'];contract['render_file']=master['id']+'.render.json'
    return master,contract

def compile_exact_crop(spec,kind,seed):
    master,contract=author_exact_crop(spec,kind,seed)
    ox,oy=spec['trim']['offset_m'];w,h=spec['trim']['width_m'],spec['trim']['height_m'];pitch=spec['pitch_m']
    cell_bounds={'min':[round(ox/pitch),round(oy/pitch),-3],'max':[round((ox+w)/pitch),round((oy+h)/pitch),0]}
    compiled=common.compile_master(master,{'pitch':pitch},cell_bounds=cell_bounds,max_candidate_cells=spec['budgets']['max_candidate_cells_per_module'],max_output_cells=spec['budgets']['max_output_cells_per_module'])
    # A pure coordinate-frame view, not a different occupancy/compiler/mesher.
    # Source integer cell indices and their verified payload hash are unchanged.
    render_frame=dict(compiled,grid_origin=[-ox,-oy,0])
    render=common.make_render_data(render_frame)
    render['provenance']['source_compile_grid_origin']=[0,0,0]
    render['provenance']['evaluation_scope']=compiled['evaluation_scope']
    render['provenance']['global_constraints_evaluated']=False
    render['provenance']['master_to_render_translation_m']=[-ox,-oy,0]
    checks=common.validate_geometry(spec,render_frame,render,contract)
    return master,compiled,render,contract,checks


def build(refresh_owned_cache=False):
    started=time.perf_counter();demand=scan();safe=read(SURFACES/'inputs/safe_offset_rules.v1.json');common.validate_rules(safe)
    require(safe['variant_family']=='safe_offset_r01' and not safe['geometry']['planks']['nails'],'safe source family required')
    require(all(safe['geometry'][k]['face_z_choices_m']==[0] for k in ('ashlar','rubble','paving')),'no extra positive relief allowed')
    existing_paths=[SURFACES/'generated/manifest.json',SURFACES/'generated_safe/manifest.json',ROOT/'voxel_character/common/core.py',ROOT/'voxel_character/common/render_data.py']
    existing={str(p.relative_to(ROOT)):sha(p) for p in existing_paths}
    records=[];lookup={};written=0
    for requirement in demand['requirements']:
        spec=copy.deepcopy(safe);spec['trim']=requirement['trim'];spec['kinds']=[requirement['kind']]
        for seed in safe['seeds']:
            master,compiled,render,contract,checks=compile_exact_crop(spec,requirement['kind'],seed)
            ident=master['id'];render_rel='renders/'+ident+'.render.json';master_rel='masters/'+ident+'.master.json'
            render_bytes=payload(render);master_bytes=payload(master);written+=len(render_bytes)+len(master_bytes)
            require(written+sum(p.stat().st_size for p in HERE.glob('*.json'))<LIMIT-1_000_000,'15 MB edge budget guard reached before writing')
            for rel,data in ((render_rel,render_bytes),(master_rel,master_bytes)):
                target=HERE/rel
                if refresh_owned_cache and target.exists():
                    require(target.parent in (HERE/'renders',HERE/'masters'),'only owned derived cache can be refreshed')
                    target.write_bytes(data)
                else:common.write_exact(target,data)
            require(abs(render['bounds']['min'][2]+.0375)<1e-8 and abs(render['bounds']['max'][2])<1e-8,'unsafe edge module envelope')
            module={'key':requirement['kind']+'/'+str(seed)+'/'+requirement['trim_key'],'trim_key':requirement['trim_key'],'kind':requirement['kind'],'seed':seed,'full_reference_module_id':ident.split('_edgecrop_')[0],'trim':spec['trim'],'id':ident,'render_file':render_rel,'path':str((HERE/render_rel).relative_to(ROOT)),'sha256':hashlib.sha256(render_bytes).hexdigest(),'render_sha256':hashlib.sha256(render_bytes).hexdigest(),'master_file':master_rel,'master_hash':compiled['master_hash'],'payload_hash':compiled['payload_hash'],'quads':render['quad_count'],'cells':len(compiled['cells']),'evaluation_scope':compiled['evaluation_scope'],'valid_scope':compiled['valid_scope'],'global_constraints_evaluated':False,'local_bounds_m':render['bounds'],'master_to_render_translation_m':[-v for v in spec['trim']['offset_m']]+[0],'visual_offset_m':.0375,'maximum_visual_collision_difference_m':.0375,'collision_change':False,'geometry_checks':checks}
            records.append(module);lookup.setdefault(requirement['kind'],{}).setdefault(requirement['trim_key'],[]).append(ident)
            if len(records)%30==0:print(json.dumps({'modules':len(records),'bytes':written,'peak_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss}),flush=True)
            del master,contract,compiled,render,render_bytes,master_bytes
    require(existing=={str(p.relative_to(ROOT)):sha(p) for p in existing_paths},'original common or full modules changed')
    catalog={'schema':'riverstone.shared_surface.edge_catalog.v1','source_demand_sha256':sha(HERE/'edge_demand.v1.json'),'safe_rules':demand['safe_rules'],'module_count':len(records),'modules':records,'by_kind_trim':lookup,'seed_order':safe['seeds'],'full_module_manifest':'../generated_safe/manifest.json','placement_contract':'placement_contract.v1.json','pipeline':['author_surfaces.author full source layout','common assembly_cuts','common.core.compile_master','rigid render-origin translation only','common.render_data.make_render_data'],'original_dependencies':existing,'global_placement_data_expanded':False,'whole_city_coverage_pass':False}
    if refresh_owned_cache and (HERE/'edge_catalog.v1.json').exists():(HERE/'edge_catalog.v1.json').write_bytes(payload(catalog))
    else:common.write_exact(HERE/'edge_catalog.v1.json',payload(catalog))
    total=sum(p.stat().st_size for p in HERE.rglob('*') if p.is_file());rss=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    require(total<LIMIT,'15 MB final package budget exceeded');require(rss<600*1024,'offline memory exceeds 600 MiB')
    report={'status':'PASS_SMALL_SHARED_EDGE_GEOMETRY_ONLY','modules':len(records),'required_kind_trim_patterns':demand['required_kind_trim_count'],'total_edge_package_bytes':total,'budget_bytes':LIMIT,'offline_peak_rss_kib':rss,'elapsed_seconds':round(time.perf_counter()-started,3),'originals_unchanged':True,'whole_city_coverage_pass':False}
    (HERE/'build_report.json').write_bytes(payload(report));print(json.dumps(report),flush=True)
    return catalog,report

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--scan-only',action='store_true');ap.add_argument('--refresh-owned-cache',action='store_true');args=ap.parse_args()
    if args.scan_only:
        value=scan();print(json.dumps({k:value[k] for k in ('candidate_assets','counts','required_kind_trim_count','required_module_count')}))
    else:build(args.refresh_owned_cache)
