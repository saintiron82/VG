"""Cheap review masses for the registered plan; not common-source geometry."""
from pathlib import Path
import json
import math
from build_audit import HERE,write,ref


def main():
    p=json.loads((HERE/'adaptation_plan.json').read_text());groups=[]
    for g in p['groups']:
        out={'id':g['id'].replace('_registered',''),'source_group_key':g['id'],
             'world_anchor_xyz_m':g['world_origin_xyz_m'],
             'image_anchor_world_xyz_m':g['registered_district_anchor_xyz_m'],
             'registration_anchor_id':g['image_anchor_id'],'masses':[],
             'replaces_source_building_ids':[],
             'status':'registered_image_shape_proxy_only; source and cache integration pending',
             'open_space_policy':'Only named bodies and roof layers. Courts, gardens and portals remain empty.',
             'access_local_polyline_xz_m':g['access_local_polyline_xz_m'],
             'frame_contract':'Mass centers already rotated around the group origin; yaw rotates each box about its own center. Do not rotate group again.'}
        a=math.radians(g['yaw_degrees']);c,s=math.cos(a),math.sin(a)
        def box(key,rect,y0,y1,role,color,source_module):
            x0,z0,x1,z1=rect;x,z=(x0+x1)/2,(z0+z1)/2
            out['masses'].append({'id':key,'source_module':source_module,'semantic_role':role,
              'position_local_xyz_m':[c*x+s*z,(y0+y1)/2,-s*x+c*z],
              'size_xyz_m':[x1-x0,y1-y0,z1-z0],'yaw_degrees':g['yaw_degrees'],
              'proxy_shape':'box_envelope','color_role':color,'actual_common_geometry':False})
        def roof(key,rect,eave,ridge,axis,color,source_module,spire=False):
            x0,z0,x1,z1=rect;cx,cz=(x0+x1)/2,(z0+z1)/2;n=8 if spire else 4
            for i in range(n):
                # Envelopes contain each sloped band; this is a review approximation.
                f=1-i/n;rx=(x1-x0)/2*(f if spire or axis=='Z' else 1);rz=(z1-z0)/2*(f if spire or axis=='X' else 1)
                box(f'{key}_band_{i}',[cx-rx,cz-rz,cx+rx,cz+rz],eave+(ridge-eave)*i/n,eave+(ridge-eave)*(i+1)/n,
                    'stepped_spire_envelope' if spire else 'stepped_gable_envelope',color,source_module)
        for m in g['modules']:
            b=m['local_bounds_m'];x0,y0,z0=b['min'];x1,h,z1=b['max'];rect=[x0,z0,x1,z1];key=m['id'];role=m['semantic_role'];color=m.get('roof','slate_gray')
            if role=='bell_tower' or role=='hip_roof_tower':
                top=m['body_top_m'];box(key+'_body',rect,0,top,'tower_body','warm_stone',key)
                roof(key+'_spire',rect,top,h,'Z',color,key,True)
            elif role=='church_body':
                # Distinct lower aisles, central clerestory and transverse arm.
                w=x1-x0;d=z1-z0;cx=(x0+x1)/2;ew=w*.235
                e=m['nave_eave_m'];ar=m.get('aisle_ridge_m',h*.48);ae=m.get('aisle_eave_m',h*.36)
                body=[cx-ew,z0,cx+ew,z1];box(key+'_nave_body',body,0,e,'nave_body','warm_stone',key);roof(key+'_nave_roof',body,e,h,'Z',color,key)
                for side,rec in [('west',[x0,z0+d*.08,cx-ew,z1-d*.1]),('east',[cx+ew,z0+d*.08,x1,z1-d*.1])]:
                    box(key+'_'+side+'_aisle',rec,0,ae,'low_aisle','warm_stone',key);roof(key+'_'+side+'_aisle_roof',rec,ae,ar,'Z',color,key)
                rec=[x0,z0+d*.30,x1,z0+d*.48];te=h*.51;tr=h*.70
                box(key+'_transept',rec,0,te,'transept_body','warm_stone',key);roof(key+'_transept_roof',rec,te,tr,'X',color,key)
            elif role=='gate_wing':
                e=17;cx=m['opening_local_xz_m'][0];half=m['clear_width_m']/2;ch=m['clear_height_m']
                box(key+'_left',[x0,z0,cx-half,z1],0,e,'gate_wing','warm_stone',key);box(key+'_right',[cx+half,z0,x1,z1],0,e,'gate_wing','warm_stone',key)
                box(key+'_header',[cx-half,z0,cx+half,z1],ch,e,'overhead_gate_header','warm_stone',key);roof(key+'_roof',rect,e,h,'X',color,key)
            elif role=='covered_arcade':
                # Open walking volume is explicit: sparse piers and overhead roof.
                along_x=(x1-x0)>(z1-z0);length=(x1-x0) if along_x else (z1-z0);n=max(2,round(length/4))
                for i in range(n+1):
                    x=x0+(x1-x0)*i/n if along_x else (x0+x1)/2;z=(z0+z1)/2 if along_x else z0+(z1-z0)*i/n
                    box(f'{key}_pier_{i}',[x-.4,z-.4,x+.4,z+.4],0,h*.55,'arcade_pier','warm_stone',key)
                roof(key+'_roof',rect,h*.55,h,'X' if along_x else 'Z',color,key)
            else:
                e=m.get('eave_m',h*.68);box(key+'_body',rect,0,e,role,'warm_stone',key)
                roof(key+'_roof',rect,e,h,'X' if x1-x0>z1-z0 else 'Z',color,key)
        groups.append(out)
    result={'schema':'riverstone.city.landmark_proxy_masses.v1','status':'registered_review_proxy_no_scene_changes',
            'source':ref(HERE/'adaptation_plan.json'),'replace_registered_group_ids':[g['id'] for g in groups],
            'apply_policy':'Parent/source owner may substitute these groups in a review overlay. This file does not edit plan.json or certify placed common geometry.',
            'masses_are':'Bodies plus explicit stepped roof/spire envelope bands. Warm stone body and approved roof role colors are distinct. No full-height church or precinct box.',
            'groups':groups,'no_compile':True,'no_scene_edit':True}
    write(HERE/'proxy_masses.json',result)
    print(json.dumps({'groups':len(groups),'masses':{g['id']:len(g['masses']) for g in groups}}))


if __name__=='__main__':main()
