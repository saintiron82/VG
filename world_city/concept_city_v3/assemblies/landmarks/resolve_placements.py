"""Resolve static integration placements through the current v3 terrain/water APIs.

This writes an integration recipe only. It does not modify the whole-city scene.
"""
from pathlib import Path
import copy,json,sys
ROOT=Path(__file__).resolve().parents[4];sys.path.insert(0,str(ROOT))
from voxel_character.common import core
from world_city.concept_city_v3.assemblies.landmarks.author import HERE,ref,write,placement
from world_city.concept_city_v3.topography.author import height_at,river_water_y,water_samples_at

EXTERNAL_LINKS={
 'castle':[[[-300,-178],[-300,-170]]],
 'cathedral':[[[250,-201.2],[250,-180],[250,-170]]],
 'monastery':[[[-249,120],[-198,120],[-195,130]]],
 'civic_grain':[[[0,-24.32],[0,-10],[20,-10],[20,0]],[[56,-18],[56,-10],[56,0]]],
}


def resolve():
    manifest=json.loads((HERE/'assemblies.json').read_text())
    entries=[];supports=[];masks=[];links=[];bed_checks=[];quay_bed_checks=[];boat_levels=[]
    for a in manifest['assemblies']:
        name=a['assembly_source'];master=json.loads((HERE/'masters'/f'{name}.json').read_text())
        p=list(a['world_translation_m']);ext=master['extensions'];bounds=ext['local_bounds_m']
        if name!='port_cluster':
            samples=[]
            for x in (bounds['min'][0],(bounds['min'][0]+bounds['max'][0])/2,bounds['max'][0]):
                for z in (bounds['min'][2],(bounds['min'][2]+bounds['max'][2])/2,bounds['max'][2]):
                    actual=height_at(p[0]+x,p[2]+z)
                    samples.append({'xz_m':[p[0]+x,p[2]+z],'host_y_m':actual,'expected_y_m':p[1],
                                    'matches':abs(actual-p[1])<1e-7})
            supports.append({'assembly':a['id'],'level_bench_samples':samples,'pass':all(s['matches'] for s in samples)})
        else:
            samples=[]
            for x in (-40,0,40):
                for z in (-20,15,30,59.2):
                    h=height_at(p[0]+x,p[2]+z)
                    samples.append({'xz_m':[p[0]+x,p[2]+z],'terrain_y_m':h,
                                    'foundation_bottom_y_m':p[1]-1.2,'slab_top_y_m':p[1],
                                    'contact_or_embed':p[1]-1.2<=h+1e-7 and h<=p[1]+1e-7})
            supports.append({'assembly':a['id'],'apron_foundation_samples':samples,
                             'pass':all(s['contact_or_embed'] for s in samples)})
            for x in (-3,3):
                for z in (68,84):
                    wx,wz=p[0]+x,p[2]+z
                    water=next(w for w in water_samples_at(wx,wz) if w['id']=='MAIN_RIVER')
                    tip=p[1]-6.5
                    bed_checks.append({'assembly':a['id'],'pile_xz_m':[wx,wz],'tip_y_m':tip,
                                       'bed_y_m':water['bed_y_m'],'embedded_m':water['bed_y_m']-tip,
                                       'pass':tip<=water['bed_y_m']})
            for x in (-40,0,40):
                wx,wz=p[0]+x,p[2]+60.5
                water=next(w for w in water_samples_at(wx,wz) if w['id']=='MAIN_RIVER')
                tip=p[1]-6.5
                quay_bed_checks.append({'assembly':a['id'],'footing_xz_m':[wx,wz],'base_y_m':tip,
                                        'bed_y_m':water['bed_y_m'],'embedded_m':water['bed_y_m']-tip,
                                        'pass':tip<=water['bed_y_m']})
        rp=HERE/a['render_cache']
        entries.append({'id':a['id'],'kind':'main_static','assembly':a['id'],
                        'render':ref(str(rp.relative_to(ROOT))),'transform':placement(p),
                        'replaces_source_building_ids':a['replaces_source_building_ids']})
        lo=[p[0]+bounds['min'][0],p[2]+bounds['min'][2]]
        hi=[p[0]+bounds['max'][0],p[2]+bounds['max'][2]]
        if name=='port_cluster':hi[1]=p[2]+60.8
        masks.append({'id':a['id'],'ground_surface_mask_xz_m':[[lo[0],lo[1]],[hi[0],lo[1]],[hi[0],hi[1]],[lo[0],hi[1]]],
                      'mode':'Suppress underlying terrain TOP render faces under authored pavement/quay. Keep water surfaces and structural bed ownership.',
                      'implemented_in_whole_city':False})
        for d in a['fine_details']:
            local=d['position_local_m'];world=[p[0]+local[0],p[1]+local[1],p[2]+local[2]]
            if d['datum']=='river_water':
                world[1]=river_water_y(world[0])+local[1]
                boat_levels.append({'id':a['id']+':'+d['id'],'world_x_m':world[0],'waterline_y_m':world[1],
                                    'quay_y_m':p[1],'nominal_draft_m':.65,'nominal_underkeel_clearance_m':2.35,'waterline_source':'topography.author.river_water_y(world_x)',
                                    'required_crane_hook_floor_y_m':world[1]-.4,
                                    'crane_motion_status':'travel and rope synchronization not implemented'})
            cache=HERE/'cache'/f"fine_{d['cache_key']}.pitch_0.2.render.json"
            entries.append({'id':a['id']+':'+d['id'],'kind':'fine_detail','assembly':a['id'],
                            'render':ref(str(cache.relative_to(ROOT))),
                            'transform':placement(world,d['yaw_degrees']),
                            'datum':d['datum'],'static_only':True})
        for i,path in enumerate(EXTERNAL_LINKS.get(name,[])):
            links.append({'id':a['id']+':external_'+str(i),'path_xz_m':path,
                          'status':'Required source-plan connector; not automatically edited into city roads.',
                          'terrain_samples_xyz_m':[[x,height_at(x,z),z] for x,z in path]})
    return {'schema':'riverstone.city.landmark_placements.v1','status':'static_integration_recipe_not_applied',
            'source_manifest':ref(str((HERE/'assemblies.json').relative_to(ROOT))),
            'terrain_author':ref('world_city/concept_city_v3/topography/author.py'),
            'placements':entries,'surface_ownership_masks':masks,'external_route_links':links,
            'support_checks':supports,'dock_pile_bed_checks':bed_checks,'quay_footing_bed_checks':quay_bed_checks,'boat_waterline_checks':boat_levels,
            'support_pass':all(x['pass'] for x in supports+bed_checks+quay_bed_checks),
            'limitations':['Point/grid support checks are geometric source checks, not structural or controller certification.',
                           'Root integration still must replace proxy IDs, apply surface ownership masks and resolve source-plan connectors.',
                           'No dynamic water, buoyancy, gate animation or cargo lifting is implemented.']}


if __name__=='__main__':
    result=resolve();write(HERE/'resolved_placements.json',result)
    print(json.dumps({'placements':len(result['placements']),'support_pass':result['support_pass'],
                      'boat_waterlines':result['boat_waterline_checks']}))
    sys.exit(0 if result['support_pass'] else 1)
