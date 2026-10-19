"""Bind the existing 0.2 m native stone bridge cache; never invoke a compiler.

Collision evidence is derived directly from the frozen, orthogonal cached mesh.
Horizontal boundary faces partition the mesh into exact constant-XZ columns;
paired Y crossings recover solids without authoring or replacing any geometry.
"""
import json
import math
from pathlib import Path
import sys
sys.dont_write_bytecode = True
import author as a
from voxel_character.common.core import digest

MASTER=a.ROOT/'world_city/concept_city_v3/assemblies/waterworks/masters/stone_road_bridge_bay.json'
RENDER=a.ROOT/'world_city/concept_city_v3/assemblies/waterworks/cache/stone_road_bridge_bay.pitch_0.2.render.json'
KEY='v3_waterworks_stone_road_bridge_bay'
FRAME={'position_m':[390.00205240938203,3.0,-3.150481687107995],'yaw_rad':0.3494290568265689}
INSTANCE={'id':'R9_LANDWARD_GATE:EAST:CANAL_BRIDGE','asset_key':KEY,**FRAME,'palette_id':'native_waterworks','palette_override':{},'scale':[1,1,1],'source_pack':'landward_gates_bridge_r9'}
EXPECTED_ENDS=[[382.48550573024147,3,-0.41159030183889644],[397.5185990885226,3,-5.889373072377094]]
EPS=1e-8


def horizontal_faces(render):
    result=[]
    for group in render['groups']:
        for q in group['quads']:
            # Every frozen boundary face must remain orthogonal in native space.
            constant=[k for k in range(3) if max(v[k]for v in q)-min(v[k]for v in q)<EPS]
            assert len(constant)==1, 'Non-orthogonal cached face requires another exact checker'
            if constant==[1]:
                result.append({'y':q[0][1],'x':[min(v[0]for v in q),max(v[0]for v in q)],'z':[min(v[2]for v in q),max(v[2]for v in q)]})
    return result


def recover_columns(render):
    faces=horizontal_faces(render)
    xs=sorted({x for f in faces for x in f['x']}); zs=sorted({z for f in faces for z in f['z']}); cols=[]
    for x0,x1 in zip(xs,xs[1:]):
        for z0,z1 in zip(zs,zs[1:]):
            x,z=(x0+x1)/2,(z0+z1)/2
            ys=sorted({f['y']for f in faces if f['x'][0]<x<f['x'][1] and f['z'][0]<z<f['z'][1]})
            assert len(ys)%2==0, ('Unclosed native mesh column',x,z,ys)
            for y0,y1 in zip(ys[::2],ys[1::2]):
                cols.append({'min':[x0,y0,z0],'max':[x1,y1,z1]})
    volume=sum(math.prod(c['max'][k]-c['min'][k] for k in range(3))for c in cols)
    assert abs(volume-render['cell_count']*render['pitch']**3)<1e-6, ('Native mesh-volume identity',volume)
    return cols,volume


def prism_hits(cols,lo,hi):
    hits=[]
    for j,c in enumerate(cols):
        dims=[min(hi[k],c['max'][k])-max(lo[k],c['min'][k])for k in range(3)]
        if min(dims)>EPS:
            hits.append({'column_index':j,'intersection_volume_m3':math.prod(dims)})
    return hits


def plane(triangle):
    p,q,r=triangle;dx1,dz1=q[0]-p[0],q[2]-p[2];dx2,dz2=r[0]-p[0],r[2]-p[2]
    dy1,dy2=q[1]-p[1],r[1]-p[1];det=dx1*dz2-dx2*dz1
    ax=(dy1*dz2-dy2*dz1)/det;az=(dx1*dy2-dx2*dy1)/det
    return lambda x,z:p[1]+ax*(x-p[0])+az*(z-p[2])


def main():
    gate_pack_sha=a.sha(a.HERE/'pack.json')
    master=json.loads(MASTER.read_text());render=json.loads(RENDER.read_text())
    assert master['id']==KEY and render['source_id']==KEY
    assert digest(master)==render['master_hash']
    assert master['materials']==render['materials'] and render['pitch']==0.2
    assert KEY not in a.S['common_assets']
    cols,volume=recover_columns(render)
    top=[f for f in horizontal_faces(render) if abs(f['y'])<EPS]
    assert top==[{'y':0.0,'x':[-8.0,8.0],'z':[-3.6,3.6]}],top
    deck_clear=prism_hits(cols,[-8,0,-3.5],[8,3.5,3.5]);assert not deck_clear
    wet_band=prism_hits(cols,[-3,-1.8,-4],[3,-1.7,4]);assert not wet_band
    deck_support=prism_hits(cols,[-8,-0.2,-3.5],[8,0,3.5]);support_volume=sum(r['intersection_volume_m3']for r in deck_support)
    assert abs(support_volume-16*7*.2)<1e-7
    # Distinguishes actual collision-support geometry from a decorative or missing deck.
    negative_underdeck=prism_hits(cols,[-1,-0.2,-1],[1,-0.01,1]);assert negative_underdeck
    endpoints=[a.world([x,0,0],FRAME)for x in [-8,8]]
    assert all(abs(p[k]-q[k])<1e-10 for p,q in zip(endpoints,EXPECTED_ENDS) for k in range(3))
    footprint=[a.world([x,0,z],FRAME)for x,z in a.rect(-8,-4,8,4)]
    # Bind the two exact source water faces to the frozen full scene, not just the extracted subset.
    assert a.sha(a.BASE)==a.BASE_SHA
    scene=json.loads(a.BASE.read_bytes());water_vertices=scene['surfaces']['water']
    extracted={r['triangle_index']:r['triangle'] for r in json.loads((a.HERE.parent/'local_source_faces.json').read_text()) if r['material']=='water'}
    water=[];wet_area=0;minimum_soffit_gap=math.inf;water_heights=[];pier_overlap=0.0
    for index in range(len(water_vertices)//3):
        triangle=water_vertices[index*3:index*3+3];lt=[a.local(v,FRAME)for v in triangle];xz=[[v[0],v[2]]for v in lt]
        clipped=a.clip(xz,a.rect(-8,-4,8,4));clipped_area=a.area(clipped)
        if clipped_area<EPS:
            continue
        assert index in [96,97] and extracted[index]==triangle
        y_at=plane(lt);ys=[y_at(x,z) for x,z in clipped];water_heights.extend(y+3 for y in ys);wet_area+=clipped_area
        assert min(x for x,z in clipped)>=-3-EPS and max(x for x,z in clipped)<=3+EPS
        local_gaps=[]
        for c in cols:
            overlap=a.clip(clipped,a.rect(c['min'][0],c['min'][2],c['max'][0],c['max'][2]))
            if a.area(overlap)<EPS:
                continue
            heights=[y_at(x,z)for x,z in overlap]
            assert c['min'][1]>max(heights)+EPS, ('Bridge solid intersects source water',index,c,heights)
            local_gaps.append(c['min'][1]-max(heights))
        minimum_soffit_gap=min(minimum_soffit_gap,min(local_gaps))
        for pier in [a.rect(-8,-4,-7,4),a.rect(7,-4,8,4)]:
            pier_overlap+=a.overlap(clipped,pier)
        water.append({'material':'water','triangle_index':index,'triangle_world_m':triangle,'triangle_bridge_local_m':lt,'clipped_xz_bridge_local_m':clipped,'clipped_area_m2':clipped_area,'water_world_y_range_m':[min(ys)+3,max(ys)+3],'minimum_exact_soffit_clearance_m':min(local_gaps)})
    del scene
    assert {v['triangle_index']for v in water}=={96,97}
    assert abs(wet_area-48)<1e-6 and pier_overlap<EPS and minimum_soffit_gap>=.7
    # Retained native instances/analytic boxes must not even enter the deck's reserved headroom bounds.
    native_candidates=[];box_candidates=[];query=a.rect(-8,-3.5,8,3.5)
    for i in a.S['common_instances']:
        b=a.B[i['asset_key']];dy=i['position_m'][1]-3
        if min(3.5,dy+b['max'][1])-max(0,dy+b['min'][1])>EPS and a.overlap(a.bound_poly(i,FRAME),query)>EPS:
            native_candidates.append(i['id'])
    for box in a.S['boxes']:
        sz=box['size_m'];dy=box['position_m'][1]-3
        if min(3.5,dy+sz[1]/2)-max(0,dy-sz[1]/2)>EPS:
            if a.overlap(a.transform_poly(a.rect(-sz[0]/2,-sz[2]/2,sz[0]/2,sz[2]/2),box,FRAME),query)>EPS:
                box_candidates.append(box['id'])
    assert not native_candidates and not box_candidates,(native_candidates,box_candidates)
    asset={'id':KEY,'master_path':a.relative(MASTER),'master_sha256':a.sha(MASTER),'render_path':a.relative(RENDER),'render_sha256':a.sha(RENDER),'master_hash':render['master_hash'],'pitch_m':render['pitch'],'bounds':render['bounds'],'cell_count':render['cell_count'],'quad_count':render['quad_count'],'source':a.ref(MASTER),'cache':a.ref(RENDER)}
    pack={'schema':'riverstone.city.visual_addendum.v1','base_scene_sha256':a.BASE_SHA,'common_assets':{KEY:asset},'add_instances':[INSTANCE],'remove_instance_ids':[],'inspection_cameras':{},'provenance':{'purpose':'Unchanged native stone arch bridge over the preserved east canal.','new_geometry_or_cache_compiled':False,'water_or_terrain_changes_in_pack':False,'audit_path':a.relative(a.HERE/'bridge_audit.json')}}
    a.write('bridge_pack.json',pack)
    a.write('bridge_frame.json',{'schema':'riverstone.city.landward_bridge_frame.v1','base_scene_sha256':a.BASE_SHA,'pack':a.ref(a.HERE/'bridge_pack.json'),'instance':INSTANCE,'axis_x_m':[math.cos(FRAME['yaw_rad']),0,-math.sin(FRAME['yaw_rad'])],'axis_z_m':[math.sin(FRAME['yaw_rad']),0,math.cos(FRAME['yaw_rad'])],'deck_endpoints_m':endpoints,'native_footprint_world_m':footprint,'native_footprint_xz_world_m':[[p[0],p[2]]for p in footprint],'road_reservation_width_m':7,'physical_clear_width_m':7.2,'deck_top_world_m':3,'excluded_road_ground_footprint_local_xz_m':a.rect(-8,-4,8,4),'parent_surface_contract':'Bridge owns deck support; parent excludes appended road ground from the full 16 x 8 m footprint and excludes terrain fills from the wet channel. Parent may trim existing banks at dry landings only.'})
    audit={'schema':'riverstone.city.landward_bridge_native_audit.v1','status':'PASS_STATIC_NATIVE_BRIDGE_MESH_AND_PRESERVED_WATER','base_scene_sha256':a.BASE_SHA,'pack':a.ref(a.HERE/'bridge_pack.json'),'frame':a.ref(a.HERE/'bridge_frame.json'),'author':a.ref(Path(__file__)),'asset_manifest':asset,'native_materials_unchanged':True,'scale':[1,1,1],'compiles_run':0,'mesh_analysis':{'method':'Exact cached-mesh horizontal boundary partition and paired Y intersections; all faces axis-aligned in native space. No compiler invocation and no geometry output.','recovered_constant_xz_solid_columns':len(cols),'recovered_solid_volume_m3':volume,'declared_cells_times_pitch_cubed_m3':render['cell_count']*render['pitch']**3,'volume_identity_pass':True},'deck_collision':{'native_top_local_y_m':0,'world_top_y_m':3,'length_m':16,'physical_clear_width_m':7.2,'reserved_clear_width_m':7,'reserved_headroom_m':3.5,'top_collision_quad_local':top[0],'exact_reserved_support_area_m2':112,'exact_support_slice_thickness_m':.2,'exact_support_slice_volume_m3':support_volume,'headroom_solid_intersections':deck_clear,'retained_native_bounds_candidates':native_candidates,'retained_analytic_box_candidates':box_candidates,'negative_control_below_deck_detects_solid':bool(negative_underdeck),'deck_endpoints_m':endpoints},'waterway':{'source_water_faces':water,'wet_width_bridge_local_m':6,'wet_x_range_bridge_local_m':[-3,3],'under_bridge_wet_area_m2':wet_area,'under_bridge_water_world_y_range_m':[min(water_heights),max(water_heights)],'requested_water_world_y_band_m':[1.2,1.3],'solid_intersections_in_requested_water_band':wet_band,'conservative_minimum_clearance_above_1_3m_band_m':.7,'minimum_exact_soffit_clearance_over_source_water_m':minimum_soffit_gap,'piers_local_x_ranges_m':[[-8,-7],[7,8]],'pier_wet_footprint_overlap_m2':pier_overlap,'pier_to_channel_horizontal_gap_m':4,'water_source_changed':False,'canal_fill_added':False},'limits':['Static frozen native mesh proof; final bank trims, bridge support bearing and source-patch collision interactions are parent-owned.','No GUI, physics traversal, hydrology, load-bearing structural analysis or boat-navigation certification performed.']}
    a.write('bridge_audit.json',audit)
    assert a.sha(a.HERE/'pack.json')==gate_pack_sha, 'Main gate pack changed'
    a.write('bridge_test_results.json',{'status':'PASS','checks':['Exact source/master/render identity','Unchanged native palette and rigid scale','Cached-mesh recovered-volume identity','Continuous 16 x 7 m deck collision support','7 x 3.5 m reserved headroom has no bridge/retained-native/box obstacles','Below-deck negative control detects real collision solid','Exact supplied deck endpoints','Exact original water triangles 96 and 97 bind to frozen scene','Full 6 m wet channel free at requested 1.2–1.3 m world Y','Piers outside wet domain with 4 m horizontal gap','Main gate pack unchanged'],'checks_passed':11,'compiles_run':0,'pack':a.ref(a.HERE/'bridge_pack.json'),'audit':a.ref(a.HERE/'bridge_audit.json'),'scope':'Static exact cached native mesh and original water source only; final source patch/runtime separate.'})
    print(json.dumps({'status':audit['status'],'bridge_pack':a.relative(a.HERE/'bridge_pack.json'),'checks_passed':11,'deck_top_world_m':3,'minimum_exact_soffit_clearance_m':minimum_soffit_gap,'source_water_world_y_range_m':audit['waterway']['under_bridge_water_world_y_range_m'],'compiles_run':0},indent=2))


if __name__=='__main__':
    main()
