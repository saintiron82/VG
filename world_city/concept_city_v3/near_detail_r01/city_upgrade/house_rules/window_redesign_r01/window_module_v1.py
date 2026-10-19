"""Reusable rectangular window source for new architectural assemblies.

Local X spans the aperture, Y rises from its bottom, +Z faces outside; wall
exterior is z=0. Return opening_cut to the WALL component, window component to
its own instance with the SAME placement transform. Never cut another component
implicitly. This source API does not compile, alter structure or bind runtime.
"""
import copy, math, re
from pathlib import Path
import revise_windows as base

HERE = Path(__file__).resolve().parent
STATES = ('glazed_closed', 'glazed_closed_shutters_open', 'shutters_closed')


def _positive(value, name):
    base.need(type(value) in (int, float) and math.isfinite(value) and value > 0,
              name + ' must be finite and positive')
    return float(value)


def build_window_module(width, height, style='thin_wood_casement',
                        state='glazed_closed', side_clearance=None, *,
                        module_id='window', wall_depth_m=.35,
                        wall_part_id='wall', materials=None,
                        material_slots=None):
    """Return component, opening_cut, axes, dimensions and explicit state.

    width/height are the clear MASONRY aperture, not outer-frame size. Materials
    is the caller's unchanged common materials dictionary. material_slots maps
    semantic wood_light, wood_dark, plaster, glass, metal to existing IDs.
    Side-open shutters require measured left/right clearance outside aperture.
    Closed shutters require no sideways space; their slabs cover the aperture.
    Hinged/open casement and open-void are intentionally unsupported.
    """
    w = _positive(width, 'width'); h = _positive(height, 'height')
    depth = _positive(wall_depth_m, 'wall_depth_m')
    base.need(isinstance(module_id, str) and re.fullmatch(r'[A-Za-z][A-Za-z0-9_]*', module_id), 'Invalid module_id')
    base.need(isinstance(wall_part_id, str) and wall_part_id, 'wall_part_id required')
    rules = base.load(HERE/'window_rules.v1.json')
    variants = base.load(HERE/'window_variants.v2.json')
    base.need(style in variants['styles'], 'Unsupported rectangular window style')
    base.need(state in STATES, 'Unsupported state; hinged/open casement requires its own geometry contract')
    preset = variants['styles'][style]
    base.need(isinstance(materials, dict) and materials, 'Caller material definitions required')
    slots = {'wood_light':'timber_light', 'wood_dark':'timber_dark', 'plaster':'plaster',
             'glass':'glass', 'metal':'iron'}
    if material_slots:
        base.need(set(material_slots) <= set(slots), 'Unknown semantic material slot')
        slots.update(material_slots)
    separate = preset['separate_recessed_casement']
    inside = preset['casement_width_m'] if separate else rules['frame_inside_aperture_m']
    outside = preset['trim_width_m'] if separate else rules['frame_width_m']-inside
    recess = preset['glass_recess_m']
    base.need(depth >= recess+rules['glass_thickness_m'], 'Wall too shallow for requested recessed glazing')
    base.need(min(w-2*inside, h-2*inside) >= rules['minimum_clear_span_m'], 'Window too small for clear-span contract')
    required = {'glass', 'wood_dark' if separate else 'wood_light'}
    if separate: required.add('plaster')
    if state != 'glazed_closed': required.update(('wood_light', 'metal'))
    base.need(all(slots[s] in materials for s in required), 'Required caller material slot missing')
    if state == 'glazed_closed_shutters_open':
        base.need(isinstance(side_clearance, dict) and set(side_clearance)=={'left','right'}, 'Side-open shutters require measured left/right side_clearance')
        needed = w/2+outside+rules['open_shutter_clearance_m']
        for side in ('left','right'):
            base.need(_positive(side_clearance[side], side+'_clearance') >= needed,
                      'Insufficient '+side+' shutter clearance')
    else:
        needed = 0
    ops=[];axes=[];semantic=[]
    def box(suffix, lo, hi, slot, role, axis=None):
        ident=module_id+'_'+suffix
        op={'id':ident,'part':'windows','action':'paint','material':slots[slot],
            'shape':{'kind':'box','min':[],'max':[]}}
        base.set_box(op,lo,hi);ops.append(op)
        semantic.append({'operation_id':ident,'role':role,'material':slots[slot]})
        if axis:
            axes.append({'component_id':module_id,'operation_id':ident,'part_id':'windows',
                         'material':slots[slot],'role':role,'grain_axis_component_local':axis})
        return op
    x0,x1=-w/2,w/2
    box('glass',[x0,0,-recess-rules['glass_thickness_m']],[x1,h,-recess], 'glass','closed_glazing')
    if separate:
        z0,z1=preset['trim_back_m'],preset['trim_front_m']
        for suffix,lo,hi in (
            ('trim_left',[x0-outside,-outside,z0],[x0,h+outside,z1]),
            ('trim_right',[x1,-outside,z0],[x1+outside,h+outside,z1]),
            ('trim_sill',[x0-outside,-outside,z0],[x1,0,z1]),
            ('trim_head',[x0-outside,h,z0],[x1,h+outside,z1])):
            box(suffix,lo,hi,'plaster','nonstructural_plaster_surround')
        z0,z1=preset['casement_back_m'],preset['casement_front_m'];slot='wood_dark';ext=0
    else:
        z0,z1=rules['frame_back_from_wall_m'],rules['frame_front_from_wall_m'];slot='wood_light';ext=outside
    for suffix,lo,hi,axis in (
        ('frame_left',[x0-ext,-ext,z0],[x0+inside,h+ext,z1],[0,1,0]),
        ('frame_right',[x1-inside,-ext,z0],[x1+ext,h+ext,z1],[0,1,0]),
        ('frame_bottom',[x0-ext,-ext,z0],[x1+ext,inside,z1],[1,0,0]),
        ('frame_head',[x0-ext,h-inside,z0],[x1+ext,h+ext,z1],[1,0,0])):
        box(suffix,lo,hi,slot,'nonstructural_wood_casement',axis)
    cross=rules['mullion_width_m'];half=cross/2
    cz0,cz1=(z0,z1) if separate else (rules['mullion_back_from_wall_m'],rules['mullion_front_from_wall_m'])
    box('mullion',[-half,inside,cz0],[half,h-inside,cz1],slot,'vertical_mullion',[0,1,0])
    box('transom',[x0+inside,h/2-half,cz0],[x1-inside,h/2+half,cz1],slot,'horizontal_transom',[1,0,0])
    # A separate shallow sill remains a window part, never a structural beam.
    sill_slot='plaster' if separate else slot;sill_axis=None if separate else [1,0,0]
    for suffix,ya,yb,front in [('sill_lower',rules['sill_lower_y_m'],rules['sill_step_y_m'],.12),('sill_top',rules['sill_step_y_m'],rules['sill_top_y_m'],rules['sill_front_m'])]:
        box(suffix,[x0-rules['sill_side_extension_m'],ya,-.10],[x1+rules['sill_side_extension_m'],yb,front],sill_slot,'nonstructural_sill',sill_axis)
    if state != 'glazed_closed':
        for side,sign in [('left',-1),('right',1)]:
            if state=='shutters_closed':a,b=(x0,0) if sign<0 else (0,x1)
            elif sign<0:b=x0-outside-rules['open_shutter_clearance_m'];a=b-w/2
            else:a=x1+outside+rules['open_shutter_clearance_m'];b=a+w/2
            # Continuous backing makes "closed" opaque; raised vertical planks
            # retain relief without creating unintended open gaps in the leaf.
            box('shutter_'+side,[a,0,.125],[b,h,.175],'wood_light','opaque_shutter_leaf',[0,1,0])
            count=max(2,math.ceil((b-a)/.18));step=(b-a)/count
            for k in range(count):
                gap=min(.025,step/8)
                box('shutter_'+side+'_plank_'+str(k),[a+k*step+gap/2,0,.175],[a+(k+1)*step-gap/2,h,.225], 'wood_light','shutter_vertical_plank',[0,1,0])
            for k,y in enumerate((h*.25,h*.75)):
                box('shutter_'+side+'_strap_'+str(k),[a,y-.025,.225],[b,y+.025,.25],'metal','shutter_hardware')
    component={'id':module_id,'parts':[{'id':'windows','pivot':[0,0,0]}],'operations':ops}
    cut={'id':module_id+'_aperture','part':wall_part_id,'action':'cut',
         'shape':{'kind':'box','min':[x0,0,-depth-.025],'max':[x1,h,.025]},
         'selector':{'part':wall_part_id}}
    test_master={'schema':base.a.core.SCHEMA,'id':module_id,'revision':1,
                 'axes':{'up':'+Y','front':'+Z','right':'+X'},'grid_origin':[0,0,0],
                 'materials':copy.deepcopy(materials),'components':[component],
                 'instances':[{'id':module_id,'component':module_id}],
                 'assembly_cuts':[],'constraints':[]}
    base.a.core.validate_master(test_master,.05)
    lo=[min(op['shape']['min'][j] for op in ops) for j in range(3)]
    hi=[max(op['shape']['max'][j] for op in ops) for j in range(3)]
    clear=[w-2*inside,h-2*inside];outer=[w+2*outside,h+2*outside]
    return {'schema':'riverstone.window_module.v1','component':component,'opening_cut':cut,
            'grain_axes':axes,'operation_roles':semantic,'style_id':style,'state_id':state,
            'dimensions':{'aperture_m':[w,h],'clear_frame_span_m':clear,'outer_span_m':outer,
                'frame_inside_aperture_m':inside,'surround_outside_aperture_m':outside,
                'mullion_width_m':cross,'glass_recess_m':recess,'glass_thickness_m':rules['glass_thickness_m'],
                'wall_depth_m':depth,'required_side_clearance_m':needed,
                'projected_visible_glass_ratio':0 if state=='shutters_closed' else (clear[0]-cross)*(clear[1]-cross)/(outer[0]*outer[1]),
                'ratio_scope':'Analytic frame/cross projection, excluding structure and voxel phase'},
            'bounds':{'min':lo,'max':hi},
            'state_contract':{'glazing':'closed','shutters':{'glazed_closed':'absent','glazed_closed_shutters_open':'side_open','shutters_closed':'closed'}[state],
                              'passage_open':False,'structural_members_included':False},
            'placement_contract':{'local_wall_front_z':0,'local_window_bottom_y':0,'local_window_center_x':0,
                 'outward_axis':'+Z','opening_cut_owner':'caller wall component',
                 'window_instance_transform':'same pose as corresponding wall cut; caller owns transforms',
                 'near_far':'use identical component operations; coarse-only silhouette remains unverified'},
            'provenance':{'module_engine_sha256':base.a.sha(__file__),
                 'base_rules_sha256':base.a.sha(HERE/'window_rules.v1.json'),
                 'variants_sha256':base.a.sha(HERE/'window_variants.v2.json'),
                 'seed':rules['seed'],'compile_run':False,'runtime_activation':False}}
