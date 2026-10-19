"""Bind the parent's actual six-panel registration report before reconstruction.

Preserves the rejected original candidate. No warp, fiducial movement, or
inferred replacement image is performed here.
"""
import json
from pathlib import Path
from parts_v1 import need
from measurements_v1 import verify_ref,pixel_world


def validate_registration_binding(data,root):
    root=Path(root).resolve();template=json.loads(verify_ref(root,data['grid_template']).read_text());report=json.loads(verify_ref(root,data['registration_report']).read_text())
    need(template.get('schema')=='riverstone.six_view_grid_template.v1','Unknown grid template')
    need(report.get('schema')=='riverstone.six_view_registration.v1','Unknown registration report')
    need(report.get('registration_pass') is True and not report.get('errors'),'Actual six-view image registration failed')
    need(report.get('visible_fiducials')==template['tolerances']['required_visible_fiducials'],'Missing registration fiducials')
    need(report.get('max_error_px',float('inf'))<=template['tolerances']['fiducial_max_error_px'],'Registration exceeds exact approved tolerance')
    need(report.get('template_sha256')==template['template']['sha256'],'Registration template identity differs')
    need(set(data['views'])==set(template['views']),'View identity mismatch')
    for name,view in data['views'].items():
        need(view['image']['sha256']==report['image_sha256'],'View image differs from registered sheet')
        need(view['size_px']==template['canvas_px'],'View canvas differs')
        expected=template_affine(template,name)
        need(view['pixel_to_world_3x3']==expected,'No unregistered scale, warp, mirror or translation allowed')
    for row in data['measurements']:
        if row['provenance_kind']!='pixel_measurement':continue
        box=template['views'][row['view_id']]['grid_bounds_px']
        for p in row['pixel_endpoints']:need(box[0]<=p[0]<=box[2] and box[1]<=p[1]<=box[3],'Measurement crosses outside its own view panel')
    return {'registration_pass':True,'registered_image_sha256':report['image_sha256'],'template_bitmap_sha256':report['template_sha256'],'max_fiducial_error_px':report['max_error_px'],'internal_projection_review_still_required':True}


def template_affine(template,name):
    view=template['views'][name];x0,y0,x1,y1=view['grid_bounds_px'];w,h=view['span_m'];ppm=view['pixels_per_meter'];need(abs((x1-x0)/ppm-w)<1e-9 and abs((y1-y0)/ppm-h)<1e-9,'Template scale inconsistency')
    axes=view['projection_axes'];result=[[0.,0.,0.] for _ in range(3)]
    for dimension,spec in enumerate(axes):
        need(spec in ('+X','-X','+Y','-Y','+Z','-Z'),'Unsupported template axis');axis='XYZ'.index(spec[1]);sign=1 if spec[0]=='+' else -1
        if dimension==0:result[axis]=[sign/ppm,0.,sign*(-x0/ppm-w/2)]
        else:result[axis]=[0.,-sign/ppm,sign*(y1/ppm-(h/2 if name in ('top','bottom') else 0))]
    return result
