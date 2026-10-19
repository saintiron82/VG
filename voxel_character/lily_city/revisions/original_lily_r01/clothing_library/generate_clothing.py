#!/usr/bin/env python3
"""Deterministic, source-only medieval clothing authoring. No shared cache writes.
Coordinates are the original adult bind frame; body-frame transforms happen at assembly.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
ADULT = ['adult_female', 'adult_male']
CHILD = ['child']
ALL = ADULT + CHILD
PIVOTS = {'pelvis':[0,.94,0], 'torso':[0,1.05,0],
    'skirt_left':[-.1,.99,0], 'skirt_right':[.1,.99,0], 'cape':[0,1.32,-.13]}
for side, sign in [('left',-1),('right',1)]:
    for bone,y in [('upper_arm',1.32),('forearm',1.11)]: PIVOTS[f'{bone}_{side}']=[sign*.27,y,0]
    for bone,y in [('thigh',.92),('shin',.52),('foot',.12)]: PIVOTS[f'{bone}_{side}']=[sign*.105,y,0]
MATERIALS = ['teal_wool','teal_light','teal_shadow','linen','linen_shadow','brass','leather','leather_light','leather_dark','sole']
PALETTE = {'primary':['teal_wool','teal_light','teal_shadow'], 'secondary':['linen','linen_shadow'], 'trim':['brass'], 'leather':['leather','leather_light','leather_dark'], 'sole':['sole']}


def clean(value):
    if isinstance(value,float): return round(value,6)
    if isinstance(value,list): return [clean(v) for v in value]
    if isinstance(value,dict): return {k:clean(v) for k,v in value.items()}
    return value

def box(ops, ident, part, mat, lo, hi):
    ops.append(clean({'id':ident,'part':part,'action':'paint','material':mat,'shape':{'kind':'box','min':lo,'max':hi,'minimum_cells':[1,1,1]}}))

def ext(ops, ident, part, mat, poly, zlo, zhi):
    ops.append(clean({'id':ident,'part':part,'action':'paint','material':mat,'shape':{'kind':'extrusion','polygon':poly,'z_min':zlo,'z_max':zhi,'minimum_cells':1}}))

def module(ident, frames, slots, tags, ops, notes, **kwargs):
    # Prefix operation IDs so independent modules can be safely concatenated.
    for op in ops: op['id'] = ident+'__'+op['id']
    used = sorted({op['part'] for op in ops})
    return {'schema':'riverstone.clothing.module.v1','id':ident,'allowed_age_frames':frames,
        'presentation_tags':tags,'slots':slots,'coordinate_space':'original_adult_bind_m',
        'frame_transform_required':True, 'palette_channels':PALETTE,
        'ops':ops, 'attachment_parts':[{'id':p,'parent':('pelvis' if p.startswith('skirt_') else 'torso'),
            'pivot':PIVOTS[p],'role':'cloth','max_swing_degrees':5} for p in used if p.startswith('skirt_') or p=='cape'],
        'fit_notes':notes, 'rear_geometry_provenance':'New interpretation: rear panels, seams and unseen closures are authored for a complete turntable; they are not claimed to be recovered reference detail.', **kwargs}


def bodice(ops, mode='fitted', mat='teal_wool', hem=1.0, depth=.145):
    if mode=='fitted': poly=[[-.16,hem],[.16,hem],[.181,1.16],[.205,1.29],[.18,1.365],[.085,1.39],[-.085,1.39],[-.18,1.365],[-.205,1.29],[-.181,1.16]]
    elif mode=='blouse': poly=[[-.185,hem],[.185,hem],[.205,1.16],[.22,1.30],[.18,1.365],[.08,1.39],[-.08,1.39],[-.18,1.365],[-.22,1.30],[-.205,1.16]]
    elif mode=='child': poly=[[-.194,hem],[.194,hem],[.205,1.30],[.18,1.365],[.085,1.39],[-.085,1.39],[-.18,1.365],[-.205,1.30]]
    else: poly=[[-.205,hem],[.205,hem],[.22,1.22],[.23,1.31],[.19,1.365],[.085,1.39],[-.085,1.39],[-.19,1.365],[-.23,1.31],[-.22,1.22]]
    ext(ops,'front_bodice','torso',mat,poly,depth-.025,depth+.025)
    ext(ops,'rear_bodice','torso',mat,poly,-depth-.025,-depth+.005)
    # Side surfaces give a readable volume without replacing the underlying body.
    for side,sign in [('left',-1),('right',1)]:
        edge=[[-.205,hem],[-.175,hem],[-.185,1.30],[-.22,1.30]] if mode=='blouse' else [[-.19,hem],[-.16,hem],[-.18,1.31],[-.215,1.31]]
        if mode=='straight': edge=[[-.215,hem],[-.188,hem],[-.205,1.31],[-.235,1.31]]
        if mode=='child': edge=[[-.202,hem],[-.175,hem],[-.18,1.31],[-.212,1.31]]
        if sign==1: edge=[[-x,y] for x,y in reversed(edge)]
        ext(ops,'side_bodice_'+side,'torso',mat,edge,-depth,depth)
    # A two-piece open collar leaves a real neckline.
    for side,sign in [('left',-1),('right',1)]:
        poly=[[-.15,1.355],[-.055,1.325],[-.035,1.37],[-.075,1.405],[-.15,1.385]]
        if sign==1: poly=[[-x,y] for x,y in reversed(poly)]
        ext(ops,'collar_'+side,'torso','linen',poly,depth+.025,depth+.05)
    box(ops,'rear_center_seam','torso','teal_shadow' if mat=='teal_wool' else 'linen_shadow',[-.012,hem,-depth-.04],[.012,1.34,-depth-.025])



def pelvis_cover(ops, prefix, mat, top=1.065):
    """Thin opaque hip/seat shell; the two moving thighs remain independent.

    The original skin pelvis reaches y=.85, below the former yoke at y=.925.
    Stop at y=.825 rather than extending a rigid center slab down the legs.
    """
    box(ops,prefix+'_pelvis_front','pelvis',mat,[-.19,.825,.115],[.19,top,.145])
    box(ops,prefix+'_pelvis_rear','pelvis',mat,[-.19,.825,-.145],[.19,top,-.115])
    box(ops,prefix+'_pelvis_left','pelvis',mat,[-.19,.825,-.115],[-.162,top,.115])
    box(ops,prefix+'_pelvis_right','pelvis',mat,[.162,.825,-.115],[.19,top,.115])

def split_skirt(ops, hem=.22, waist=.995, top=.19, bottom=.32, mat='teal_wool', depth=.19, prefix='skirt', pleats=True, depth_profile=None):
    if not depth_profile:
        # Preserve all existing short/child garments exactly; only explicitly
        # selected long adult garments use the new stride-clearance profile.
        pelvis_cover(ops,prefix+'_underlap',mat,max(waist+.025,1.065))
        for side,sign in [('left',-1),('right',1)]:
            poly=[[-bottom,hem],[-.015,hem],[-.014,waist],[-top,waist]]
            outer=[[-bottom,hem],[-bottom+.025,hem],[-top+.025,waist],[-top,waist]]
            if sign==1:
                poly=[[-x,y] for x,y in reversed(poly)];outer=[[-x,y] for x,y in reversed(outer)]
            p='skirt_'+side
            ext(ops,prefix+'_front_'+side,p,mat,poly,depth-.018,depth+.018)
            ext(ops,prefix+'_rear_'+side,p,mat,poly,-depth-.018,-depth+.018)
            ext(ops,prefix+'_outer_return_'+side,p,mat,outer,-depth+.018,depth-.018)
            hem_poly=[[-bottom,hem],[-.015,hem],[-.015,hem+.035],[-bottom+.008,hem+.035]]
            if sign==1: hem_poly=[[-x,y] for x,y in reversed(hem_poly)]
            ext(ops,prefix+'_front_hem_'+side,p,'teal_light' if mat=='teal_wool' else 'linen_shadow',hem_poly,depth+.018,depth+.038)
            ext(ops,prefix+'_rear_hem_'+side,p,'teal_shadow' if mat=='teal_wool' else 'linen_shadow',hem_poly,-depth-.035,-depth-.018)
            if pleats:
                x0=sign*(bottom*.60);x1=sign*(top*.65)
                poly=[[x0-.012,hem+.05],[x0+.012,hem+.05],[x1+.012,waist-.03],[x1-.012,waist-.03]]
                ext(ops,prefix+'_raised_pleat_'+side,p,'teal_light' if mat=='teal_wool' else 'linen_shadow',poly,depth+.018,depth+.036)
        return
    # Piecewise front/rear flare stays hollow. XY bands approximate a depth-varying
    # surface using the agreed constant-Z extrusion schema, without engine edits.
    pelvis_cover(ops,prefix+'_underlap',mat,max(waist+.025,1.065))
    def depth_at(y):
        if not depth_profile: return depth
        for (y0,z0),(y1,z1) in zip(depth_profile,depth_profile[1:]):
            if y0<=y<=y1: return z0+(z1-z0)*(y-y0)/(y1-y0)
        return depth_profile[0][1] if y<depth_profile[0][0] else depth_profile[-1][1]
    def width_at(y): return bottom+(top-bottom)*(y-hem)/(waist-hem)
    count=max(1,int((waist-hem)/.035)+1) if depth_profile else 1
    for side,sign in [('left',-1),('right',1)]:
        p='skirt_'+side
        for band in range(count):
            y0=hem+(waist-hem)*band/count;y1=hem+(waist-hem)*(band+1)/count
            w0=width_at(y0);w1=width_at(y1);d=depth_at((y0+y1)/2)
            poly=[[-w0,y0],[-.015,y0],[-.014,y1],[-w1,y1]]
            outer=[[-w0,y0],[-w0+.025,y0],[-w1+.025,y1],[-w1,y1]]
            if sign==1:
                poly=[[-x,y] for x,y in reversed(poly)];outer=[[-x,y] for x,y in reversed(outer)]
            tag=f'_{side}_band_{band:02d}' if depth_profile else '_'+side
            ext(ops,prefix+'_front'+tag,p,mat,poly,d-.018,d+.018)
            ext(ops,prefix+'_rear'+tag,p,mat,poly,-d-.018,-d+.018)
            ext(ops,prefix+'_outer_return'+tag,p,mat,outer,-d+.018,d-.018)
            if pleats and y1>hem+.05 and y0<waist-.03:
                py0=max(y0,hem+.05);py1=min(y1,waist-.03)
                x0=sign*width_at(py0)*.62;x1=sign*width_at(py1)*.62
                pp=[[x0-.012,py0],[x0+.012,py0],[x1+.012,py1],[x1-.012,py1]]
                ext(ops,prefix+'_raised_pleat'+tag,p,'teal_light' if mat=='teal_wool' else 'linen_shadow',pp,d+.018,d+.036)
        d=depth_at(hem+.0175)
        hem_poly=[[-bottom,hem],[-.015,hem],[-.015,hem+.035],[-width_at(hem+.035),hem+.035]]
        if sign==1: hem_poly=[[-x,y] for x,y in reversed(hem_poly)]
        ext(ops,prefix+'_front_hem_'+side,p,'teal_light' if mat=='teal_wool' else 'linen_shadow',hem_poly,d+.018,d+.038)
        ext(ops,prefix+'_rear_hem_'+side,p,'teal_shadow' if mat=='teal_wool' else 'linen_shadow',hem_poly,-d-.035,-d-.018)


def open_vest(ops, coat=False):
    low=.95 if not coat else .98
    width=.212 if not coat else .232
    for side,sign in [('left',-1),('right',1)]:
        poly=[[-width,low],[-.045,low],[-.028,1.18],[-.08,1.37],[-.17,1.385],[-width,1.29]]
        lapel=[[-.065,1.08],[-.025,1.20],[-.08,1.39],[-.14,1.365]]
        if sign==1:
            poly=[[-x,y] for x,y in reversed(poly)];lapel=[[-x,y] for x,y in reversed(lapel)]
        ext(ops,'open_front_'+side,'torso','teal_wool',poly,.166,.205)
        if coat: ext(ops,'folded_lapel_'+side,'torso','linen_shadow',lapel,.205,.236)
        x=sign*.16
        box(ops,'pocket_'+side,'torso','leather', [x-.045,1.03,.205],[x+.045,1.12,.23])
        # Narrow shoulder bridge makes this recognizably sleeveless without arm fill.
        xa,xb=sorted([sign*.16,sign*.225])
        box(ops,'shoulder_bridge_'+side,'torso','teal_wool',[xa,1.33,-.17],[xb,1.37,.17])
    ext(ops,'rear_vest','torso','teal_wool',[[-width,low],[width,low],[width,1.29],[.17,1.37],[-.17,1.37],[-width,1.29]],-.19,-.15)
    box(ops,'back_seam','torso','teal_shadow',[-.012,low,-.21],[.012,1.35,-.19])
    if coat: split_skirt(ops,.43,.99,.22,.275,'teal_wool',.217,'coat_tail',False,depth_profile=[(.43,.29),(.50,.29),(.99,.20)])


def trousers(ops, child=False, mat='teal_shadow'):
    pelvis_cover(ops,'trouser_seat',mat)
    for side,sign in [('left',-1),('right',1)]:
        x=sign*.105
        # Thigh and shin remain different attachment surfaces at the original knee pivot.
        topw=.087 if child else .079;low=.24 if child else .14
        box(ops,'trouser_thigh_'+side,'thigh_'+side,mat,[x-topw,.525,-.108],[x+topw,.965,.108])
        box(ops,'trouser_shin_'+side,'shin_'+side,mat,[x-.072,low,-.092],[x+.072,.525,.095])
        box(ops,'trouser_cuff_'+side,'shin_'+side,'linen_shadow' if child else 'leather_dark',[x-.078,low,-.101],[x+.078,low+.055,.106])
        box(ops,'outer_leg_seam_'+side,'thigh_'+side,'teal_light',[x+sign*(topw-.012)-.009,.55,.108],[x+sign*(topw-.012)+.009,.91,.124])
    # A small hip yoke, not a solid panel extending down over the legs.
    box(ops,'trouser_hip_yoke','pelvis',mat,[-.183,.925,-.116],[.183,1.01,.12])


def first_modules():
    result=[]
    ops=[];bodice(ops);split_skirt(ops,depth_profile=[(.22,.32),(.45,.32),(.70,.25),(.995,.17)])
    for y in [1.12,1.19,1.26]: box(ops,f'bodice_lacing_{y}','torso','brass',[-.035,y,.173],[.035,y+.02,.193])
    result.append(module('female_dress',['adult_female'],['top','bottom'],['dress','long_a_line','fitted_bodice'],ops,['Long flared front, back and side shells use two independent skirt parts.','Add sleeves, belt and shoes independently; no leg geometry is included.']))
    ops=[];bodice(ops,'blouse','linen',.98,.15)
    box(ops,'gathered_hem','torso','linen_shadow',[-.19,.98,.15],[.19,1.025,.183])
    result.append(module('female_blouse',['adult_female'],['top'],['blouse','loose_waist','open_collar'],ops,['A gathered loose blouse, compatible with skirt or work trousers.']))
    ops=[];split_skirt(ops,.31,1.025,.2,.305,depth_profile=[(.31,.32),(.45,.32),(.70,.23),(1.025,.17)])
    box(ops,'raised_waistband','pelvis','teal_shadow',[-.205,.99,-.16],[.205,1.04,.165])
    result.append(module('female_skirt',['adult_female'],['bottom'],['skirt','mid_calf','gored'],ops,['Independent mid-calf skirt has a real flared outline and hollow interior.']))
    ops=[];bodice(ops,'straight',hem=.98);split_skirt(ops,.72,.99,.207,.235,depth=.175,prefix='tunic_split',pleats=False)
    box(ops,'neck_slit','torso','teal_shadow',[-.018,1.265,.17],[.018,1.365,.193])
    result.append(module('male_tunic',['adult_male'],['top'],['tunic','straight','split_hip_hem'],ops,['Straight cut and thigh-length split hem; add trousers and sleeve option.']))
    ops=[];open_vest(ops)
    result.append(module('male_vest',['adult_male'],['outer'],['vest','sleeveless','open_front'],ops,['Open front, shoulder bridges and no arm operations create an actual sleeveless vest.'],requires_slots=['top']))
    ops=[];bodice(ops,'child',hem=1.035);split_skirt(ops,.815,1.04,.20,.22,depth=.178,prefix='child_tunic_tail',pleats=False)
    box(ops,'single_wooden_clasp','torso','leather_light',[-.025,1.29,.195],[.025,1.33,.22])
    result.append(module('child_tunic',CHILD,['top'],['child_tunic','loose_straight','short_hem','simple_closure'],ops,['Purpose-authored child pattern with high waist, short hem and straight loose chest.','Use a child frame transform, not a uniform miniature adult.']))
    return result



def sleeves(kind, child=False):
    ops=[]
    if kind=='none': return ops
    for side,sign in [('left',-1),('right',1)]:
        x=sign*.27
        width=.079 if not child else .084
        mat='teal_wool' if kind=='coat' else 'linen'
        if kind=='puffed':
            poly=[[x-.105,1.185],[x+.105,1.185],[x+.115,1.27],[x+.088,1.35],[x-.088,1.35],[x-.115,1.27]]
            ext(ops,'puff_'+side,'upper_arm_'+side,mat,poly,-.104,.108)
            box(ops,'puff_band_'+side,'upper_arm_'+side,'linen_shadow',[x-.097,1.175,-.11],[x+.097,1.21,.115])
        else:
            low=1.20 if kind=='short' else 1.115
            box(ops,'upper_sleeve_'+side,'upper_arm_'+side,mat,[x-width,low,-.098],[x+width,1.35,.098])
            if kind=='short': box(ops,'short_hem_'+side,'upper_arm_'+side,'linen_shadow',[x-width-.006,low,-.105],[x+width+.006,low+.035,.106])
        if kind in ['long','rolled','coat']:
            low=1.01 if kind=='rolled' else .895
            w=.075 if kind!='coat' else .089
            box(ops,'lower_sleeve_'+side,'forearm_'+side,mat,[x-w,low,-.092],[x+w,1.105,.094])
            box(ops,'cuff_'+side,'forearm_'+side,'linen_shadow' if kind!='coat' else 'teal_shadow',[x-w-.012,low-.006,-.106],[x+w+.012,low+.045,.108])
            if kind=='rolled': box(ops,'rolled_second_fold_'+side,'forearm_'+side,'linen',[x-w-.016,low+.018,-.112],[x+w+.016,low+.042,.114])
        if child:
            box(ops,'simple_sleeve_tab_'+side,'upper_arm_'+side,'linen_shadow',[x-.025,1.235,.099],[x+.025,1.27,.116])
    return ops


def apron(kind, child=False):
    ops=[]
    if kind=='none': return ops
    material='leather' if kind=='leather' else 'linen'
    hem=.55 if kind!='leather' else .62
    waist=1.04 if child else 1.0
    width=.21 if not child else .19
    for side,sign in [('left',-1),('right',1)]:
        # The apron is also split into two independent rigid cloth pieces.
        poly=[[-width,hem],[-.012,hem],[-.012,waist],[-.16,waist]]
        if sign==1: poly=[[-x,y] for x,y in reversed(poly)]
        ext(ops,'apron_leaf_'+side,'skirt_'+side,material,poly,.235,.268)
        xa,xb=sorted([sign*.05,sign*.15])
        box(ops,'apron_pocket_'+side,'skirt_'+side,'leather_dark' if kind=='leather' else 'linen_shadow',[xa,hem+.09,.268],[xb,hem+.18,.291])
    if kind in ['bib','leather','pinafore']:
        ext(ops,'bib_panel','torso',material,[[-.13,1.02],[.13,1.02],[.12,1.285],[-.12,1.285]],.198,.229)
        for side,sign in [('left',-1),('right',1)]:
            xa,xb=sorted([sign*.095,sign*.13])
            box(ops,'shoulder_strap_front_'+side,'torso',material,[xa,1.25,.182],[xb,1.365,.218])
            box(ops,'shoulder_strap_top_'+side,'torso',material,[xa,1.35,-.179],[xb,1.38,.198])
            box(ops,'shoulder_strap_back_'+side,'torso',material,[xa,1.045,-.196],[xb,1.365,-.167])
    box(ops,'waist_tie_front','pelvis',material,[-.208,waist-.015,.198],[.208,waist+.025,.237])
    box(ops,'waist_tie_back','pelvis',material,[-.208,waist-.015,-.203],[.208,waist+.025,-.17])
    box(ops,'rear_knot','pelvis','leather_dark' if kind=='leather' else 'linen_shadow',[-.04,waist-.035,-.233],[.04,waist+.035,-.203])
    return ops


def belt(kind, child=False):
    ops=[]
    if kind=='none': return ops
    y=1.05 if child else 1.01
    height=.034 if kind in ['narrow','rope'] else .075
    mat='linen_shadow' if kind=='rope' else ('teal_light' if kind=='sash' else 'leather_dark')
    # Four thin surfaces, not a full solid box painted through the torso.
    box(ops,'belt_front','pelvis',mat,[-.223,y-height/2,.169],[.223,y+height/2,.208])
    box(ops,'belt_back','pelvis',mat,[-.223,y-height/2,-.198],[.223,y+height/2,-.162])
    for side,sign in [('left',-1),('right',1)]:
        xa,xb=sorted([sign*.193,sign*.223])
        box(ops,'belt_side_'+side,'pelvis',mat,[xa,y-height/2,-.17],[xb,y+height/2,.18])
    if kind in ['narrow','wide']:
        box(ops,'buckle_outer','pelvis','brass',[-.042,y-.031,.208],[.042,y+.031,.235])
        box(ops,'buckle_center','pelvis','leather_dark',[-.022,y-.013,.235],[.022,y+.013,.244])
        if kind=='wide':
            box(ops,'belt_tail','pelvis','leather', [.061,y-.13,.208],[.097,y-.005,.238])
    else:
        box(ops,'tie_knot','pelvis',mat,[.07,y-.025,.208],[.125,y+.025,.24])
        box(ops,'tie_tail','pelvis',mat,[.08,y-.14,.214],[.105,y-.01,.24])
    return ops


def shoes(kind, child=False):
    ops=[]
    for side,sign in [('left',-1),('right',1)]:
        x=sign*.105;w=.09 if not child else .085;toe=.205 if not child else .182
        box(ops,'shoe_body_'+side,'foot_'+side,'leather',[x-w,.033,-.095],[x+w,.137,.16])
        box(ops,'toe_cap_'+side,'foot_'+side,'leather_light',[x-w+.012,.035,.145],[x+w-.012,.095,toe])
        box(ops,'sole_'+side,'foot_'+side,'sole',[x-w-.006,0,-.101],[x+w+.006,.035,toe+.008])
        box(ops,'shoe_opening_'+side,'foot_'+side,'leather_dark',[x-w+.006,.135,-.082],[x+w-.006,.16,.102])
        if kind in ['ankle_boot','tall_boot']:
            height=.31 if kind=='ankle_boot' else .49
            box(ops,'boot_shaft_'+side,'shin_'+side,'leather',[x-w+.008,.145,-.092],[x+w-.008,height,.099])
            box(ops,'boot_cuff_'+side,'shin_'+side,'leather_light',[x-w-.002,height-.045,-.104],[x+w+.002,height,.112])
            box(ops,'boot_seam_'+side,'shin_'+side,'leather_dark',[x-.012,.17,.099],[x+.012,height-.045,.12])
        else:
            box(ops,'instep_strap_'+side,'foot_'+side,'leather_dark',[x-w+.008,.11,.065],[x+w-.008,.142,.092])
    return ops


def remaining_modules():
    result=[]
    ops=[];bodice(ops,'fitted',hem=1.0);trousers(ops)
    split_skirt(ops,.755,1.005,.19,.235,depth=.19,prefix='work_hip_panel',pleats=False)
    for side,sign in [('left',-1),('right',1)]:
        x=sign*.12
        box(ops,'reinforced_chest_'+side,'torso','leather',[x-.05,1.12,.173],[x+.05,1.285,.197])
    result.append(module('female_workwear',['adult_female'],['top','bottom'],['workwear','trousers','short_split_hip_panels','reinforced'],ops,['Fitted practical top, articulated trousers and short protective hip panels form a different silhouette from the dress.']))
    ops=[];trousers(ops)
    result.append(module('adult_trousers',ADULT,['bottom'],['trousers','separate_knees','straight_legs'],ops,['Thigh, shin and hip yoke attach separately. Shared with adult blouse, tunic and vest outfits.']))
    ops=[];bodice(ops,'straight','linen',.99,.15)
    result.append(module('male_shirt',['adult_male'],['top'],['shirt','straight_hem','open_collar'],ops,['Linen base layer for open vest or coat. Sleeves are independent.']))
    ops=[];open_vest(ops,coat=True)
    result.append(module('male_coat',['adult_male'],['outer'],['coat','folded_lapels','split_long_tails','layered'],ops,['Long open coat includes two skirt tail shells; lapels have physical thickness.','A shirt plus trousers and coat sleeves complete the outfit.'],requires_slots=['top','bottom'],requires_sleeve_options=['sleeves_coat']))
    ops=[];bodice(ops,'straight',hem=.99);trousers(ops)
    for side,sign in [('left',-1),('right',1)]:
        x=sign*.13
        box(ops,'work_chest_patch_'+side,'torso','leather',[x-.061,1.10,.173],[x+.061,1.245,.205])
        x=sign*.105
        box(ops,'knee_patch_'+side,'thigh_'+side,'leather_dark',[x-.06,.545,.109],[x+.06,.635,.134])
    result.append(module('male_workwear',['adult_male'],['top','bottom'],['workwear','square_torso','reinforced_trousers'],ops,['Square work shirt with real chest patches and joint-separated reinforced trousers.']))
    ops=[];bodice(ops,'child',hem=1.07);split_skirt(ops,.435,1.08,.20,.285,depth=.19,prefix='child_dress')
    box(ops,'high_waist_band','torso','linen_shadow',[-.201,1.055,.174],[.201,1.095,.201])
    result.append(module('child_dress',CHILD,['top','bottom'],['child_dress','high_waist','loose_bodice','short_a_line'],ops,['Separate age-appropriate high-waisted pattern; no shaped adult waist or adult bodice lacing.','Apply child-specific frame transform once.']))
    ops=[];trousers(ops,child=True)
    result.append(module('child_trousers',CHILD,['bottom'],['child_trousers','roomy_thighs','short_cuffed_legs'],ops,['Purpose-authored roomy short-cuffed trousers, separate thigh and shin parts; not an adult palette swap.']))
    ops=[];bodice(ops,'child','linen',1.035,.15)
    result.append(module('child_blouse',CHILD,['top'],['child_blouse','straight_loose','simple_collar'],ops,['Straight loose child top for trousers or pinafore layering.']))
    for kind in ['none','short','long','rolled','puffed','coat']:
        frames=ALL if kind=='none' else ADULT
        notes=['Attach upper and lower sleeves to their respective existing arm bones.','Replace the sleeve slot instead of stacking sleeve modules.']
        result.append(module('sleeves_'+kind,frames,['sleeves'],['sleeves',kind],sleeves(kind),notes,optional_empty=(kind=='none')))
    for kind in ['short','long']:
        result.append(module('child_sleeves_'+kind,CHILD,['sleeves'],['child_sleeves',kind,'roomy'],sleeves(kind,True),['Child sleeve pattern has its own roomier cut and simple sleeve tabs.']))
    for kind in ['none','waist','bib','leather']:
        result.append(module('apron_'+kind,ALL if kind=='none' else ADULT,['apron'],['apron',kind],apron(kind),['Front leaves are split across skirt_left/right; rear ties are new interpreted detail.'],optional_empty=(kind=='none')))
    result.append(module('child_apron_pinafore',CHILD,['apron'],['child_pinafore','high_waist','broad_bib'],apron('pinafore',True),['High-waist child pinafore with connected shoulder straps, split leaves and simple pockets.']))
    for kind in ['none','narrow','wide','rope']:
        result.append(module('belt_'+kind,ALL if kind=='none' else ADULT,['belt'],['belt',kind],belt(kind),['A separate four-surface belt follows the pelvis.'],optional_empty=(kind=='none')))
    result.append(module('child_belt_sash',CHILD,['belt'],['child_sash','soft_closure'],belt('sash',True),['Soft tie closure at the child high waist; no oversized adult buckle.']))
    for kind in ['low','ankle_boot','tall_boot']:
        result.append(module('shoes_'+kind,ADULT,['shoes'],['shoes',kind],shoes(kind),['Foot and shin boot sections remain separate across the ankle socket.']))
    result.append(module('child_shoes_soft',CHILD,['shoes'],['child_shoes','short_toe','low_soft_shoe'],shoes('low',True),['Shorter toe cap and simplified soft shoe detail authored for child proportions.']))
    return result


def write_catalog(modules):
    outfits=[
      {'id':'female_long_dress','age_frame':'adult_female','modules':['female_dress','sleeves_long','apron_none','belt_narrow','shoes_low']},
      {'id':'female_blouse_skirt','age_frame':'adult_female','modules':['female_blouse','female_skirt','sleeves_puffed','apron_bib','belt_rope','shoes_ankle_boot']},
      {'id':'female_workwear','age_frame':'adult_female','modules':['female_workwear','sleeves_rolled','apron_leather','belt_wide','shoes_tall_boot']},
      {'id':'male_tunic','age_frame':'adult_male','modules':['male_tunic','adult_trousers','sleeves_long','apron_none','belt_narrow','shoes_ankle_boot']},
      {'id':'male_vest','age_frame':'adult_male','modules':['male_shirt','adult_trousers','male_vest','sleeves_rolled','apron_none','belt_narrow','shoes_low']},
      {'id':'male_coat','age_frame':'adult_male','modules':['male_shirt','adult_trousers','male_coat','sleeves_coat','apron_none','belt_none','shoes_tall_boot']},
      {'id':'male_workwear','age_frame':'adult_male','modules':['male_workwear','sleeves_rolled','apron_leather','belt_wide','shoes_ankle_boot']},
      {'id':'child_tunic','age_frame':'child','modules':['child_tunic','child_trousers','child_sleeves_short','apron_none','child_belt_sash','child_shoes_soft']},
      {'id':'child_dress','age_frame':'child','modules':['child_dress','child_sleeves_long','child_apron_pinafore','belt_none','child_shoes_soft']},
      {'id':'child_trousers','age_frame':'child','modules':['child_blouse','child_trousers','child_sleeves_long','apron_none','child_belt_sash','child_shoes_soft']},
    ]
    registry={m['id']:m for m in modules}
    dump(ROOT/'catalog.json',{'schema':'riverstone.clothing.catalog.v1','revision':'original_lily_r01',
        'module_directory':'modules','module_count':len(modules),'modules':[{'id':m['id'],'path':'modules/'+m['id']+'.json','slots':m['slots'],'allowed_age_frames':m['allowed_age_frames'],'presentation_tags':m['presentation_tags'],'operation_count':len(m['ops'])} for m in modules],
        'example_outfits':outfits,'assembly_order':['bottom','top','outer','sleeves','apron','belt','shoes'],
        'palette_contract':{'channels':PALETTE,'rule':'Color variation must preserve silhouette modules. Remap material values by role after geometry composition; do not replace geometry with palette variants.'},
        'source_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()})
    dump(ROOT/'slot_options.json',{'schema':'riverstone.clothing.slots.v1',
        'slots':{slot:{'selection':'exactly_one' if slot in ['top','bottom','sleeves','apron','belt','shoes'] else 'zero_or_one','options':[m['id'] for m in modules if slot in m['slots']]} for slot in ['top','bottom','outer','sleeves','apron','belt','shoes']},
        'none_options':{'sleeves':'sleeves_none','apron':'apron_none','belt':'belt_none'},
        'selection_rule':'A multi-slot module satisfies all its listed slots once. All selected modules must allow the age frame. No duplicate occupied slot.',
        'safe_recommendation':'Use catalog.example_outfits as valid starting combinations; validate every user-edited combination.'})
    dump(ROOT/'validation_rules.json',{'schema':'riverstone.clothing.validation.v1',
        'allowed_age_frames':ALL,'allowed_parts':sorted(PIVOTS),'allowed_materials':MATERIALS,
        'required_module_fields':['id','allowed_age_frames','presentation_tags','ops','fit_notes'],
        'allowed_actions':['paint'],'allowed_shape_kinds':['box','extrusion'],
        'required_outfit_slots':['top','bottom','sleeves','apron','belt','shoes'],
        'max_modules_per_slot':1,'part_remap':{'skeletal':'costume_<original_bone_id>','parent_socket':'<original_bone_id>','retain_cloth_parts':['skirt_left','skirt_right','cape']},
        'canonical_reference':{'height_m':1.76,'torso_pivot_m':[0,1.05,0],'shoulder_pivot_x_m':[-.27,.27],'units':'m','up':'+Y','front':'+Z'},
        'child_frame_rule':'Child patterns are distinct source shapes and require the assembler child frame transform, applied exactly once. Do not uniformly scale a completed adult costume.',
        'minimum_front_rear_skirt_shell_inner_z_m':.15,'maximum_shell_depth_m':.05,
        'pelvis_coverage':{'required_for':['adult_trousers','child_trousers','female_dress','female_skirt','child_dress','female_workwear','male_workwear'],'canonical_skin_bottom_y_m':.85,'shell_bottom_y_m':.825,'shell_top_y_min_m':1.05,'front_inner_z_min_m':.105,'max_front_rear_depth_m':.035,'rule':'Opaque thin pelvis front, rear and side surfaces cover the existing skin hip without a thigh-length center slab.'},
        'skirt_outer_returns_rule':'At every Y cross section, outer returns stay outside the corresponding leg envelope; there is no center-spanning solid lower-body extrusion.',
        'stride_depth_profiles':{'female_dress':[[.22,.32],[.45,.32],[.70,.25],[.995,.17]],'female_skirt':[[.31,.32],[.45,.32],[.70,.23],[1.025,.17]],'male_coat':[[.43,.29],[.50,.29],[.99,.20]],'band_max_height_m':.035,'rule':'Segmented thin front/rear leaves and outer side returns only; no filled skirt interior. Final motion must be re-rendered; no gait or clip changes.'},
        'optional_apron_layer_fit':{'apply_only_when_selected_bottom_is_flared':True,'allowed_apron_modules':['apron_waist','apron_bib','apron_leather'],'apron_leaf_id_contains':'__apron_leaf_','apron_pocket_id_contains':'__apron_pocket_','base_leaf_z_m':[.235,.268],'base_pocket_z_m':[.268,.291],'leaf_offsets_from_selected_skirt_depth_m':[.045,.078],'pocket_offsets_from_selected_skirt_depth_m':[.078,.101],'band_max_height_m':.035,'preserve_parts':['skirt_left','skirt_right'],'do_not_transform':['bib_panel','shoulder_strap','waist_tie','rear_knot'],'rule':'Optional assembly-only fit: split lower apron leaves/pockets into height bands and offset each band against the selected skirt depth profile; leave upper bib/straps/ties and child aprons unchanged. No blanket Z offset or gait change.'},
        'skirt_rig':{'parts':['skirt_left','skirt_right'],'rigid':True,'max_swing_degrees':5,'preserve_original_clip_channels':True},
        'clashing_pairs':[['male_coat','male_tunic'],['male_coat','apron_bib'],['male_coat','apron_leather'],['male_coat','apron_waist']],
        'requirements':{m['id']:{key:m[key] for key in ['requires_slots','requires_sleeve_options'] if key in m} for m in modules if 'requires_slots' in m or 'requires_sleeve_options' in m},
        'prohibited_content':['npc_behavior','navigation','occupation_ai','skin_geometry','facial_features','hair_geometry'],
        'runtime_note':'Source validation is not a rendered collision proof. Final transformed rig, cell quantization and animation are validated by the assembler.'})
    dump(ROOT/'outfit_examples.json',{'schema':'riverstone.clothing.outfits.v1','outfits':outfits})

def dump(path,data):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(clean(data),ensure_ascii=False,indent=2)+'\n',encoding='utf-8')


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--early',action='store_true');args=parser.parse_args()
    modules=first_modules()
    if not args.early: modules += remaining_modules()
    for m in modules: dump(ROOT/'modules'/(m['id']+'.json'),m)
    if not args.early: write_catalog(modules)
    print(f'Wrote {len(modules)} source clothing modules under {ROOT / "modules"}')

if __name__=='__main__': main()
