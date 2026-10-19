"""Small source-preserving common ROI tests and analytic/orthographic views."""
from __future__ import annotations
from collections import Counter
import copy,json,math,resource,sys,time
from pathlib import Path
from PIL import Image,ImageDraw
import author as a
import seam_adapter
sys.path.insert(0,str(a.ROOT/'voxel_character/tools'))
import mesh
HERE=a.HERE;OUT=HERE/'tests'

def cells_map(c):return {tuple(r[:3]):r for r in c['cells']}
def surface(c):
    p=c['pitch'];o=c['grid_origin'];groups={}
    for q,m in mesh.greedy_faces([(*r[:3],r[5]) for r in c['cells']]):groups.setdefault(m,[]).append([[o[j]+v[j]*p for j in range(3)] for v in q])
    return {'schema':'riverstone.facility_openings.roi_preview.v1','evaluation_scope':c['evaluation_scope'],'global_valid':None,'source_id':c['source_id'],'master_hash':c['master_hash'],'payload_hash':c['payload_hash'],'pitch':p,'materials':c['materials'],'groups':[{'material':m,'quads':q} for m,q in sorted(groups.items())]}
def cut_contains(cut,world,pitch):return a.core.contains(a.core.prepare_shape(cut['shape'],pitch),a.core.inverse(a.core.transform(cut.get('transform')),world),epsilon=pitch*a.core.EPS)
def first_hit(c,frame,target,yaw,cells):
    p=c['pitch'];origin=c['grid_origin'];slope=math.tan(math.radians(yaw));z=.35
    while z>=-.45:
        local=[target[0]+slope*(z+.225),target[1],z];world=a.core.apply(frame,local);ijk=tuple(math.floor((world[j]-origin[j])/p) for j in range(3));row=cells.get(ijk)
        if row:return {'local_z':round(z,5),'material':row[5],'feature':row[6],'part':row[4]}
        z-=.005
    return None

def ray_checks(c,p):
    poly=p['source_profile_polygon'];xmin=min(x for x,y in poly);xmax=max(x for x,y in poly);ymin=min(y for x,y in poly);ymax=max(y for x,y in poly)
    results=[];lookup=cells_map(c)
    for yaw in [-35,0,35]:
        hits=[]
        for fx in [.2,.3,.4,.6,.7,.8]:
            for fy in [.25,.4,.55]:
                target=[xmin+(xmax-xmin)*fx,ymin+(ymax-ymin)*fy]
                if not a.core.inside_polygon(*target,poly):continue
                hit=first_hit(c,p['local_to_master'],target,yaw,lookup)
                if hit:hits.append(hit)
        glass=[h for h in hits if h['part']=='glass' and h['feature'].endswith('_glass')]
        assert glass,('No new glazing visible',p['id'],yaw,hits)
        results.append({'yaw_degrees':yaw,'rays':len(hits),'new_glass_first_hit_count':len(glass),'new_glass_front_local_z_range_m':[min(h['local_z'] for h in glass),max(h['local_z'] for h in glass)],'other_first_hit_parts':dict(Counter(h['part'] for h in hits if h not in glass))})
    return results

def draw_panel(canvas,box,render,patch,yaw,title):
    x0,y0,x1,y1=box;draw=ImageDraw.Draw(canvas);draw.rectangle(box,fill='#20272d');frame=patch['local_to_master'];ang=math.radians(yaw);el=math.radians(8)
    right=[math.cos(ang),0,-math.sin(ang)];up=[-math.sin(ang)*math.sin(el),math.cos(el),-math.cos(ang)*math.sin(el)];view=[math.sin(ang)*math.cos(el),math.sin(el),math.cos(ang)*math.cos(el)];polys=[];allxy=[]
    for g in render['groups']:
        base=tuple(int(render['materials'][g['material']].lstrip('#')[i:i+2],16) for i in (0,2,4))
        for q in g['quads']:
            q=[a.core.inverse(frame,v) for v in q];u=[q[1][j]-q[0][j] for j in range(3)];v=[q[2][j]-q[1][j] for j in range(3)];normal=[u[1]*v[2]-u[2]*v[1],u[2]*v[0]-u[0]*v[2],u[0]*v[1]-u[1]*v[0]];length=math.sqrt(sum(n*n for n in normal));normal=[n/length for n in normal]
            if sum(normal[j]*view[j] for j in range(3))<1e-6:continue
            xy=[(sum(v[j]*right[j] for j in range(3)),sum(v[j]*up[j] for j in range(3))) for v in q];depth=sum(sum(v[j]*view[j] for j in range(3)) for v in q)/4;light=.48+.46*max(0,sum(normal[j]*[.3,.4,.866][j] for j in range(3)));color=tuple(min(255,round(c*light)) for c in base);polys.append((depth,xy,color));allxy+=xy
    lo=[min(v[j] for v in allxy) for j in range(2)];hi=[max(v[j] for v in allxy) for j in range(2)];scale=min((x1-x0-30)/(hi[0]-lo[0]),(y1-y0-54)/(hi[1]-lo[1]));cx=(lo[0]+hi[0])/2;cy=(lo[1]+hi[1])/2
    for depth,xy,color in sorted(polys):draw.polygon([(round((x0+x1)/2+(x-cx)*scale),round((y0+y1)/2+14-(y-cy)*scale)) for x,y in xy],fill=color)
    draw.text((x0+10,y0+10),title,fill='#f0e8d9')

def structural(source,master,contract):
    assert master['components'][:-1]==source['components'];assert master['instances'][:-1]==source['instances'];assert master['extensions']==source['extensions'];assert master['constraints']==source['constraints'];assert master['grid_origin']==source['grid_origin']
    n=len(source.get('assembly_cuts',[]));assert master['assembly_cuts'][:n]==source.get('assembly_cuts',[])
    a.core.validate_master(master,.05)
    seen=set();totalarea=0
    for e in contract['cache_quad_edits']:
        assert (e['group_index'],e['quad_index']) not in seen;seen.add((e['group_index'],e['quad_index']));assert a.core.digest(e['original_quad'])==e['original_quad_sha256']
        areas=[a.rect_area(a.quad_info(q)[4]) for q in e['retained_quads']];assert abs(sum(areas)+e['removed_area_m2']-e['original_area_m2'])<1e-7
        assert all(a.quad_info(q)[3]==e['normal_sign'] for q in e['retained_quads']);totalarea+=e['removed_area_m2']
    source_ids={i['id'] for i in source['instances']};detail=master['components'][-1]
    for op in detail['operations']:
        assert op['shape']['z_max']<=0 and op['shape']['z_min']>=-.3-1e-8
    for cut in master['assembly_cuts'][n:]:
        assert cut['selector'];assert cut['selector']['instance'] in source_ids or cut['selector']['instance']=='opening_details'
        if cut['selector']['instance']!='opening_details':assert cut['selector'].get('feature') and cut['shape']['z_min']==-.3 and cut['shape']['z_max']==.025
    return {'original_components_operations_unchanged':True,'original_instances_unchanged':True,'original_cuts_order_preserved':True,'original_constraints_and_entrances_preserved':True,'source_primitive_cropping':False,'authored_outward_protrusion_m':0,'finite_quad_edits':len(seen),'finite_removed_area_m2':round(totalarea,5),'whole_group_removal':False}

def main():
    started=time.monotonic();rules=a.load(HERE/'rules.v1.json');cat=a.load(HERE/'generated/catalog.json');results=[];structures=[]
    for row,target in zip(cat['assets'],rules['assets']):
        source=a.load(a.ROOT/row['source_master_path']);master=a.load(a.ROOT/row['emitted_master_path']);contract=a.load(a.ROOT/row['replacement_contract_path']);assert a.sha(a.ROOT/row['source_master_path'])==row['source_sha256'];assert a.sha(a.ROOT/row['emitted_master_path'])==row['emitted_master_sha256'];structures.append({'asset_key':row['asset_key'],**structural(source,master,contract)})
        for number,window in enumerate(target['probe_windows']):
            patch=next(p for p in contract['patches'] if p['source_glass']['operation']==window);kwargs={'max_candidate_cells':rules['max_roi_candidates'],'max_output_cells':rules['max_roi_cells'],'cell_bounds':patch['fine_cell_bounds']}
            t0=time.monotonic();baseline=a.core.compile_master(source,{'pitch':.05},**kwargs);t1=time.monotonic();fine=a.core.compile_master(master,{'pitch':.05},**kwargs);t2=time.monotonic()
            assert baseline['global_constraints_evaluated'] is False and fine['global_constraints_evaluated'] is False
            bm=cells_map(baseline);fm=cells_map(fine);new=[r for r in fine['cells'] if r[3]=='opening_details'];assert new;assert any(r[4]=='glass' for r in new);assert any(r[4]=='mullion' for r in new)
            removed=[];changed=[];added=[];bad=[]
            roi=[patch['replacement_volume_master_m']['min'],patch['replacement_volume_master_m']['max']]
            relevant=[c for c in master['assembly_cuts'][len(source.get('assembly_cuts',[])):] if a.overlaps(a.bounds(c['shape'],a.core.transform(c.get('transform'))),roi)]
            prepared=[(a.core.prepare_shape(c['shape'],.05),a.core.transform(c.get('transform'))) for c in relevant]
            for ijk in set(bm)|set(fm):
                old,b=bm.get(ijk),fm.get(ijk);center=[(v+.5)*.05+fine['grid_origin'][j] for j,v in enumerate(ijk)]
                if old!=b:
                    changed.append(ijk)
                    if old is not None and b is None:removed.append(ijk)
                    if old is None and b is not None:added.append(ijk)
                    if not any(a.core.contains(shape,a.core.inverse(tr,center),epsilon=.05*a.core.EPS) for shape,tr in prepared) and (b is None or b[3]!='opening_details'):bad.append(ijk)
            assert not bad,('Unbounded source changes',bad[:5]);assert removed,('No physical cavity',window)
            protected=list(source.get('assembly_cuts',[]))+contract['protected_component_entry_cuts'];blocked=[]
            for r in new:
                center=[(v+.5)*.05+fine['grid_origin'][j] for j,v in enumerate(r[:3])]
                if any(cut_contains(c,center,.05) for c in protected):blocked.append(r[:3])
            assert not blocked,('New detail blocks entry',window,blocked[:5])
            preview0=surface(baseline);preview1=surface(fine);name=row['asset_key']+'__'+window
            seam=seam_adapter.build(a.load(a.ROOT/contract['source_render_path']),fine,preview1,patch,protected)
            a.write(OUT/(name+'.seam.json.gz'),seam)
            a.write(OUT/(name+'.fine_preview.json.gz'),preview1)
            rays=ray_checks(fine,patch) if number==0 else []
            if number==0:
                image=Image.new('RGB',(1050,820),'#13191e')
                for col,yaw in enumerate([-35,0,35]):
                    draw_panel(image,(col*350,0,(col+1)*350-4,405),preview0,patch,yaw,f'SOURCE .05 / yaw {yaw}')
                    draw_panel(image,(col*350,410,(col+1)*350-4,815),preview1,patch,yaw,f'RECESSED .05 / yaw {yaw}')
                image.save(OUT/(row['asset_key']+'.multiview.png'))
            result={'asset_key':row['asset_key'],'window':window,'cell_bounds':patch['fine_cell_bounds'],'source_cell_count':len(bm),'detail_cell_count':len(fm),'source_compile_seconds':round(t1-t0,5),'detail_compile_seconds':round(t2-t1,5),'seam_transition_faces':seam['transition_unit_faces'],'seam_transition_quads':seam['transition_quads'],'unpaired_interface_edges':seam['unpaired_interface_edges'],'protected_entry_interface_violations':seam['protected_entry_interface_violations'],'source_candidate_cells':baseline['candidate_cells'],'detail_candidate_cells':fine['candidate_cells'],'source_payload_hash':baseline['payload_hash'],'detail_payload_hash':fine['payload_hash'],'new_detail_cells':len(new),'new_parts':dict(Counter(r[4] for r in new)),'removed_occupied_cells_for_real_cavity':len(removed),'changed_final_labels':len(changed),'added_previously_empty_cells':len(added),'unbounded_source_changes':0,'new_entry_blockers':0,'multiview_rays':rays,'global_constraints_evaluated':False,'bounded_source_constraints':baseline['constraints'],'bounded_authored_constraints':fine['constraints'],'bounded_valid_is_not_building_valid':True}
            results.append(result);print(json.dumps({k:result[k] for k in ['asset_key','window','source_candidate_cells','detail_candidate_cells','new_parts','removed_occupied_cells_for_real_cavity','new_entry_blockers']}),flush=True)
            del baseline,fine,bm,fm,new,preview0,preview1
    result={'schema':'riverstone.facility_openings.verification.v1','passed':True,'source_assets':2,'authored_windows':sum(x['window_count'] for x in cat['assets']),'common_roi_probes':len(results),'common_compile_calls':len(results)*2,'full_building_compiles':0,'structures':structures,'roi_probes':results,'runtime_edits':0,'collider_edits':0,'runtime_ready':False,'seam_contract_status':'Exact coarse/fine grid-interface XOR seam passes all tested ROI closure/entry checks; runtime atomic activation remains untested.','elapsed_seconds':round(time.monotonic()-started,3),'max_rss_kb':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss}
    a.write(OUT/'verification.json',result);size=sum(p.stat().st_size for p in HERE.rglob('*') if p.is_file());assert size<10*1024*1024;assert result['max_rss_kb']<500*1024
    print(json.dumps({'passed':True,'directory_bytes':size,'elapsed_seconds':result['elapsed_seconds'],'max_rss_kb':result['max_rss_kb']}))
if __name__=='__main__':main()
