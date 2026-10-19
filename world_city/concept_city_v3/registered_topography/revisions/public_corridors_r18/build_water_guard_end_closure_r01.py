import json,math
from .height_field import HERE
from .classify_top_holes_r02 import a,ref

def main():
 cp=HERE/'unknown_boundary_classification_r05_context.json';d=json.loads(cp.read_bytes());r=next(r for r in d['rows']if r['owner_id']=='R18_FINITE:9604:2');low=next(q['surface']for q in r['native_and_contract_intervals']if q['surface']['id']=='REGISTERED_WATER_CROSSING:MARKET_NORTH:UP:1:28');root=a.CITY/'assemblies/waterworks/registered_water_completion_r01';render=root/'cache/market_north.render.json'
 assert a.sha(render)=='f27b05cb1f7323c1621332ec00f5743895f9b61e8a33b409dd87e031539aa0ee'
 p,q=r['edge_xz_m'];ys=[a.common.height(r['owner_plane_y_xz_m'],x)for x in(p,q)];zs=[a.common.height(low['plane_y_xz_m'],x)for x in(p,q)];assert max(abs(z-15.6)for z in zs)<1e-10
 v=[[p[0],ys[0],p[1]],[q[0],ys[1],q[1]],[q[0],zs[1],q[1]],[p[0],zs[0],p[1]]];tris=[[v[0],v[1],v[2]],[v[0],v[2],v[3]]];base=json.loads((a.CITY/'registered_integration/r8/joint_boundary_r05/surface_patch.json').read_bytes())
 patch=dict(schema='riverstone.frozen_scene_patch.v1',id='R18_MARKET_NORTH_GUARD_END_STRUCTURAL_CLOSURE_R01',status='BOUNDED_NONWALKING_SIDE_CANDIDATE',base_scene_sha256=base['base_scene_sha256'],source_surface_hashes={},surface_edits=[],appended_surfaces={'bank':[v for t in tris for v in t]},removed_foundation_proxy_ids=[],source_references=[ref(cp),ref(render),ref(root/'crossing_interfaces.json'),ref(__import__('pathlib').Path(__file__))]);op=HERE/'water_guard_end_side_patch_r01.json';op.write_text(json.dumps(patch,separators=(',',':'))+'\n')
 review=dict(status='EXACT_FINITE_NONWALKING_JOIN',patch=ref(op),owner_id=r['owner_id'],edge_xz_m=r['edge_xz_m'],length_m=math.dist(p,q),public_y_m=ys,lower_actual_deck_y_m=zs,native_deck_face=low,rail_cap_excluded=True,walking_geometry_unchanged=True,source_refs=patch['source_references'],semantics='Outer guard-strip end, native local X+5, Z[-3.003392,-3], outside the6m traffic strip. Native side Y13.6–15.6 and separate railY16.4–16.8 leave this exact gap; join stops at actual deck top15.6, never rail cap.');rp=HERE/'water_guard_end_side_review_r01.json';rp.write_text(json.dumps(review,separators=(',',':'))+'\n');print(ref(op),ref(rp))
if __name__=='__main__':main()
