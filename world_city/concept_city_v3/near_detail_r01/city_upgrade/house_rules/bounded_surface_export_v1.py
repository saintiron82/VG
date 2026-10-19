"""Export bounded cell geometry without inferring whole-source constraints.

Nonempty/connected source conditions may fail locally. This adapter leaves that
bounded result unchanged. Its geometry-only view passes through the existing
common exporter's cell hash, grid, material and duplicate-coordinate checks.
The caller must separately aggregate the complete source domain fail-closed.
"""
from voxel_character.common.render_data import make_render_data


def make_bounded_render_data(compiled):
    scope=compiled.get('evaluation_scope',{})
    if (compiled.get('schema')!='riverstone.voxel.compiled.v1' or scope.get('kind')!='cell_bounds' or
        compiled.get('valid_scope')!='cell_bounds_only' or compiled.get('global_constraints_evaluated') is not False or
        compiled.get('global_constraints_valid') is not None):
        raise ValueError('Surface adapter requires explicitly bounded, non-global common output')
    if any(type(v)is not int for k in ('min','max') for v in scope.get(k,[])) or any(len(scope.get(k,[]))!=3 for k in ('min','max')):
        raise ValueError('Bounded surface geometry requires exact integer ownership bounds')
    checks=compiled.get('constraints')
    if not isinstance(checks,list) or any(c.get('kind') not in ('nonempty','connected') or
            type(c.get('pass'))is not bool or c.get('scope')!='cell_bounds_only' or c.get('global_pass') is not None for c in checks):
        raise ValueError('Unsupported or unscoped deferred constraint')
    if compiled.get('valid')!=all(c['pass'] for c in checks):
        raise ValueError('Common bounded validity differs from its actual constraint results')
    view={**compiled,'valid':True,'valid_scope':'cell_payload_geometry_export_only','constraints':[],
          'deferred_source_constraint_results':checks,'global_constraints_evaluated':False,'global_constraints_valid':None}
    result=make_render_data(view)
    result['provenance']['constraint_scope']='Cell geometry only; source constraints require separate full-domain aggregation.'
    result['provenance']['global_constraints_inferred']=False
    return result
