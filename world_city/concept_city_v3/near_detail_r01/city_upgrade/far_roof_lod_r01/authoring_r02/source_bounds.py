"""Negative separation proofs only, using the unchanged common source bounds.

An enclosing AABB never authorizes a roof, floor, mesh or filled volume. Rigid
rotations are enclosed, not approximated by unrotated extents. Contact and any
positive or uncertain overlap cannot prove disjointness.
"""
from fractions import Fraction
import itertools,math
from voxel_character.common import core


def outward(value,lower):
    """Enclose an exact rational in binary64 without tolerance widening policy."""
    f=float(value)
    if not math.isfinite(f):raise ValueError('nonfinite transformed source bounds')
    if (Fraction(f)>value if lower else Fraction(f)<value):
        f=math.nextafter(f,-math.inf if lower else math.inf)
    if not math.isfinite(f):raise ValueError('overflow in source bounds')
    return f


def transformed_bounds(shape,transform,pitch):
    if not core.number(pitch)or pitch<=0:raise ValueError('invalid source pitch')
    t=core.transform(transform)
    prepared=core.prepare_shape(shape,pitch)
    lo,hi=core.shape_bounds(prepared)
    if not(core.vector(lo)and core.vector(hi)and all(a<=b for a,b in zip(lo,hi))):
        raise ValueError('invalid common source bounds')
    # core tube bounds include a single rounded addition/subtraction. Enclose
    # those operations (and all other primitive bounds) by one outward ULP.
    lo=[math.nextafter(float(x),-math.inf)for x in lo]
    hi=[math.nextafter(float(x),math.inf)for x in hi]
    if not all(math.isfinite(x)for x in lo+hi):raise ValueError('nonfinite local enclosure')
    exact=[]
    for p in itertools.product(*zip(lo,hi)):
        exact.append([sum(Fraction(t['basis'][i][j])*Fraction(p[j])for j in range(3))+Fraction(t['translation'][i])for i in range(3)])
    return {'min':[outward(min(p[i]for p in exact),True)for i in range(3)],
            'max':[outward(max(p[i]for p in exact),False)for i in range(3)]}


def strictly_disjoint(a,b):
    return any(a['max'][i]<b['min'][i]or b['max'][i]<a['min'][i]for i in range(3))


def union_bounds(rows):
    if not rows:raise ValueError('empty source paint bounds')
    return {'min':[min(r['min'][i]for r in rows)for i in range(3)],
            'max':[max(r['max'][i]for r in rows)for i in range(3)]}


def audit_paints(master,source_parts,pitch,roof_materials):
    rows=[]
    for ins,op,t in source_parts(master):
        if op['action']!='paint':continue
        b=transformed_bounds(op['shape'],t,pitch)
        rows.append({'instance':ins['id'],'component':ins['component'],'operation':op['id'],
                     'material':op['material'],'shape_kind':op['shape']['kind'],
                     'roof_material':op['material']in roof_materials,
                     'operation_sha256':core.digest(op),'transform_sha256':core.digest(t),
                     'source_shape_prepared_at_pitch_m':pitch,
                     'minimum_rule_changes_shape':core.prepare_shape(op['shape'],pitch)!=op['shape'],
                     'conservative_transformed_bounds':b})
    return {'method':'unchanged common.core.prepare_shape + shape_bounds; outward local bounds, exact-rational affine corner transform, outward binary64 enclosure',
            'purpose':'negative separation / descriptive envelope only; never geometry or volume',
            'all_paint_count':len(rows),'nonroof_paint_count':sum(not r['roof_material']for r in rows),
            'conservative_all_paint_bounds':union_bounds([r['conservative_transformed_bounds']for r in rows]),'operations':rows}


def strict_cut_proofs(master,source_parts,pitch,roof_materials):
    """Replay component and assembly cut selectors before trusting AABB exclusion."""
    components={c['id']:c for c in master['components']}
    # Source_parts gives op-composed transforms. Instance transforms are needed
    # separately for component cuts; use the existing source instance helper.
    import author_facility_roofs as roofs
    transforms=roofs.instance_transforms(master);proofs=[]
    for ins,op,t in source_parts(master):
        if op['action']!='paint'or op.get('material')not in roof_materials:continue
        cell={'instance':ins['id'],'component':ins['component'],'part':op['part'],'material':op['material'],'feature':op['id']}
        ob=transformed_bounds(op['shape'],t,pitch)
        cuts=[('component',c)for c in components[ins['component']]['operations']if c['action']=='cut']+[('assembly',c)for c in master.get('assembly_cuts',[])]
        for scope,cut in cuts:
            record={'instance':ins['id'],'component':ins['component'],'operation':op['id'],'cut':cut['id'],'scope':scope,'cut_operation_sha256':core.digest(cut)}
            if not core.selector_matches(cut.get('selector',{}),cell):
                proofs.append({**record,'exclusion':'selector_excludes_roof_operation'});continue
            ct=core.transform(cut.get('transform'))
            if scope=='component':ct=core.compose(transforms[ins['id']],ct)
            cb=transformed_bounds(cut['shape'],ct,pitch)
            if not strictly_disjoint(ob,cb):
                raise ValueError('ROOF_CUT_ENVELOPE_TOUCH_OR_OVERLAP: '+ins['id']+'/'+op['id']+'/'+cut['id'])
            proofs.append({**record,'exclusion':'strictly_disjoint_conservative_transformed_aabb','roof_operation_aabb':ob,'cut_aabb':cb})
    return proofs
