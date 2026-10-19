"""Source-profile-bound stave seams, authored as ordinary common operations.

This rule modifies a declared wooden lathe, not arbitrary object semantics.
No mesh engine, collision editing, image reconstruction or footprint expansion.
"""
import copy
import math


def apply(master, spec):
    result = copy.deepcopy(master)
    component = next(c for c in result['components'] if c['id'] == spec['component'])
    operation = next(o for o in component['operations'] if o['id'] == spec['operation'])
    assert operation['action'] == 'paint' and operation['shape']['kind'] == 'lathe'
    assert operation['material'].startswith('timber')
    assert not operation.get('transform'), 'Local transformed lathe needs an explicit composed transform adapter'
    assert all(o['action'] == 'paint' for o in component['operations']), 'Existing body cuts require ordered ownership proof'
    profile = operation['shape']['profile']
    outer = [p[:] for p in profile if p[0] > 0]
    assert len(outer) >= 2 and all(a[1] < b[1] for a, b in zip(outer, outer[1:]))
    depth, width = spec['groove_depth_m'], spec['groove_width_m']
    count = spec['stave_count']
    assert type(count) is int and 8 <= count <= 32
    assert 0 < depth <= min(r for r, y in outer) * .1
    assert 0 < width < 2 * math.pi * min(r for r, y in outer) / count * .25
    polygon = [[r-depth, y] for r, y in outer] + [[r+.05, y] for r, y in outer[::-1]]
    added = []
    for i in range(count):
        angle = 2 * math.pi * (i + spec.get('phase', .5)) / count
        c, s = math.cos(angle), math.sin(angle)
        added.append({'id':f'stave_seam_{i:02}', 'part':operation['part'], 'action':'cut',
                      'selector':{'component':component['id'], 'operation':operation['id']},
                      'shape':{'kind':'extrusion', 'polygon':copy.deepcopy(polygon),
                               'z_min':-width/2, 'z_max':width/2},
                      'transform':{'basis':[[c,0,s],[0,1,0],[-s,0,c]]},
                      'metadata':{'source_profile_operation':operation['id'],
                                  'detail_rule':'profile_following_stave_seam_v1'}})
    radius, top = outer[-1]
    spacing = spec['cap_board_spacing_m']
    assert width < spacing < radius
    for i in range(-math.ceil(radius/spacing), math.ceil(radius/spacing)+1):
        x = i * spacing
        if abs(x) + width/2 >= radius:
            continue
        added.append({'id':f'cap_board_seam_{i:+03}', 'part':operation['part'], 'action':'cut',
                      'selector':{'component':component['id'], 'operation':operation['id']},
                      'shape':{'kind':'box','min':[x-width/2,top-depth,-radius],
                               'max':[x+width/2,top+.025,radius]},
                      'metadata':{'detail_rule':'source_cap_board_seam_v1'}})
    # Appending cuts to this source component cannot select later hoop instances.
    component['operations'].extend(added)
    result['revision'] = master.get('revision', 0) + 1
    result['id'] = master['id'] + '_stave_detail_r01'
    result.setdefault('extensions', {})['near_detail_rule'] = copy.deepcopy(spec)
    return result, added
