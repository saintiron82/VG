"""Registered market fixtures, reusing unchanged common stall/fountain masters.

The stall clusters are authored interpretations of the painting; the fountain's
image anchor is observed. No new floor plane or whole-asset scaling is introduced.
"""
import hashlib,json,math,copy
from pathlib import Path
from world_city.runtime_city.checks import placement as geo
from world_city.concept_city_v3.registered_topography import author as terrain
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[4]
CITY=ROOT/'world_city/concept_city_v3'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def bounds_poly(bounds,pos,yaw):
    return [[q[0],q[2]] for q in [geo.transform_point_m([x,0,z],pos,yaw) for x,z in [(bounds['min'][0],bounds['min'][2]),(bounds['max'][0],bounds['min'][2]),(bounds['max'][0],bounds['max'][2]),(bounds['min'][0],bounds['max'][2])]]]
def main():
    source=CITY/'registered_source/plan.json';plan=json.loads(source.read_bytes());source_sha=sha(source)
    assets={}
    for key,name in [('cloth','b7bbb02d2f9be2'),('timber','c33d20b8743e94')]:
        master=ROOT/f'world_city/runtime_city/generated/r2/fabric_masters/uf_market_stall_{name}.json'
        render=ROOT/f'world_city/runtime_city/generated/r2/fabric_renders/uf_market_stall_{name}.json'
        d=json.loads(render.read_bytes());assets[key]=dict(master_path=str(master.relative_to(ROOT)),master_sha256=sha(master),render_path=str(render.relative_to(ROOT)),render_sha256=sha(render),bounds=d['bounds'],quad_count=d['quad_count'],pitch_m=d['pitch'])
    master=ROOT/'voxel_character/common/assets/fountain/master.json';render=ROOT/'world_city/runtime_city/generated/r1/infrastructure_renders/fountain.json';d=json.loads(render.read_bytes())
    assets['fountain']=dict(master_path=str(master.relative_to(ROOT)),master_sha256=sha(master),render_path=str(render.relative_to(ROOT)),render_sha256=sha(render),bounds=d['bounds'],quad_count=d['quad_count'],pitch_m=d['pitch'])
    site=next(s for s in plan['spaces'] if s['id']=='SITE_MARKET');group=next(g for g in plan['landmark_components'] if g['id']=='market_stalls')
    fountain_pos=terrain.inverse([935,481],site['finished_floor_y_m'])
    placements=[dict(id='MARKET_FOUNTAIN',asset_key='fountain',position_m=fountain_pos,yaw_rad=0,scale=[1,1,1],palette_id='original_fountain',palette_override={},function='public_drawpoint_and_market_marker',registration=dict(pixel_xy=[935,481],height_m=4,interpretation='visible center anchor; original4.8m common asset kept at native scale'))]
    rejected=[];road_masks=[]
    original=next(r for r in plan['roads'] if r['id']=='MARKET_PROCESSION');replacement=copy.deepcopy(original);cx,_,cz=fountain_pos
    replacement['polyline_xz_m']=[original['polyline_xz_m'][0],[cx-1,cz+26],[cx-8,cz+12],[cx-10,cz],[cx-8,cz-12],original['polyline_xz_m'][-1]]
    replacement['levels_m']=[4]*len(replacement['polyline_xz_m']);replacement['resolved_world_xyz_m']=[[x,4,z] for x,z in replacement['polyline_xz_m']]
    replacement['observed_vs_inferred']='Explicit local functional bypass of observed fountain anchor; unchanged road endpoints and7m width. Original trace preserved in this pack.'
    replacement['maximum_vertex_grade']=0
    for road in [replacement if r['id']==original['id'] else r for r in plan['roads']]:
        for a,b in zip(road['polyline_xz_m'],road['polyline_xz_m'][1:]):road_masks.append((road['id'],geo.road_ribbon(a,b,road['width_m'])))
    water=[w['polygon_xz_m'] for w in terrain.finite_water_polygons()]
    for i,m in enumerate(group['masses']):
        x,_,z=m['position_local_xyz_m'];pos=[x,4,z];yaw=math.radians(m['yaw_degrees']);key='timber' if i%4==0 else 'cloth';p=bounds_poly(assets[key]['bounds'],pos,yaw)
        reason=None
        if math.dist([x,z],[fountain_pos[0],fountain_pos[2]])<10:reason='10m fountain gathering reservation'
        elif not geo.convex_polygon_contains(site['polygon_xz_m'],p,0):reason='outside registered market'
        elif any(geo.positive_area_overlap(p,r,0) for _,r in road_masks):reason='public traffic reservation'
        elif any(geo.positive_area_overlap(p,w,0) for w in water):reason='water reservation'
        if reason:rejected.append(dict(source_proxy_id=m['id'],reason=reason));continue
        cloth=['d4c5a2','b87352','e2d4b5'][i%3]
        placements.append(dict(id='MARKET_'+m['id'],source_proxy_id=m['id'],asset_key=key,position_m=pos,yaw_rad=yaw,scale=[1,1,1],palette_id='canvas_'+str(i%3) if key=='cloth' else 'native_timber',palette_override={'plaster_light':cloth} if key=='cloth' else {},function=['grain','produce','cloth','household_goods'][i%4],footprint_xz_m=p,standing_frontage_width_m=4,source_floor_y_m=4))
    polygons=[bounds_poly(assets[p['asset_key']]['bounds'],p['position_m'],p['yaw_rad']) for p in placements]
    for i,a in enumerate(polygons):
        assert all(not geo.positive_area_overlap(a,b,1e-6) for b in polygons[i+1:]),'fixture overlap'
        assert all(not geo.positive_area_overlap(a,r,0) for _,r in road_masks),'fixture intersects current traffic reservation'
        assert all(not geo.positive_area_overlap(a,w,0) for w in water),'fixture intersects water reservation'
    for p,poly in zip(placements,polygons):
        samples=poly+[[sum(q[k] for q in poly)/len(poly) for k in (0,1)]];heights=[terrain.land_height_at(*q) for q in samples]
        assert max(abs(h-4) for h in heights)<1e-8,(p['id'],heights)
        p['support_samples']=dict(y_m=heights,ground_range_m=max(heights)-min(heights),native_bottom_y_m=p['position_m'][1]+assets[p['asset_key']]['bounds']['min'][1])
    out=dict(schema='riverstone.registered_market_fixtures.v2',status='resolved_native_candidate_requires_bypass_owner_then_actual_view',source_plan_sha256=source_sha,source_proxy_group='market_stalls',replace_landmark_groups=['market_stalls'],access_overlay=dict(replace_roads=[replacement],original_roads=[original],reason='Observed fountain center must be an island, not occupy active procession traffic.'),placements=placements,assets=assets,rejections=rejected,summary=dict(stalls=len(placements)-1,fountains=1,unique_assets=len(assets),new_compiles=0,scaled_instances=0,new_ground_planes=0),limits=['Stall locations derive from the registered functional clusters, not exact individual objects in the painting.','Fountain uses original cached static exterior and colors. Water supply link and runtime flow remain separate staged work.','Walkspace/source support checks do not certify character, cart, NPC or trading gameplay.','Terrain and physics must consume the explicit7m procession bypass before this pack is activated.'])
    assert sha(source)==source_sha
    (HERE/'resolved_placements.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out['summary']))
if __name__=='__main__':main()
