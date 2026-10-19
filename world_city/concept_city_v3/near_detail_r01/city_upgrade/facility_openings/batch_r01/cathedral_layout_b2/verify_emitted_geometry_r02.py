"""Versioned verifier: distinguish exposed restoration from hidden solid joins.

The frozen r01 verifier and its failing result remain preserved. This version
requires emitted closed-solid ray coverage where the unchanged source occupies
both sides of a former window plane; it never adds or changes geometry.
"""
import json,sys
from pathlib import Path
import verify_emitted_geometry as v
HERE=Path(__file__).resolve().parent
ORIGINAL=v.validate_ray
PROOF=HERE/'old_cavity_exposure.json'

def hidden_result(r,result,w):
    hits=result['ordered_hits'];expected=r['expected_front_depth_m'];problems=[]
    if any(v.close(h['depth_m'],expected) for h in hits):problems.append('unexpected_internal_face_at_hidden_restoration')
    if any(h['material']=='glass' and -.35-v.EPS<=h['depth_m']<=.1+v.EPS for h in hits):problems.append('stale_glass_at_restored_solid_join')
    cover=[]
    for depth in (expected-.025,expected+.025):
        prefix=[h for h in hits if h['depth_m']>depth+v.EPS]
        correct=bool(len(prefix)%2) and all(h['normal_outward']==(1 if i%2==0 else -1) for i,h in enumerate(prefix))
        correct=correct and bool(prefix) and prefix[-1]['material'] in ('stone','stone_dark','stone_light')
        cover.append({'local_depth_m':depth,'occupied_by_emitted_ray':correct,'crossing_count':len(prefix)})
        if not correct:problems.append('hidden_restoration_missing_emitted_solid_coverage')
    result.update(pass_=not problems)
    result.pop('pass_',None);result.update({'pass':not problems,'problems':problems,'restoration_exposure':'hidden_solid_join','source_exposure_witness':w,'emitted_adjacent_cell_coverage':cover,'interpretation':'No internal quad is expected. Both adjacent common-source samples are occupied, and actual emitted surface crossings put both points inside the restored solid.'})
    return result

def validate(r):
    result=ORIGINAL(r)
    if r['kind']!='old_restoration':return result
    proof=v.load(PROOF);assert proof['canonical_master_sha256']==v.load(HERE/'catalog.json')['canonical_master_sha256']
    w=next(w for w in proof['witnesses'] if w['patch_id']==r['patch_id'] and v.close(w['local_x_m'],r['requested_window_xy_m'][0]))
    assert all(v.close(x,y) for x,y in zip(w['sample_yz_m'],r['sample_master_yz_m']))
    if w['surface_exposed']:result['restoration_exposure']='exposed_wall_face';return result
    assert w['hidden_solid_continuation'] and w['inside_label'] and w['outside_label']
    return hidden_result(r,result,w)

def tests():
    r={'expected_front_depth_m':-.02};w={'hidden_solid_continuation':True};base={'ordered_hits':[{'depth_m':2.38,'normal_outward':1,'material':'stone'}]}
    assert hidden_result(r,dict(base),w)['pass']
    assert not hidden_result(r,{'ordered_hits':[]},w)['pass']
    assert not hidden_result(r,{'ordered_hits':base['ordered_hits']+[{'depth_m':-.02,'normal_outward':1,'material':'stone'}]},w)['pass']
    assert not hidden_result(r,{'ordered_hits':base['ordered_hits']+[{'depth_m':-.22,'normal_outward':1,'material':'glass'}]},w)['pass']
    return {'tests':4,'pass':True,'scope':'Hidden-solid ray coverage, missing exterior cover, fake internal face, stale glass.'}

def main():
    if '--self-test' in sys.argv:print(json.dumps({'r01':v.self_test(),'r02':tests()}));return 0
    assert tests()['pass'];v.validate_ray=validate;code=v.main()
    if '--prepare-only' in sys.argv:return code
    path=HERE/'emitted_geometry_qa.json';result=v.load(path);proof=v.load(PROOF);result['verifier']=v.ref(Path(__file__));result['base_verifier']=v.ref(HERE/'verify_emitted_geometry.py');result['old_cavity_exposure_reference']=v.ref(PROOF);result['old_cavity_classification_implementation']=v.ref(HERE/'classify_old_cavity_exposure.py');result['verification_revision']='r02_exposed_surface_vs_hidden_solid_restoration';result['restoration_exposure_counts']={'exposed_wall_faces':proof['exposed_count'],'hidden_solid_joins':proof['hidden_count']};result['old_restoration_semantics']='Thirty old restoration witnesses require actual stone/stone_light wall faces. Two source-backed transept joins require no internal face and occupied intervals on both sides, measured from actual emitted ray crossings. Frozen r01 failure evidence is retained.';path.write_text(json.dumps(result,sort_keys=True,separators=(',',':'))+'\n');return code
if __name__=='__main__':sys.exit(main())
