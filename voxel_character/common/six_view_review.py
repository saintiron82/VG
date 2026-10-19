"""Shared six-direction evidence gate, not an automatic artistic judge.

Missing/conflicting reference views never count as measured fidelity passes.
An unseen underside may have a reviewed design section, separately reported.
"""
from pathlib import Path
import hashlib, math

VIEWS = {'front':(0,0,1),'back':(0,0,-1),'right':(1,0,0),
         'left':(-1,0,0),'top':(0,1,0),'bottom':(0,-1,0)}
TOPICS = {'silhouette','missing_parts','stretching','color','component_relationships'}

def validate(report, root):
    root=Path(root).resolve(); errors=[]; unresolved=[]; design_only=[]
    def check(ok, why):
        if not ok: errors.append(why)
    def ref(item,label):
        if not isinstance(item,dict): errors.append(label+': missing reference'); return
        path=Path(str(item.get('path','')))
        if path.is_absolute() or '..' in path.parts: errors.append(label+': unsafe reference'); return
        p=(root/path).resolve()
        if not p.is_relative_to(root) or not p.is_file(): errors.append(label+': unavailable'); return
        check(hashlib.sha256(p.read_bytes()).hexdigest()==item.get('sha256'),label+': hash mismatch')
    check(report.get('schema')=='riverstone.six_view_review.v1','invalid schema')
    ref(report.get('source_render'),'source_render')
    check(bool(report.get('reviewer')),'reviewer missing')
    check(report.get('actual_images_opened') is True,'actual views not inspected')
    rows=report.get('views',[]); ids=[r.get('view') for r in rows]
    check(len(ids)==len(set(ids)),'duplicate view')
    check(set(VIEWS)<=set(ids),'six required orthographic directions missing')
    for row in rows:
        name=row.get('view'); prefix=str(name)
        if name not in VIEWS: continue
        ref(row.get('image'),prefix+'.image');ref(row.get('capture_report'),prefix+'.capture')
        check(row.get('engine')=='Godot',prefix+': actual Godot required')
        check(row.get('projection')=='orthographic',prefix+': perspective is not orthographic')
        check(row.get('source_render_sha256')==report.get('source_render',{}).get('sha256'),prefix+': stale render')
        try:
            camera=row['camera'];p=camera['position'];t=camera['target'];up=camera['up']
            check(len(p)==len(t)==len(up)==3,prefix+': camera dimensionality')
            values=[float(x) for x in p+t+up];check(all(math.isfinite(x) for x in values),prefix+': nonfinite camera')
            axis=[float(p[i])-float(t[i]) for i in range(3)];length=math.sqrt(sum(x*x for x in axis));axis=[x/length for x in axis]
            check(sum(axis[i]*VIEWS[name][i] for i in range(3))>0.999999,prefix+': wrong direction')
            un=math.sqrt(sum(float(x)**2 for x in up));check(un>0 and abs(sum(axis[i]*float(up[i]) for i in range(3))/un)<1e-5,prefix+': invalid up axis')
            check(float(camera['size_m'])>0,prefix+': invalid size')
        except (KeyError,TypeError,ValueError,ZeroDivisionError,IndexError):errors.append(prefix+': incomplete camera')
        obs=row.get('observations',[])
        check(TOPICS<={o.get('topic') for o in obs},prefix+': incomplete visual critique')
        for item in obs:
            check(bool(item.get('reason')),prefix+': critique reason missing')
            if item.get('status')!='pass':unresolved.append(prefix+': '+str(item.get('topic')))
        status=row.get('reference_status')
        check(status in {'measured_reference','design_section_only','contradictory','unavailable'},prefix+': invalid reference status')
        if status=='measured_reference':
            ref(row.get('reference_image'),prefix+'.reference');ref(row.get('comparison'),prefix+'.comparison')
            if row.get('alignment_pass') is not True:unresolved.append(prefix+': registration unresolved')
        elif status=='design_section_only':
            ref(row.get('design_contract'),prefix+'.design_contract');check(bool(row.get('inference_basis')),prefix+': design inference missing')
            design_only.append(name);unresolved.append(prefix+': no observed reference')
        else:unresolved.append(prefix+': '+str(status))
    return {'all_pass':not errors and not unresolved,'evidence_complete':not errors,
            'errors':errors,'unresolved':unresolved,'design_only_views':design_only,
            'scope':'Evidence and recorded six-view critique only; no automatic art or hidden-surface reconstruction approval.'}
