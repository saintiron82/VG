"""Strict image-measurement input gate; affine reprojection, no image invention.

Parent owns mask extraction and review. This adapter verifies its measured
numbers against exact image references before any production source is emitted.
"""
import hashlib, math
from pathlib import Path
from parts_v1 import need
VIEWS={'front','back','left','right','top','bottom'}


def finite(x):return type(x) in (int,float) and math.isfinite(x)
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def verify_ref(root,ref):
    need(isinstance(ref,dict) and isinstance(ref.get('path'),str),'Input file reference required')
    p=(root/ref['path']).resolve();need(p.is_relative_to(root.resolve()),'Reference escapes repository')
    need(p.is_file() and sha(p)==ref.get('sha256'),'Input reference hash mismatch: '+str(ref.get('path')))
    return p


def pixel_world(view,pixel):
    need(len(pixel)==2 and all(finite(v) for v in pixel),'Finite image point required')
    need(all(0<=pixel[j]<=view['size_px'][j] for j in range(2)),'Pixel point outside image')
    # Matrix columns map image +u/+v to canonical world axes. Translation is
    # explicit; image origin/perspective and an arbitrary 12m rescale are not inferred.
    m=view['pixel_to_world_3x3'];return [m[j][0]*pixel[0]+m[j][1]*pixel[1]+m[j][2] for j in range(3)]


def validate_measurements(data,repo_root,require_review=True):
    root=Path(repo_root).resolve();need(data.get('schema')=='riverstone.architecture.image_measurements.v1','Measurement adapter schema required')
    views=data.get('views',{});need(set(views)==VIEWS,'Exactly six named orthographic views required')
    refs=[]
    for ident,view in views.items():
        need(view.get('projection')=='orthographic','Perspective guide cannot be treated as orthographic measurements')
        image=verify_ref(root,view['image']);refs.append(view['image']);need(len(view['size_px'])==2 and all(type(n)is int and n>0 for n in view['size_px']),'Image dimensions required')
        # Standard-library header inspection is deliberately avoided: PNG/JPEG
        # dimensions are read using the installed Pillow decoder, never resampled.
        from PIL import Image
        with Image.open(image) as im:need(list(im.size)==view['size_px'],'Image dimensions mismatch')
        m=view.get('pixel_to_world_3x3');need(isinstance(m,list) and len(m)==3 and all(len(row)==3 and all(finite(x) for x in row) for row in m),'Finite pixel affine required')
        u=[r[0] for r in m];v=[r[1] for r in m];need(sum(x*x for x in u)>0 and sum(x*x for x in v)>0 and abs(sum(a*b for a,b in zip(u,v)))<1e-10,'Orthogonal nonzero image axes required')
        need(view.get('scale_basis') in ('shared_grid','planned_metric_anchor'),'Explicit shared scale required')
        need(view.get('mask_reference'),'Measured silhouette/opening mask file required');verify_ref(root,view['mask_reference']);refs.append(view['mask_reference'])
    need(data.get('measurement_report'),'Actual mask/color/depth measurement report required');verify_ref(root,data['measurement_report']);refs.append(data['measurement_report'])
    values={};kind_counts={}
    for row in data.get('measurements',[]):
        ident=row.get('id');need(isinstance(ident,str) and ident and ident not in values,'Unique measurement ID required')
        kind=row.get('provenance_kind');kind_counts[kind]=kind_counts.get(kind,0)+1
        value=row.get('value_m');need(finite(value),'Measurement value must be finite')
        if kind=='pixel_measurement':
            need(row.get('view_id') in views,'Unknown measurement view');p=row.get('pixel_endpoints');need(isinstance(p,list) and len(p)==2,'Actual pixel endpoints required')
            view=views[row['view_id']];need(row.get('image_sha256')==view['image']['sha256'],'Measurement image identity differs')
            a,b=[pixel_world(view,q) for q in p];axis=row.get('world_axis')
            if axis is None:recomputed=math.sqrt(sum((b[j]-a[j])**2 for j in range(3)))
            else:need(type(axis)is int and 0<=axis<3,'Invalid world axis');recomputed=b[axis]-a[axis]
            need(abs(value-recomputed)<1e-8,'Pixel-derived dimension mismatch: '+ident)
            need(row.get('feature_id') and row.get('mask_label'),'Pixel measurement must identify physical mask feature')
        elif kind in ('semantic_depth','planned_scale'):
            need(isinstance(row.get('reason'),str) and len(row['reason'])>=12,'Inferred/planned value needs an explicit rationale')
            need(row.get('estimated') is True,'Inferred/planned value must remain labelled estimated')
            if require_review:need(row.get('approved') is True,'Unreviewed inferred depth: '+ident)
        else:raise ValueError('Unknown measurement provenance '+str(kind))
        values[ident]=row
    need(values and kind_counts.get('pixel_measurement',0)>0,'No measured pixel boundaries supplied')
    if require_review:
        review=data.get('review',{});need(review.get('status')=='approved' and review.get('orthographic_consistency') is True and review.get('mask_color_depth_checked') is True,'Six-view measurement review pending')
    return {'values':values,'source_references':refs,'kind_counts':kind_counts,'all_pass':True,'scope':'Input identity and affine measurement replay; image masks and color/depth interpretation remain the explicitly referenced review evidence.'}


def resolve_dimensions(value,validated,required_kind=None):
    if isinstance(value,dict) and set(value)=={'measurement'}:
        row=validated['values'].get(value['measurement']);need(row is not None,'Missing dimension '+value['measurement'])
        if required_kind:need(row['provenance_kind']==required_kind,'Boundary requires pixel measurement')
        return row['value_m']
    if isinstance(value,list):return [resolve_dimensions(x,validated,required_kind) for x in value]
    if isinstance(value,dict) and value:return {k:resolve_dimensions(v,validated,required_kind) for k,v in value.items()}
    raise ValueError('Source geometry dimensions require explicit measurement references')
