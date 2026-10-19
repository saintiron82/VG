"""Measured full-width projected sections; semantic correspondence remains prior."""
from pathlib import Path
import sys
BASE=Path(__file__).resolve().parents[1];ROOT=BASE.parent
sys.path.insert(0,str(ROOT/'whole_source06/tools'))
import measure_regions as before
from measure_regions import *
BASE=Path(__file__).resolve().parents[1];ROOT=BASE.parent;P=BASE/'data/width_contract.json';A=read(P)

def measured_sections(a,index):
    front=a[f'owned_{index}'];side=a[f'lining_{index}_side_candidate'] if index in [5,6] else a[f'chart_{index}_side']
    fr=C['views']['front'];sv=C['views']['side'];ss=HEIGHT/sv['scale_px_per_unit'];available=np.flatnonzero(side.any(1));rows=[];unknown=[]
    for fy in np.flatnonzero(front.any(1)):
        expected=sv['sole_y']-(fr['sole_y']-(fy+.5))*SCALE/ss;near=int(available[np.argmin(abs(available+.5-expected))]);error=abs(near+.5-expected)
        if error>A['width_correspondence']['height_tolerance_px']:unknown.append(int(fy));continue
        x=np.flatnonzero(front[fy])+fr['crop'][0];u=np.flatnonzero(side[near])+sv['crop'][0]
        rows.append([fy+.5,float(x.min()),float(x.max()+1),near+.5,float(u.min()),float(u.max()+1),int((np.diff(x)>1).sum()+1),int((np.diff(u)>1).sum()+1),float(error)])
    out=np.array(rows,float).reshape((-1,9))
    return out,{'chart':index,'matched_height_rows':len(rows),'unknown_rows':unknown,'front_visible_rows':int(front.any(1).sum()),
      'max_height_disagreement_px':float(out[:,8].max()) if len(out) else None,'multiple_run_front_rows':int((out[:,6]>1).sum()) if len(out) else 0,
      'multiple_run_side_rows':int((out[:,7]>1).sum()) if len(out) else 0,
      'boundary_roles':A['width_correspondence']['semantic_roles'][str(index)],'status':'Actual projected extrema; role correspondence and hidden intermediate surface are explicit priors, not sewing or calibrated material points.'}

def extract(source):
    pm,a=before.extract(source);reports=[]
    for index in A['width_correspondence']['charts']:
        a[f'width_sections_{index}'],r=measured_sections(a,index);reports.append(r)
        if not len(a[f'width_sections_{index}']):raise ValueError('No measured compatible width sections for chart '+str(index))
    m={'schema':'riverstone.measured_width_sections.v1','actual_pixel_sha256':rawsha(source),'source_file_sha256':pm['source_file_sha256'],'source_status':pm['source_status'],'previous_measurement':pm,'section_reports':reports,
      'dependencies':pm['dependencies']+[{'path':str(p.relative_to(REPO)),'sha256':sha(p)} for p in [P,Path(__file__)]],'arrays_digest':digest({k:rawsha(v) for k,v in a.items()})}
    return m,a

def validate(m,a,source):
    if not m or m.get('schema')!='riverstone.measured_width_sections.v1':raise ValueError('Independent full-width section measurements required')
    if m['actual_pixel_sha256']!=rawsha(source):raise ValueError('Wrong source pixels')
    if m['arrays_digest']!=digest({k:rawsha(v) for k,v in a.items()}):raise ValueError('Changed measured input')
    for dep in m['dependencies']:
        if sha(REPO/dep['path'])!=dep['sha256']:raise ValueError('Changed dependency '+dep['path'])

def width_prior(v,pixels,index,a):
    rows=a[f'width_sections_{index}'];py=pixels[:,1];near=np.abs(rows[:,0,None]-py[None,:]).argmin(0);r=rows[near];rank=np.clip((pixels[:,0]-r[:,1])/(r[:,2]-r[:,1]),0,1)
    if A['width_correspondence']['orientation'][str(index)]<0:rank=1-rank
    u=r[:,4]+rank*(r[:,5]-r[:,4]);sv=C['views']['side'];ss=HEIGHT/sv['scale_px_per_unit'];theta=math.radians(A['width_correspondence']['camera_nominal_deg']);z=(math.cos(theta)*v[:,0]-(u-sv['axis_u'])*ss)/math.sin(theta)
    valid=abs(r[:,0]-py)<=A['width_correspondence']['height_tolerance_px'];edge=(np.minimum(abs(pixels[:,0]-r[:,1]),abs(pixels[:,0]-r[:,2]))<=A['width_correspondence']['boundary_proximity_px'])&valid
    return z,edge,valid

def load():
    m=gzread(BASE/'evidence/measurement.json.gz');a=dict(np.load(BASE/'evidence/measurement.npz'));assert m['arrays_file_sha256']==sha(BASE/'evidence/measurement.npz');validate(m,a,SOURCE);return m,a

def run():
    m,a=extract(SOURCE);np.savez_compressed(BASE/'evidence/measurement.npz',**a);m['arrays_file_sha256']=sha(BASE/'evidence/measurement.npz');gzwrite(BASE/'evidence/measurement.json.gz',m);print(json.dumps(m['section_reports']))

if __name__=='__main__':run()
