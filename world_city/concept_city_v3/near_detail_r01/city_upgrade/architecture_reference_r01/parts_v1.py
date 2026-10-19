"""Measured architectural source parts in the existing Assembly/common grammar.

This is an authoring library, not a voxel sampler. No dimensions are inferred
from the perspective reference. Final production emission is measurement-gated.
"""
from copy import deepcopy
import hashlib, math, sys
from pathlib import Path
ROOT=next(p for p in Path(__file__).resolve().parents if (p/'world_city/runtime_city/archetypes/ordinary.py').exists())
sys.path.insert(0,str(ROOT))
from world_city.runtime_city.archetypes.ordinary import _Assembly, _box, _extrusion, _source, ROTATIONS, SCHEMA
from world_city.runtime_city.archetypes.ordinary_r2 import _roof_gable
from voxel_character.common import core
WINDOW_ROOT=Path(__file__).resolve().parent.parent/'house_rules/window_redesign_r01'
sys.path.insert(0,str(WINDOW_ROOT))
from window_module_v1 import build_window_module


def need(ok,message):
    if not ok: raise ValueError(message)


def positive(v,name):
    need(type(v) in (int,float) and math.isfinite(v) and v>0,name+' must be finite and positive')
    return float(v)


def unit_material(unit_id,family,slots,seed):
    """One stable tone per brick/tile/board, independent of cells and emission order."""
    need(isinstance(unit_id,str) and unit_id,'Stable physical unit ID required')
    need(1<=len(slots)<=3 and len(slots)==len(set(slots)),'Use one to three distinct family tones')
    digest=hashlib.sha256((str(seed)+'\0'+family+'\0'+unit_id).encode()).digest()
    return slots[int.from_bytes(digest[:8],'big')%len(slots)]


class AssemblyKit(_Assembly):
    def __init__(self,asset_id,palette=None,seed='architecture_reference_r01'):
        super().__init__();self.asset_id=asset_id;self.materials=deepcopy(palette or _source()[0]['materials']);self.seed=seed
        self.grain_axes=[];self.units=[];self.openings=[];self.reservations=[];self.connections=[]

    def component(self,name,category):
        need(not any(c['id']==name for c in self.components),'Duplicate component '+name)
        c=super().component(name,category);c['metadata']={'source_category':category};return c

    def solid_box(self,ident,lo,hi,material='timber',role='structural_member',grain=None):
        need(material in self.materials,'Unknown material');c=self.component(ident,role)
        self.paint(c,ident,_box(lo,hi),material);self.instance(c)
        if grain is not None:
            need(core.vector(grain) and abs(sum(x*x for x in grain)-1)<1e-8,'Unit grain vector required')
            self.grain_axes.append({'component_id':ident,'operation_id':ident,'part_id':'solid','material':material,'role':role,'grain_axis_component_local':grain})
        self.units.append({'unit_id':ident,'component_id':ident,'role':role,'material':material})
        return c

    def plank(self,ident,lo,hi,slots=('timber',),grain=(0,1,0)):
        return self.solid_box(ident,lo,hi,unit_material(ident,'plank',slots,self.seed),'individual_timber_board',list(grain))

    def perforated_board(self,ident,width,height,thickness,diamond_width,diamond_height,position,side='front',slots=('timber_light',)):
        w,h,t=[positive(x,n) for x,n in [(width,'width'),(height,'height'),(thickness,'thickness')]]
        need(0<diamond_width<w and 0<diamond_height<h,'Diamond must leave real solid edge and top/bottom ligaments')
        c=self.component(ident,'pierced_timber_balustrade_board');material=unit_material(ident,'plank',slots,self.seed)
        self.paint(c,'board',_box((-w/2,0,-t/2),(w/2,h,t/2)),material)
        cy=h/2;self.cut(c,'pierced_diamond',_extrusion([(0,cy-diamond_height/2),(diamond_width/2,cy),(0,cy+diamond_height/2),(-diamond_width/2,cy)],-t,t))
        self.instance(c,position=position,side=side);self.units.append({'unit_id':ident,'component_id':ident,'role':'pierced_baluster','material':material})
        self.grain_axes.append({'component_id':ident,'operation_id':'board','part_id':'solid','material':material,'role':'pierced_baluster','grain_axis_component_local':[0,1,0]})
        return c

    def brace(self,ident,x0,y0,x1,y1,width,z0,z1,material='timber_dark',position=(0,0,0),side='front'):
        length=math.hypot(x1-x0,y1-y0);need(length>0 and 0<width<length,'Invalid brace')
        dx,dy=(x1-x0)/length,(y1-y0)/length;nx,ny=-dy*width/2,dx*width/2
        poly=[(x0+nx,y0+ny),(x1+nx,y1+ny),(x1-nx,y1-ny),(x0-nx,y0-ny)]
        c=self.component(ident,'exposed_diagonal_support');self.paint(c,'brace',_extrusion(poly,z0,z1),material);self.instance(c,position=position,side=side)
        self.grain_axes.append({'component_id':ident,'operation_id':'brace','part_id':'solid','material':material,'role':'diagonal_support','grain_axis_component_local':[dx,dy,0]});return c

    def wall(self,ident,width,height,depth,position,side='front',material='plaster_light'):
        for v,n in [(width,'width'),(height,'height'),(depth,'depth')]:positive(v,n)
        c=self.component(ident,'measured_wall_panel');self.paint(c,'wall_body',_box((-width/2,0,-depth),(width/2,height,0)),material);self.instance(c,position=position,side=side);return c

    def window(self,wall,ident,width,height,center_x,bottom_y,wall_depth_m,style='thin_wood_casement',state='glazed_closed',side_clearance=None):
        """Cut and component use exactly the same pose; frame never changes a post."""
        wi=next(i for i in self.instances if i['component']==wall['id']);local={'translation':[center_x,bottom_y,0]}
        module=build_window_module(width,height,style,state,side_clearance,module_id=ident,wall_depth_m=wall_depth_m,wall_part_id='solid',materials=self.materials)
        cut=deepcopy(module['opening_cut']);cut['transform']=local;wall['operations'].append(cut)
        c=module['component'];need(not any(x['id']==ident for x in self.components),'Duplicate window ID');self.components.append(c)
        wt=core.compose(core.transform(wi.get('transform')),core.transform(local))
        self.instances.append({'id':ident,'component':ident,'transform':{'basis':wt['basis'],'translation':wt['translation']}})
        self.grain_axes.extend(module['grain_axes']);self.openings.append({'id':ident,'kind':'window','owner_wall':wall['id'],'state':state,'dimensions':module['dimensions'],'transform':self.instances[-1]['transform'],'api_provenance':module['provenance']})
        return module

    def open_doorway(self,wall,ident,width,height,center_x,bottom_y,wall_depth_m,deck_top_y,clearance_height_m=2.0):
        """Explicit open void reaching deck; no glass/window overlay substitutes for it."""
        width=positive(width,'width');height=positive(height,'height');need(height>=clearance_height_m,'Door below head clearance')
        wi=next(i for i in self.instances if i['component']==wall['id']);wt=core.transform(wi.get('transform'));world_bottom=core.apply(wt,[center_x,bottom_y,0])[1]
        need(abs(world_bottom-deck_top_y)<1e-8,'Balcony door must reach its actual deck')
        cut={'id':ident+'_passage','part':'solid','action':'cut','shape':_box((center_x-width/2,bottom_y,-wall_depth_m-.025),(center_x+width/2,bottom_y+height,.025)),'selector':{'part':'solid'}}
        wall['operations'].append(cut)
        self.openings.append({'id':ident,'kind':'door','owner_wall':wall['id'],'state':'open_passage','aperture_m':[width,height],'deck_top_y':deck_top_y,'bottom_world_y':world_bottom,'source_cut_id':cut['id']})
        return cut

    def extruded_unit(self,ident,profile,z_min,z_max,family,slots,position=(0,0,0),side='front',grain=None):
        need(family in ('tile','brick','plank'),'Physical material family required')
        material=unit_material(ident,family,slots,self.seed);need(material in self.materials,'Unknown unit material')
        c=self.component(ident,'individual_'+family);self.paint(c,ident,_extrusion(profile,z_min,z_max),material);self.instance(c,position=position,side=side)
        self.units.append({'unit_id':ident,'component_id':ident,'role':family,'material':material})
        if grain is not None:self.grain_axes.append({'component_id':ident,'operation_id':ident,'part_id':'solid','material':material,'role':family,'grain_axis_component_local':list(grain)})
        return c

    def gallery_deck(self,ident,x_min,x_max,front_wall_z,outer_z,deck_top_y,deck_thickness,plank_intervals,slots=('timber',)):
        need(x_min<x_max and front_wall_z<outer_z,'Nonempty gallery domain required')
        positive(deck_thickness,'deck_thickness');need(plank_intervals,'Measured or explicitly inferred board subdivision required')
        need(abs(plank_intervals[0][0]-x_min)<1e-8 and abs(plank_intervals[-1][1]-x_max)<1e-8,'Deck boards must cover complete width')
        for k,(l,r) in enumerate(plank_intervals):
            need(l<r and (k==0 or abs(l-plank_intervals[k-1][1])<1e-8),'Board domains must cover deck without walking holes')
            self.plank(ident+'_board_'+str(k),[l,deck_top_y-deck_thickness,front_wall_z],[r,deck_top_y,outer_z],slots,grain=(0,0,1))
        return {'id':ident,'deck_top_y':deck_top_y,'depth_m':outer_z-front_wall_z,'bounds':{'min':[x_min,deck_top_y-deck_thickness,front_wall_z],'max':[x_max,deck_top_y,outer_z]}}

    def roof_gable(self,ident,width,z_min,z_max,eave_y,ridge_y):
        need(ridge_y>eave_y,'Ridge must exceed eave');pitch=math.degrees(math.atan2(ridge_y-eave_y,width/2))
        _roof_gable(self,ident,width,z_min,z_max,eave_y,pitch)
        return self.components[-1]

    def master(self):
        m={'schema':SCHEMA,'id':self.asset_id,'revision':1,'axes':{'up':'+Y','front':'+Z','right':'+X'},'grid_origin':[0,0,0],'materials':deepcopy(self.materials),'components':deepcopy(self.components),'instances':deepcopy(self.instances),'assembly_cuts':[],'constraints':[],
           'metadata':{'authoring_only':True,'physical_unit_palette_policy':'Stable SHA256 per named board/tile/brick; never a per-cell seed','openings':deepcopy(self.openings)},'provenance':{'ordinary_assembly_reused':True,'ordinary_r2_gable_reused':True,'new_sampling_engine':False,'measurement_review_pending':True}}
        core.validate_master(m,.05);return m
