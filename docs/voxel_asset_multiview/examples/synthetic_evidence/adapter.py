"""Tiny synthetic evidence fixture. No character quality/real-asset claim.

The only compiler and mesher used are the existing common modules. A 96px
orthographic box projector supplies small test PNGs, not production rendering.
"""
from __future__ import annotations
import copy
import hashlib
import json
from pathlib import Path
import struct
import sys
import zlib

REPO = Path(__file__).resolve().parents[3]
sys.dont_write_bytecode = True
sys.path.insert(0, str(REPO / 'voxel_character/common'))
from core import compile_master
from render_data import make_render_data


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path, value):
    path.write_text(json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False)+'\n')


def png(path, boxes, view, color):
    """Project exact axis-aligned solid source boxes; no source-image sampling."""
    width = height = 96
    pixels = bytearray([235,237,231] * width * height)
    for lo, hi in boxes:
        umin, umax = (lo[2],hi[2]) if view == 'side' else (lo[0],hi[0])
        if view == 'back':
            umin,umax = -umax,-umin
        # Fixed physical span 1.5 m, centre Y=.5 m, no model auto-fit.
        x0,x1 = [round(width/2 + value/1.5*height) for value in (umin,umax)]
        y0,y1 = [round(height/2-(value-.5)/1.5*height) for value in (hi[1],lo[1])]
        for y in range(max(0,y0),min(height,y1)):
            for x in range(max(0,x0),min(width,x1)):
                offset = (y*width+x)*3
                pixels[offset:offset+3] = bytes(color)
    def chunk(kind,data):
        return struct.pack('>I',len(data))+kind+data+struct.pack('>I',zlib.crc32(kind+data)&0xffffffff)
    raw = b''.join(b'\0'+pixels[y*width*3:(y+1)*width*3] for y in range(height))
    path.write_bytes(b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',width,height,8,2,0,0,0))+
                     chunk(b'IDAT',zlib.compress(raw))+chunk(b'IEND',b''))


def build(root):
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    artifacts = {}
    def artifact(key, kind, value=None, path=None):
        if path is None:
            path = root/(key+'.json')
            write_json(path,value)
        path = Path(path)
        # Tests use a temporary root with small copies of exact common sources.
        if not path.is_relative_to(root):
            copied = root/(key+path.suffix)
            copied.write_bytes(path.read_bytes())
            path = copied
        artifacts[key] = {'kind':kind,'path':str(path.relative_to(root)),'sha256':sha(path)}
        return key
    master = {'schema':'riverstone.voxel.master.v1','id':'synthetic_box_only','revision':1,
              'axes':{'right':'+X','up':'+Y','front':'+Z'},'materials':{'test':'829787'},
              'components':[{'id':'body','parts':[{'id':'solid','pivot':[0,0,0]}],
                'operations':[{'id':'solid','action':'paint','part':'solid','material':'test',
                               'shape':{'kind':'box','min':[-.25,0,-.125],'max':[.25,1,.125]}}]}],
              'instances':[{'id':'body','component':'body'}]}
    compiled = compile_master(master, {'pitch':.125})
    render = make_render_data(compiled)
    artifact('master','master',master)
    artifact('compiled','compiled',compiled)
    artifact('render_mesh','render_mesh',render)
    artifact('compiler','compiler_source',path=REPO/'voxel_character/common/core.py')
    artifact('exporter','exporter_source',path=REPO/'voxel_character/common/render_data.py')
    artifact('mesher','mesher_source',path=REPO/'voxel_character/tools/mesh.py')
    artifact('renderer','renderer_source',path=Path(__file__).resolve())
    artifact('adapter','adapter_source',path=Path(__file__).resolve())
    part = {'id':'body:solid','source_pointer':'/parts/0','representation':'section_loft',
            'max_station_step_m':.5,'sections':[{'station_m':y,'center_xz_m':[0,0], 'width_m':.5,'depth_m':.25} for y in (0,.5,1)]}
    artifact('source_volume','source_volume',{'schema':'synthetic.section_box.v1','parts':[part],
             'scope':'Test-only constant rectangular section loft; not a character.'})
    artifact('profile','volume_profile',{'schema':'riverstone.volume.profile.v1',
             'source_sha256':artifacts['source_volume']['sha256'],'parts':[part]})
    references, model_renders = [], []
    # Synthetic measured drawing: do not represent this as user-observed anatomy.
    source = root/'synthetic_measured_drawing.png'
    png(source,[([-.25,0,-.125],[.25,1,.125])],'front',(100,100,100))
    artifact('source_drawing','observed_reference',path=source)
    artifact('observation','observation_record',{'source_sha256':sha(source),
             'source_type':'measured_drawing','scope':'Synthetic test fixture authored from a known box, not a user reference.'})
    for index,(view,yaw) in enumerate({'front':0,'side':90,'back':180}.items()):
        ref = root/f'reference_{view}.png'
        png(ref,[([-.25,0,-.125],[.25,1,.125])],view,(70+index*10,80,90))
        rid = artifact('ref_'+view,'manual_reference',path=ref)
        gid = artifact('generation_'+view,'generation_record',{'output_sha256':sha(ref),
             'source_sha256':[sha(source)],'method':'manual_inference',
             'unobserved_surfaces':'Synthetic box dimensions determine these test views; no real hidden anatomy observed.'})
        calibration = {'schema':'riverstone.multiview.calibration.v1','reference_sha256':sha(ref),
             'view':view,'crop_px':[0,0,96,96],'projection':'orthographic_aligned',
             'yaw_deg':yaw,'pitch_deg':0,'roll_deg':0,'pixels_per_m':64,'footline_px':80,'crown_px':16,
             'unresolved_conflicts':[]}
        aid = artifact('alignment_'+view,'calibration',calibration)
        references.append({'view':view,'artifact':rid,'origin':'manual_inference','source_refs':['source_drawing'],
             'generation_record':gid,'alignment_record':aid,'crop_px':[0,0,96,96]})
        for stage in ('authored_volume','compiled_mesh'):
            image = root/f'{stage}_{view}.png'
            if stage == 'authored_volume':
                # Exact constant section volume preview.
                boxes = [([-.25,0,-.125],[.25,1,.125])]
                rgb = (130,142,155)
            else:
                boxes = [([min(p[i] for p in quad) for i in range(3)],
                          [max(p[i] for p in quad) for i in range(3)])
                         for group in render['groups'] for quad in group['quads']]
                rgb = (135,145,120)
            png(image,boxes,view,rgb)
            iid = artifact(f'image_{stage}_{view}','model_render',path=image)
            input_id = 'source_volume' if stage == 'authored_volume' else 'render_mesh'
            record = {'schema':'riverstone.multiview.render_record.v1','subject':stage,'view':view,
                'input_sha256':artifacts[input_id]['sha256'],'image_sha256':sha(image),
                'renderer_source_sha256':artifacts['renderer']['sha256'],'actual_geometry_render':True,
                'command':'fixture_factory.build: exact box sections or actual common render quad projection; test only',
                'camera':{'projection':'orthographic','frame_id':'fixture_frame','yaw_deg':yaw,'pitch_deg':0,'roll_deg':0,
                          'vertical_span_m':1.5,'resolution_px':[96,96],'target_m':[0,.5,0],
                          'scale_source':'locked_reference_frame'}}
            eid = artifact(f'record_{stage}_{view}','render_record',record)
            model_renders.append({'stage':stage,'view':view,'image':iid,'record':eid,'renderer_source':'renderer'})
    artifact('source_review','precompile_review',{'schema':'riverstone.multiview.precompile_review.v1',
        'fixture_only':True,'reviewer':'SYNTHETIC_UNIT_TEST_RECORD_NOT_A_HUMAN_REVIEW',
        'source_sha256':artifacts['source_volume']['sha256'],'profile_sha256':artifacts['profile']['sha256'],
        'reviewed_image_sha256':[artifacts[r['image']]['sha256'] for r in model_renders if r['stage']=='authored_volume'],
        'decision':'ready_for_voxelization','basis':'direct_multiview_image_review',
        'findings':['Synthetic fixture record checks dependency validation; it does not claim a person reviewed an asset.']})
    artifact('lowering','lowering_record',{'schema':'riverstone.multiview.common_lowering.v1',
        'source_sha256':artifacts['source_volume']['sha256'],'master_sha256':artifacts['master']['sha256'],
        'precompile_review_sha256':artifacts['source_review']['sha256'],'adapter_source_sha256':artifacts['adapter']['sha256'],
        'command':'fixture_factory.build: constant rectangular section box lowers to common box; synthetic test only'})
    contract = {'schema':'riverstone.asset.multiview_contract.v1','asset_id':'synthetic_box_fixture_NOT_a_character',
        'asset_class':'complex_character','fixture_only':True,
        'frame':{'id':'fixture_frame','unit':'m','right':'+X','up':'+Y','front':'+Z','handedness':'right',
                 'foot_y_m':0,'asset_height_m':1},'artifacts':artifacts,'references':references,
        'volume':{'authoring_method':'section_loft','source_artifact':'source_volume','profile_artifact':'profile',
                  'continuity_disposition':{},'precompile_review':'source_review'},
        'common':{'master':'master','compiled':'compiled','render_mesh':'render_mesh','compiler_source':'compiler',
                  'exporter_source':'exporter','mesher_source':'mesher','adapter_source':'adapter',
                  'lowering_record':'lowering'},'model_renders':model_renders,
        'visual_review':{'status':'pending'},'claims':{'asset_complete':False,'coverage_pass':False}}
    return contract
