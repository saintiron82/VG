"""Resolve approved finite landscape sites using existing common caches only."""
from __future__ import annotations
import copy,hashlib,json,math
from pathlib import Path
from . import recipes
from world_city.concept_city_v3.assemblies.property.resolver import sha,read_source_plan
HERE=Path(__file__).parent
CITY=HERE.parents[1]
OLD_CACHE=Path('world_city/runtime_city/generated/r3_bounded_review/compiled_overlay.json')


def file_sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def write(p,value):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(value,indent=2)+'\n')
def shape_sha(source):
    source=copy.deepcopy(source);source.pop('id',None);return sha(source)


def existing_cache_records():
    old=json.loads(OLD_CACHE.read_text());records=[]
    for key,a in old['assets'].items():
        records.append({'cache_asset_key':key,'master_path':a['master_path'],'master_file_sha256':a['master_sha256'],'render_path':a['render_path'],'render_sha256':a['render_sha256'],'pitch_m':a['pitch_m'],'bounds':a['bounds'],'cache_source':str(OLD_CACHE)})
    newer=CITY/'assemblies/property/cache/manifest.json'
    if newer.exists():
        for key,a in json.loads(newer.read_text())['assets'].items():records.append({'cache_asset_key':key,'master_path':a['master_path'],'master_file_sha256':a['master_file_sha256'],'render_path':a['compiled_asset_ref'],'render_sha256':a['render_sha256'],'pitch_m':a['pitch_m'],'bounds':a['bounds'],'cache_source':str(newer)})
    valid=[]
    for r in records:
        if file_sha(r['master_path'])==r['master_file_sha256'] and file_sha(r['render_path'])==r['render_sha256']:
            source=json.loads(Path(r['master_path']).read_text());r['master_source_sha256']=sha(source);r['geometry_identity_ignoring_asset_id_sha256']=shape_sha(source);r['compiled_source_id']=source['id'];valid.append(r)
    return valid


def bind_asset(spec,available):
    source=recipes.make_asset_master(spec);key=recipes.source_key(spec);desired=recipes.resource_for(spec)['pitch'];identity=shape_sha(source)
    choices=[r for r in available if r['geometry_identity_ignoring_asset_id_sha256']==identity and r['pitch_m']<=desired]
    if not choices:return None
    chosen=copy.deepcopy(min(choices,key=lambda x:(x['cache_asset_key']!=key,-x['pitch_m'])));w,d,h=recipes.master_bounds(spec)
    if chosen['bounds']['min'][0]<-w/2-1e-5 or chosen['bounds']['max'][0]>w/2+1e-5 or chosen['bounds']['min'][2]<-d/2-1e-5 or chosen['bounds']['max'][2]>d/2+1e-5:return None
    chosen.update(asset_key=key,authored_source_sha256=sha(source),authored_source_id=source['id'],recommended_pitch_m=desired,sampling_status='exact_recommended_resource' if chosen['pitch_m']==desired else 'verified_finer_existing_resource',alias_policy='Full source equality except top-level asset id; no changed operations, materials, geometry or scale.',compiled_asset_ref=chosen['render_path'],new_compilation_count=0)
    return chosen


def project(p,height_at):
    p=copy.deepcopy(p);anchor=p['ground_anchor'];center=anchor['sample_center_xz_m'];corners=anchor['support_points_xz_m'];points=[center]+corners+[[ (a[0]+b[0])/2,(a[1]+b[1])/2] for a,b in zip(corners,corners[1:]+corners[:1])];levels=[height_at(*q) for q in points];delta=max(levels)-min(levels);datum=levels[0];embed=anchor['footing_embed_m']
    if not all(math.isfinite(y) for y in levels):return None,{'id':p['id'],'reason':'nonfinite_terrain_sample'}
    if delta>anchor['maximum_support_height_delta_m']+1e-6:return None,{'id':p['id'],'reason':'support_delta_exceeds_contract','support_delta_m':delta}
    if datum-embed>min(levels)+1e-6:return None,{'id':p['id'],'reason':'footing_embed_cannot_reach_low_support','datum_y_m':datum,'minimum_support_y_m':min(levels),'footing_embed_m':embed}
    p['position_m'][1]=datum;anchor['datum_y_m']=datum;anchor['resolved']=True;p['terrain_support']={'samples_xz_m':points,'samples_y_m':levels,'minimum_y_m':min(levels),'maximum_y_m':max(levels),'support_delta_m':delta,'datum_policy':'exact center land_height_at; original common root/bed embed retained','xz_unchanged':True,'crown_scaled':False};return p,None


def run():
    plan_path=CITY/'source/plan.json';terrain_path=CITY/'topography/contract.json';proposal_path=CITY/'source/proposed_landscape_sites.json';plan,plan_sha=read_source_plan(plan_path);terrain=json.loads(terrain_path.read_text());proposal=json.loads(proposal_path.read_text())
    if terrain['source_plan_sha256']!=plan_sha or proposal['frozen_source_plan_sha256']!=plan_sha:raise ValueError('Landscape/source/terrain snapshots do not match')
    from world_city.concept_city_v3.topography import author as topography
    if topography.SOURCE_PLAN_SHA256!=plan_sha:raise ValueError('Topography module snapshot is stale')
    available=existing_cache_records();exclusions={e['id']:e for e in proposal['exclusion_catalog']};estate_exclusions=[{'id':'EXCLUSIVE_ESTATE_FLOOR:'+p['id'],'polygon_xz_m':p['polygon_xz_m']} for p in plan['plots'] if p['property_type']=='noble_estate']
    pack={'schema':'riverstone.concept_city.landscape_resolution.v1','status':'cached_source_placement_pack_not_integrated_scene','source_plan_sha256':plan_sha,'terrain_contract_file_sha256':file_sha(terrain_path),'proposed_sites_file_sha256':file_sha(proposal_path),'landscape_recipe_source_sha256':file_sha(HERE/'recipes.py'),'approved_site_ids':[s['id'] for s in proposal['sites']],'approval':'Parent approved bounded landscape resolution after contour blockout review; source proposal itself remains unchanged.','site_records':[],'placements':[],'asset_manifest':{},'unresolved':[],'terrain_rejections':[],'no_new_floor_planes':True,'new_compilation_count':0,'geometry_scaling':False,'scene_integration_performed':False,'actual_scene_visual_review':'pending concept registration and parent integration'}
    for original in proposal['sites']:
        site=copy.deepcopy(original);sid=site['id'];kind=site['landscape_kind']
        if kind not in recipes.KINDS:
            pack['unresolved'].append({'source_ground_id':sid,'reason':'missing_dedicated_facility_recipe','required_recipe':site.get('required_facility_recipe'),'replacement_ids':[]});continue
        if kind in ('monastery_garden','clergy_garden') and site.get('coherent_recipe_frame'):
            frame=site['coherent_recipe_frame']
            if frame.get('verified_union_uncovered_area_m2',1)>.001:raise ValueError('Formal garden frame lacks exact reserved-union coverage proof')
            site['polygons_xz_m']=[frame['polygon_xz_m']]
            site['generation_scope']='Only the approved coherent garden frame; irregular residual boundary slivers are not planted.'
        hard=[exclusions[key] for key in site['exclusion_ids']]+estate_exclusions
        try:r=recipes.build_landscape_recipe(site,plan['boundary_xz_m'],hard)
        except (ValueError,KeyError) as error:pack['unresolved'].append({'source_ground_id':sid,'reason':'source_recipe_failed','detail':str(error),'replacement_ids':[]});continue
        if not r['checks']['valid']:
            pack['unresolved'].append({'source_ground_id':sid,'reason':'source_clearance_or_density_checks_failed','detail':r['checks']['errors'],'replacement_ids':[]});continue
        placed=[];rejections=[];bindings={};missing=[]
        for key,spec in r['master_specs'].items():
            a=bind_asset(spec,available)
            if not a:missing.append(key)
            else:bindings[key]=a
        for p in r['placements']:
            projected,rejected=project(p,topography.land_height_at)
            if rejected:rejections.append(rejected);continue
            if p['asset_key'] in missing:rejections.append({'id':p['id'],'reason':'missing_verified_existing_cache','asset_key':p['asset_key']});continue
            projected['source_site_record_sha256']=sha(original);projected['source_owned_ground_ids']=site.get('source_ground_ids',[]);projected['render_sha256']=bindings[p['asset_key']]['render_sha256'];projected['compiled_asset_ref']=bindings[p['asset_key']]['compiled_asset_ref'];placed.append(projected)
        projected_routes=[];route_fail=[]
        for route in r['access_reservations']:
            samples=[];maximum_grade=0
            for a,b in zip(route['polyline_xz_m'],route['polyline_xz_m'][1:]):
                steps=max(1,math.ceil(math.dist(a,b)))
                part=[[a[0]+(b[0]-a[0])*i/steps,a[1]+(b[1]-a[1])*i/steps] for i in range(steps+1)];levels=[topography.land_height_at(*q) for q in part]
                maximum_grade=max(maximum_grade,max((abs(y2-y1)/math.dist(p1,p2) for p1,p2,y1,y2 in zip(part,part[1:],levels,levels[1:])),default=0));samples.extend([[q[0],y,q[1]] for q,y in zip(part,levels)])
            projected_routes.append({**route,'terrain_samples_m':samples,'maximum_sampled_grade':maximum_grade,'floor_geometry_added':False})
            if maximum_grade>.12001:route_fail.append({'route_id':route['id'],'reason':'garden_walk_requires_explicit_steps_or_reroute','maximum_sampled_grade':maximum_grade})
        if kind in ('monastery_garden','clergy_garden') and (rejections or route_fail):
            pack['unresolved'].append({'source_ground_id':sid,'reason':'coherent_garden_support_or_cache_not_complete','detail':rejections+route_fail,'replacement_ids':[]});pack['terrain_rejections'].extend(rejections);continue
        for key in {p['asset_key'] for p in placed}:pack['asset_manifest'][key]=bindings[key]
        pack['placements'].extend(placed);pack['terrain_rejections'].extend(rejections)
        pack['site_records'].append({'source_ground_id':sid,'landscape_kind':kind,'source_site_record_sha256':sha(original),'source_ground_ids':site.get('source_ground_ids',[]),'owned_polygons_xz_m':original['polygons_xz_m'],'generation_polygons_xz_m':site['polygons_xz_m'],'source_area_m2':site['area_m2'],'source_recipe_metrics':r['metrics'],'placed_count':len(placed),'placement_ids':[p['id'] for p in placed],'excluded_candidate_count':len(rejections),'clearings':r['clearings'],'access_reservations':projected_routes,'land_use_regions':r['land_use_regions'],'source_checks':r['checks'],'replacement_ids':[],'surface_ownership':'existing ground owner; no floor plane added','estate_ownership_guard':'All seven noble plot polygons explicitly excluded'} )
        print(json.dumps({'site':sid,'placements':len(placed),'rejected_support_or_cache':len(rejections),'source_checks':r['checks']['valid']}),flush=True)
    pack['summary']={'resolved_sites':len(pack['site_records']),'unresolved_sites':len(pack['unresolved']),'placements':len(pack['placements']),'trees':sum(p['spec']['kind']=='forest_tree' for p in pack['placements']),'understory':sum(p['spec']['kind']=='understory' for p in pack['placements']),'garden_beds':sum(p['spec']['kind']=='garden_bed' for p in pack['placements']),'unique_existing_cache_assets':len(pack['asset_manifest']),'terrain_rejections':len(pack['terrain_rejections']),'maximum_accepted_support_delta_m':max((p['terrain_support']['support_delta_m'] for p in pack['placements']),default=0),'new_compilations':0,'new_floors':0}
    target=HERE/'resolved_placements.json'
    if target.exists():
        archive=HERE/'generated'/('resolved_placements.'+file_sha(target)[:12]+'.json')
        if not archive.exists():archive.write_bytes(target.read_bytes())
    write(target,pack);write(HERE/'generated/resolution_summary.json',{'summary':pack['summary'],'unresolved':pack['unresolved'],'sites':[{'id':s['source_ground_id'],'placed_count':s['placed_count'],'metrics':s['source_recipe_metrics'],'excluded_candidate_count':s['excluded_candidate_count']} for s in pack['site_records']]});return pack
if __name__=='__main__':print(json.dumps(run()['summary'],indent=2))
