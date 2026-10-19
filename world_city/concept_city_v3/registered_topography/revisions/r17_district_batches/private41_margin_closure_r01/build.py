"""One source-bound nonwalking support wedge under retained E4 masonry."""
import json, math, hashlib
from pathlib import Path
from .. import author as a
HERE = Path(__file__).resolve().parent
NOBLE = a.CITY/'assemblies/landmarks/registered/precinct_r06_whole/residual_completion_r01/noble_entry_batch_r01'
BATCH = a.HERE/'coherent_batch18_r01'

def ref(p): return dict(path=str(p.relative_to(a.ROOT)), sha256=a.sha(p))
def write(name, data):
    p=HERE/name
    assert not p.exists(), p
    p.write_text(json.dumps(data,separators=(',',':'))+'\n')
    return ref(p)

def build():
    source=json.loads((HERE/'source_component_r01.json').read_bytes())
    pack=json.loads((NOBLE/'resolved_placements.json').read_bytes())
    placement=next(p for p in pack['placements'] if p['id']=='R06_NOBLE_ENTRY_R01:E4:retained_base')
    cache=a.ROOT/placement['cache']['path']; assert a.sha(cache)==placement['cache']['sha256']
    render=json.loads(cache.read_bytes()); assert placement['yaw_rad']==0 and placement['scale']==[1,1,1]
    quad=render['groups'][1]['quads'][278]
    world=[[v[k]+placement['position_m'][k] for k in range(3)] for v in quad]
    assert a.normal_y(world[:3])<0 and all(v[1]==12.5 for v in world)
    footprint=[[v[0],v[2]]for v in world]
    owner=source['owner']; edge=source['unknown_edge_xz_m']; low=owner['plane_y_xz_m'][2]; high=12.5
    poly=a.clip(owner['polygon_xz_m'],footprint)
    assert poly and all(a.geo.point_in_convex_polygon(p,poly,1e-8) for p in edge)
    # This triangular wedge is the complete finite portion beneath the retained
    # native bottom inside the regraded court. It is not an unknown soil hole.
    lacuna=json.loads((BATCH/'lacuna_scope_review_r01.json').read_bytes())
    missing=[r['polygon_xz_m']for r in lacuna['records']]
    residual=sum(a.geo.polygon_area(p)for p in a.common.subtract([poly],missing))
    reverse=sum(a.geo.polygon_area(p)for p in a.common.subtract(missing,[poly]))
    assert max(residual,reverse)<1e-9
    prepared=json.loads((BATCH/'effective_prepared_parcels_r03.json').read_bytes())
    parcel=next(p for p in prepared['parcels']if p['id']=='BLOCK_001:R8_C002')
    checks={}
    for key,polygons in parcel.items():
        if isinstance(polygons,list) and key.endswith('polygons_xz_m') and ('walk' in key or 'foot' in key or 'entry' in key):
            area=sum(a.geo.polygon_area(q)for p in polygons if(q:=a.clip(poly,p)))
            checks[key]=area
            assert area<1e-9,(key,area)
    u,v=edge
    ul=[u[0],low,u[1]];vl=[v[0],low,v[1]];uh=[u[0],high,u[1]];vh=[v[0],high,v[1]]
    triangles=[[ul,uh,vh],[ul,vh,vl]]
    # Orient the vertical face toward the retained lower court, away from the
    # supporting wedge's interior. No double-sided material is used.
    center=[sum(p[k]for p in poly)/len(poly)for k in(0,1)];mid=[(u[k]+v[k])/2 for k in(0,1)]
    def outward(tri):
        b=[tri[1][k]-tri[0][k]for k in range(3)];c=[tri[2][k]-tri[0][k]for k in range(3)]
        n=[b[1]*c[2]-b[2]*c[1],b[2]*c[0]-b[0]*c[2],b[0]*c[1]-b[1]*c[0]]
        return n[0]*(mid[0]-center[0])+n[2]*(mid[1]-center[1])
    triangles=[t if outward(t)>0 else[t[0],t[2],t[1]]for t in triangles]
    assert all(a.normal_y(t)==0 and outward(t)>0 for t in triangles)
    length=math.dist(u,v);area=a.geo.polygon_area(poly)
    refs=[ref(HERE/'source_component_r01.json'),ref(NOBLE/'resolved_placements.json'),ref(cache),ref(BATCH/'physical_owner_handoff_r02.json'),ref(BATCH/'lacuna_scope_review_r01.json'),ref(BATCH/'effective_prepared_parcels_r03.json')]
    result=dict(schema='riverstone.finite_native_support_closure.v1',status='EXACT_SOURCE_BOUND_NONWALKING_SUPPORT_READY',source_refs=refs,base_scene=source['source_scene'],resolved_boundary_owner_id=owner['id'],holding_id=owner['holding_id'],source_native=dict(placement=placement,render_group_index=1,downward_quad_index=278,vertices_xyz_m=world,normal_y=a.normal_y(world[:3])),support_owner=dict(id='BLOCK_001:R8_C002:E4_FOUNDATION_SUPPORT:0',kind='retained_native_foundation_support',polygon_xz_m=poly,lower_plane_y_xz_m=owner['plane_y_xz_m'],upper_plane_y_xz_m=[0,0,high],render_top=False,walking=False,volume_m3=area*(high-low)),rendered_top_suppression=dict(owner_id=owner['id'],polygon_xz_m=poly,reason='Retained masonry bottom now has an explicit finite support wedge; hide its internal lower court top.'),boundary_connection=dict(id='BLOCK_001:R8_C002:E4_FOUNDATION_CONNECTION:0',edge_xz_m=edge,lower_xyz_m=[ul,vl],upper_xyz_m=[uh,vh],material='bank',triangles_xyz_m=triangles,length_m=length,rise_m=high-low,area_m2=length*(high-low),walking=False),review=dict(footprint_area_m2=area,prior_lacuna_forward_difference_m2=residual,prior_lacuna_reverse_difference_m2=reverse,protected_route_and_footing_intersections_m2=checks,top_plane_changes_outside_support_m2=0,native_geometry_changes=0),integration_policy='Compose the exact suppression into the private top owner. Resolve this one unknown edge using the explicit connection, once only. Keep lower physical earth as the wedge base and top unrendered beneath native masonry. Other two wedge boundaries meet retained ground/masonry and remain with the joint boundary owner pass. No new walkable crossing.',superseded_interpretation='The two prior 0.02354677872 m2 unowned-lacuna labels are replaced by actual retained E4 downward-bearing ownership. Prior evidence stays immutable.',activation=False,runtime_approval=False)
    output=write('closure_contract.json',result)
    print(output,flush=True)
    return result
if __name__=='__main__':build()
