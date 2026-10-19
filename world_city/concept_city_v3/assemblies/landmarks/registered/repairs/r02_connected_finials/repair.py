"""Source-only taper repair, sampled by the unchanged common compiler.

Sealed r01 masters/caches are read-only inputs. No output cell is added or edited.
"""
import copy
import json
from pathlib import Path
import resource
import sys
import time

HERE=Path(__file__).resolve().parent
REGISTERED=HERE.parents[1]
sys.path.insert(0,str(REGISTERED))
from build_audit import ROOT,ref,write,estimate_candidates
from voxel_character.common import coordinate_planes,core,render_data

NAMES=('cathedral_bell_tower_128m','monastery_bell_tower_84m','registered_civic_civic_tower')
BUDGET={'pitch_m':.5,'candidate_cells_per_request':400000,'output_cells_per_request':200000,'requests':6,'sequential':True}


def continuity(c,base,top):
    """Six-neighbour flood from the main body; inspect all occupied roof cells."""
    occupied={tuple(r[:3]):r for r in c['cells']};remaining=set(occupied);groups=[]
    neighbours=((1,0,0),(-1,0,0),(0,1,0),(0,-1,0),(0,0,1),(0,0,-1))
    while remaining:
        start=next(iter(remaining));remaining.remove(start);stack=[start];group={start}
        while stack:
            x,y,z=stack.pop()
            for dx,dy,dz in neighbours:
                p=x+dx,y+dy,z+dz
                if p in remaining:remaining.remove(p);group.add(p);stack.append(p)
        groups.append(group)
    groups.sort(key=len,reverse=True);body=groups[0];pitch=c['pitch'];origin=c['grid_origin']
    roofs={p for p in occupied if origin[1]+(p[1]+.5)*pitch>=base}
    detached=sorted(roofs-body)
    layers=[]
    for iy in range(round((base-origin[1])/pitch),round((top-origin[1])/pitch)):
        p=[q for q in roofs if q[1]==iy]
        layers.append({'y_min_m':origin[1]+iy*pitch,'occupied_cells':len(p),'body_connected_cells':sum(q in body for q in p)})
    return {'occupied_components':len(groups),'component_sizes':list(map(len,groups)),
            'roof_cells':len(roofs),'roof_cells_disconnected_from_body':len(detached),
            'detached_roof_samples_cell_coordinates':detached[:24],
            'all_roof_cells_body_connected':not detached,'empty_roof_layers':[r['y_min_m'] for r in layers if not r['occupied_cells']],
            'top_layer_body_connected':layers[-1]['body_connected_cells']>0,'layers':layers}


def source_variant(original,path):
    v=copy.deepcopy(original);v['id']+='_r02';v['revision']=2
    for component in v['components']:
        for op in component['operations']:
            if op['id']=='bell_tower_spire':
                radius,base=op['shape']['profile'][0];top=op['shape']['profile'][1][1]
                # Keep the original external silhouette. The internal taper closes
                # five metres below the tip and stays >=1 m thick at the eave.
                op['shape']['profile']=[[radius,base],[0,top],[0,top-5],[radius-1,base]]
                shape_contract={'outer_radius_m':radius,'base_y_m':base,'top_y_m':top,'inner_apex_y_m':top-5,'base_radial_thickness_m':1}
    for component in v['components']:
        for op in component['operations']:
            if op['id']=='spire_finial':op['shape']['min'][1]=top-4
    v['provenance'].update(repair_author=ref(Path(__file__)),repair_parent_source=ref(path),repair_reason='Actual r01 closeups show detached finial and perforated coarse taper; improve continuous source occupancy without editing sampled cells.')
    v['extensions']['coarse_spire_repair']={**shape_contract,'finial_min_y_m':top-4,'finial_max_y_m':top,'finial_square_width_m':.6,'outer_silhouette_unchanged':True,'source_tip_height_unchanged':True,'actual_visual_review':False}
    return v,shape_contract


def main():
    oldpack=REGISTERED/'assembly_r01/resolved_placements.json';pack=json.loads(oldpack.read_text());new=copy.deepcopy(pack);rows=[];replacements=[]
    inputs={n:ref(REGISTERED/'assembly_r01/masters'/f'{n}.json') for n in NAMES}
    for n in NAMES:
        p=ROOT/inputs[n]['path'];old=json.loads(p.read_text());v,contract=source_variant(old,p);newpath=HERE/'masters'/f"{v['id']}.json";write(newpath,v)
        estimate=estimate_candidates(v,.5)
        assert estimate['candidate_cells_exact_aabb_visits']<=BUDGET['candidate_cells_per_request']
        row={'old_id':n,'new_id':v['id'],'old_source':inputs[n],'new_source':ref(newpath),'source_shape_contract':contract,'estimate':estimate['candidate_cells_exact_aabb_visits']}
        for stage,src in [('before',old),('after',v)]:
            start=time.monotonic();c=coordinate_planes.compile_master(src,{'pitch':.5},max_candidate_cells=BUDGET['candidate_cells_per_request'],max_output_cells=BUDGET['output_cells_per_request']);assert c['valid']
            audit=continuity(c,contract['base_y_m'],contract['top_y_m'])
            row[stage]={'candidate_cells':c['candidate_cells'],'output_cells':len(c['cells']),'seconds':round(time.monotonic()-start,3),'process_peak_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'connectivity':audit}
            if stage=='after':
                write(HERE/'evidence'/f'{n}.connectivity.json',row)
                assert audit['all_roof_cells_body_connected'] and audit['top_layer_body_connected'] and not audit['empty_roof_layers'],audit
                r=render_data.make_render_data(c);cache=HERE/'cache'/f"{v['id']}.pitch_0.5.render.json";write(cache,r)
                assert r['bounds']['max'][1]==contract['top_y_m']
                asset={'id':v['id'],'source':ref(newpath),'cache':ref(cache),'master_hash':core.digest(v),'pitch_m':.5,'cell_count':r['cell_count'],'quad_count':r['quad_count']}
                new['assets']=[asset if a['id']==n else a for a in new['assets']]
                for placement in new['placements']:
                    if placement['source_id']==n:
                        original_placement=copy.deepcopy(placement)
                        placement.update(source_id=v['id'],asset_key=v['id'],source=asset['source'],cache=asset['cache'],master_hash=asset['master_hash'],actual_cached_bounds_local_m=r['bounds'],status='resolved_rigid_source_repair_pending_actual_view')
                        replacements.append({'placement_id':placement['id'],'before_asset_id':n,'after_asset_id':v['id'],'before_source':original_placement['source'],'before_cache':original_placement['cache'],'after_source':asset['source'],'after_cache':asset['cache'],'transform_unchanged':True,'floor_and_access_unchanged':True})
                row.update(cache=ref(cache),master_hash=core.digest(v),render_bounds=r['bounds'])
        rows.append(row)
        print(json.dumps({'id':n,'before_detached_roof_cells':row['before']['connectivity']['roof_cells_disconnected_from_body'],'after_detached_roof_cells':row['after']['connectivity']['roof_cells_disconnected_from_body'],'candidate_cells':row['after']['candidate_cells'],'output_cells':row['after']['output_cells'],'peak_rss_kib':row['after']['process_peak_rss_kib']}),flush=True)
    for n,r in inputs.items():assert ref(ROOT/r['path'])==r
    report={'schema':'riverstone.city.spire_connectivity_repair.v1','status':'pass','budget':BUDGET,'base_pack':ref(oldpack),'requests':rows,'whole_city_compile':False,'sampled_cell_mutation':False,'actual_repaired_scene_viewed':False}
    write(HERE/'evidence/compile_connectivity_report.json',report)
    overlay={'schema':'riverstone.city.asset_replacement_overlay.v1','base_pack':ref(oldpack),'replacements':replacements,'remove_placement_ids':[],'add_placement_ids':[],'transform_changes':[],'floor_changes':[],'access_changes':[],'repair_report':ref(HERE/'evidence/compile_connectivity_report.json'),'actual_scene_integration':False,'actual_visual_review':False}
    write(HERE/'asset_replacement_overlay.json',overlay)
    new['status']='registered_landmark_r02_connected_spire_candidate';new['spire_repair_overlay']=ref(HERE/'asset_replacement_overlay.json');new['base_pack']=ref(oldpack);new['completion_claims'].update(actual_scene_loaded=False,actual_visual_review=False)
    write(HERE/'resolved_placements.json',new)
    return report

if __name__=='__main__':main()
