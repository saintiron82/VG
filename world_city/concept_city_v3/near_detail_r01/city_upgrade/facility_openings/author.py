"""Data-driven bounded opening replacements, using common source geometry.

Writes authored common masters and finite original-cache quad subtraction data.
No source/runtime edits, full-building compilation, or source shape cropping.
"""
from __future__ import annotations
from collections import defaultdict
import copy,gzip,hashlib,itertools,json,math,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[4]
sys.path.insert(0,str(ROOT))
from voxel_character.common import core

def load(p):
    p=Path(p)
    return json.loads(gzip.open(p,'rt').read() if p.suffix=='.gz' else p.read_text())
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def write(p,value):
    p=Path(p);b=(json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False)+'\n').encode()
    if p.suffix=='.gz':
        with p.open('wb') as f:
            with gzip.GzipFile(filename='',mode='wb',fileobj=f,mtime=0) as g:g.write(b)
    else:p.write_bytes(b)
def world_transforms(m):
    ids={i['id']:i for i in m['instances']};result={}
    def get(k):
        if k not in result:
            i=ids[k];t=core.transform(i.get('transform'));result[k]=core.compose(get(i['parent']),t) if i.get('parent') else t
        return result[k]
    for k in ids:get(k)
    return result

def local_bounds(s):return core.shape_bounds(core.prepare_shape(s,.05))
def bounds(shape,t):
    lo,hi=local_bounds(shape);p=[core.apply(t,x) for x in itertools.product(*zip(lo,hi))]
    return [[min(q[j] for q in p) for j in range(3)],[max(q[j] for q in p) for j in range(3)]]
def overlaps(a,b):return all(min(a[1][i],b[1][i])-max(a[0][i],b[0][i])>1e-8 for i in range(3))
def extrusion(poly,lo,hi):return {'kind':'extrusion','polygon':copy.deepcopy(poly),'z_min':lo,'z_max':hi}
def clipped(poly,axis,limit,greater):
    out=[]
    for p,q in zip(poly,poly[1:]+poly[:1]):
        pin=p[axis]>=limit if greater else p[axis]<=limit;qin=q[axis]>=limit if greater else q[axis]<=limit
        if pin:out.append(p)
        if pin!=qin:
            f=(limit-p[axis])/(q[axis]-p[axis]);r=[p[j]+f*(q[j]-p[j]) for j in range(2)];r[axis]=limit;out.append(r)
    return out

def common_op(name,shape,material,t,part):
    return {'id':name,'action':'paint','part':part,'shape':shape,'material':material,'transform':copy.deepcopy(t)}
def op_binding(c,i,o):return {'component':c,'instance':i,'operation':o['id'],'operation_sha256':core.digest(o)}
def source_inventory(m):
    ts=world_transforms(m);ops=[]
    for inst in m['instances']:
        c=next(c for c in m['components'] if c['id']==inst['component'])
        for o in c['operations']:
            t=core.compose(ts[inst['id']],core.transform(o.get('transform')))
            ops.append((c['id'],inst['id'],o,t,bounds(o['shape'],t)))
    return ops

def patch_for(w,outer,rules,pitch,origin):
    lo,hi=local_bounds(outer);pad=rules['patch_tangent_margin_m']
    local={'kind':'box','min':[lo[0]-pad,lo[1]-pad,-rules['patch_inward_depth_m']],'max':[hi[0]+pad,hi[1]+pad,rules['patch_outward_depth_m']]}
    a,b=bounds(local,w['local_to_master'])
    low=[origin[j]+math.floor((a[j]-origin[j])/pitch+1e-8)*pitch for j in range(3)]
    high=[origin[j]+math.ceil((b[j]-origin[j])/pitch-1e-8)*pitch for j in range(3)]
    f=rules['fine_pitch_m'];return {'min':low,'max':high}, {'min':[round((low[j]-origin[j])/f) for j in range(3)],'max':[round((high[j]-origin[j])/f) for j in range(3)]}

def quad_info(q):
    lo=[min(p[j] for p in q) for j in range(3)];hi=[max(p[j] for p in q) for j in range(3)];axis=next(j for j in range(3) if abs(hi[j]-lo[j])<1e-8);t=[j for j in range(3) if j!=axis]
    u=[q[1][j]-q[0][j] for j in range(3)];v=[q[2][j]-q[1][j] for j in range(3)];cross=[u[1]*v[2]-u[2]*v[1],u[2]*v[0]-u[0]*v[2],u[0]*v[1]-u[1]*v[0]]
    return axis,t,lo[axis],1 if cross[axis]>0 else -1,[lo[t[0]],lo[t[1]],hi[t[0]],hi[t[1]]]
def rect_area(r):return max(0,r[2]-r[0])*max(0,r[3]-r[1])
def subtract_rect(a,b):
    x0,y0,x1,y1=max(a[0],b[0]),max(a[1],b[1]),min(a[2],b[2]),min(a[3],b[3])
    if x1-x0<=1e-8 or y1-y0<=1e-8:return [a],None
    removed=[x0,y0,x1,y1];pieces=[[a[0],a[1],x0,a[3]],[x1,a[1],a[2],a[3]],[x0,a[1],x1,y0],[x0,y1,x1,a[3]]]
    return [r for r in pieces if rect_area(r)>1e-12],removed

def rect_quad(r,axis,t,plane,sign):
    q=[]
    for x,y in [(r[0],r[1]),(r[2],r[1]),(r[2],r[3]),(r[0],r[3])]:
        p=[0,0,0];p[axis]=plane;p[t[0]]=x;p[t[1]]=y;q.append(p)
    if quad_info(q)[3]!=sign:q.reverse()
    return q

def cache_contract(render,patches):
    edits=[]
    for gi,g in enumerate(render['groups']):
        for qi,q in enumerate(g['quads']):
            axis,t,plane,sign,original=quad_info(q);rest=[original];removed=[]
            for p in patches:
                b=p['replacement_volume_master_m']
                if not b['min'][axis]-1e-8<=plane<=b['max'][axis]+1e-8:continue
                rect=[b['min'][t[0]],b['min'][t[1]],b['max'][t[0]],b['max'][t[1]]];out=[]
                for fragment in rest:
                    kept,cut=subtract_rect(fragment,rect);out+=kept
                    if cut:removed.append({'patch_id':p['id'],'rect':cut})
                rest=out
            if removed:
                assert abs(rect_area(original)-sum(map(rect_area,rest))-sum(rect_area(x['rect']) for x in removed))<1e-7
                edits.append({'group_index':gi,'quad_index':qi,'material':g['material'],'original_quad_sha256':core.digest(q),'original_quad':q,'normal_axis':axis,'normal_sign':sign,'plane_m':plane,'tangent_axes':t,'retained_quads':[rect_quad(r,axis,t,plane,sign) for r in rest],'removed_rectangles':removed,'original_area_m2':rect_area(original),'removed_area_m2':sum(rect_area(x['rect']) for x in removed)})
    return edits

def author():
    rules=load(HERE/'rules.v1.json');audit=load(ROOT/rules['source_audit']);assets={x['asset_key']:x for x in audit['assets']}
    with gzip.open(ROOT/rules['source_windows'],'rt') as f:windows=[json.loads(x) for x in f]
    catalog=[]
    for target in rules['assets']:
        key=target['asset_key'];a=assets[key];mp=ROOT/a['source_master_path'];rp=ROOT/a['render_path'];assert sha(mp)==a['source_sha256'] and sha(rp)==a['render_sha256']
        source=load(mp);render=load(rp);master=copy.deepcopy(source);inventory=source_inventory(source);look={(c,i,o['id']):o for c,i,o,t,b in inventory};selected=[w for w in windows if w['asset_key']==key]
        new_ops=[];new_cuts=[];patches=[];source_ids=[i['id'] for i in source['instances']]
        for n,w in enumerate(selected):
            assert w['source_profile']=='landmark_polygon_painted_panel' and w['local_outward_sign']==1
            g=look[w['component'],w['instance'],w['glass']['id']];assert core.digest(g)==w['glass']['operation_sha256'];sur=next(f for f in w['associated_features'] if f['id'].endswith('_surround'));outer=look[w['component'],w['instance'],sur['id']]['shape'];poly=g['shape']['polygon'];t=w['local_to_master'];stem=f'opening_{n:03d}';stone=sur['material'];glass=g['material']
            cavity=extrusion(poly,-rules['cavity_depth_m'],.025);cb=bounds(cavity,t);owners=defaultdict(list)
            for c,i,o,ot,b in inventory:
                relevant=(c in rules['wall_component_ids'] and o.get('material') in rules['wall_semantic_slots']) or (c==w['component'] and i==w['instance'] and o['id'] in [g['id']]+[f['id'] for f in w['associated_features']])
                if relevant and o['action']=='paint' and overlaps(cb,b):owners[i].append((c,o))
            assert w['instance'] in owners and any(c in rules['wall_component_ids'] for rows in owners.values() for c,o in rows)
            for i,rows in owners.items():new_cuts.append({'id':stem+'_cavity_'+i,'selector':{'instance':i,'feature':[o['id'] for c,o in rows]},'shape':copy.deepcopy(cavity),'transform':copy.deepcopy(t)})
            new_ops.append(common_op(stem+'_glass',extrusion(poly,-rules['glass_recess_m']-rules['glass_thickness_m'],-rules['glass_recess_m']),glass,t,'glass'))
            ymin=min(p[1] for p in poly);sill=clipped(poly,1,ymin+rules['sill_height_m'],False)
            new_ops.append(common_op(stem+'_sill',extrusion(sill,-rules['cavity_depth_m'],-rules['sill_front_recess_m']),stone,t,'sill'))
            has_mullion=any(f['role']=='mullion' for f in w['associated_features'])
            if has_mullion:
                center=(min(p[0] for p in poly)+max(p[0] for p in poly))/2;bar=clipped(clipped(poly,0,center-rules['mullion_width_m']/2,True),0,center+rules['mullion_width_m']/2,False)
                new_ops.append(common_op(stem+'_mullion',extrusion(bar,-rules['cavity_depth_m'],-rules['mullion_front_recess_m']),stone,t,'mullion'))
            volume,cell_bounds=patch_for(w,outer,rules,render['pitch'],render['grid_origin'])
            patches.append({'id':stem,'source_glass':op_binding(w['component'],w['instance'],g),'source_profile_polygon':copy.deepcopy(poly),'local_to_master':copy.deepcopy(t),'source_surround':op_binding(w['component'],w['instance'],look[w['component'],w['instance'],sur['id']]),'source_owners':[op_binding(c,i,o) for i,rows in owners.items() for c,o in rows],'source_outward_surface_local_z_m':0,'source_glass_recess_m':w['source_glass_recess_m'],'new_glass_recess_m':rules['glass_recess_m'],'cavity_shape_local':cavity,'replacement_volume_master_m':volume,'fine_cell_bounds':cell_bounds,'source_render_observation':w['glass']['cache']['status'],'source_protrusion_m':0,'runtime_ready':False})
        # Existing assembly cuts already apply to all layers. Mirror component
        # entry cuts solely into the new detail layer so open routes stay open.
        protected=[]
        for c,i,o,t,b in inventory:
            if o['action']=='cut' and any(x in o['id'].lower() for x in ['entry','door','portal','loading_bay','passage']):
                protected.append({'id':'opening_protect_'+i+'_'+o['id'],'selector':{'instance':'opening_details'},'shape':copy.deepcopy(o['shape']),'transform':copy.deepcopy(t)})
        master['components'].append({'id':'opening_details','parts':[{'id':name,'pivot':[0,0,0]} for name in ['glass','sill','mullion']],'operations':new_ops});master['instances'].append({'id':'opening_details','component':'opening_details'})
        master['assembly_cuts']=copy.deepcopy(source.get('assembly_cuts',[]))+new_cuts+protected
        master['id']=key+'__opening_detail_r01';master['revision']=1
        master.setdefault('provenance',{})['facility_openings']={'source_master_path':a['source_master_path'],'source_sha256':a['source_sha256'],'rules_sha256':sha(HERE/'rules.v1.json'),'source_shapes_unchanged':True,'generated_with_ai':True,'author_sha256':sha(__file__),'seed':41873,'scope':'Bounded window replacement source; full-building global constraints untested.'}
        core.validate_master(master,rules['fine_pitch_m']);edits=cache_contract(render,patches);out=HERE/'generated'/f'{key}.master.json.gz';write(out,master)
        contract={'schema':'riverstone.facility_openings.replacement.v1','asset_key':key,'source_master_path':a['source_master_path'],'source_sha256':a['source_sha256'],'source_render_path':a['render_path'],'source_render_sha256':a['render_sha256'],'authored_master_path':str(out.relative_to(ROOT)),'authored_master_sha256':sha(out),'source_pitch_m':render['pitch'],'fine_pitch_m':rules['fine_pitch_m'],'grid_origin':source.get('grid_origin',[0,0,0]),'patches':patches,'cache_quad_edits':edits,'original_assembly_cuts':copy.deepcopy(source.get('assembly_cuts',[])),'protected_component_entry_cuts':protected,'entrances':copy.deepcopy(a['entrance_metadata']),'city_placement_ids':a['placement_ids'],'activation':{'runtime_ready':False,'atomic':True,'whole_group_removal':False,'untouched_quads_byte_preserved':True,'collision_reference_changed':False,'source_envelope_growth_m':0,'coarse_grid_transition_seams':'Require boundary stitching or verified no-gap correspondence before runtime activation.','fine_selection':'Compile unmodified authored source with common cell_bounds; never crop primitive polygons; deduplicate overlaps by global integer cell and final label.','scope':'All geometry within union of finite replacement volumes, not an entire wall or material group.'}}
        cp=HERE/'generated'/f'{key}.replacement.json.gz';write(cp,contract)
        catalog.append({'asset_key':key,'source_master_path':a['source_master_path'],'source_sha256':a['source_sha256'],'emitted_master_path':str(out.relative_to(ROOT)),'emitted_master_sha256':sha(out),'replacement_contract_path':str(cp.relative_to(ROOT)),'replacement_contract_sha256':sha(cp),'window_count':len(patches),'new_operations':len(new_ops),'bounded_source_cuts':len(new_cuts),'impacted_original_quads':len(edits),'city_placements':len(a['placement_ids']),'runtime_ready':False})
    write(HERE/'generated/catalog.json',{'schema':'riverstone.facility_openings.catalog.v1','assets':catalog,'full_compile':False,'runtime_activation':False})
    print(json.dumps(catalog,indent=2))
if __name__=='__main__':author()
