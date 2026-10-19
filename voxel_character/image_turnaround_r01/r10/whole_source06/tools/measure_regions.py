"""Separate actual visible side lining pixels; identity and occlusion explicit."""
from pathlib import Path
import sys
BASE=Path(__file__).resolve().parents[1];ROOT=BASE.parent
sys.path.insert(0,str(ROOT/'whole_source05/tools'))
import height_correspondence as prev
from height_correspondence import *
BASE=Path(__file__).resolve().parents[1];ROOT=BASE.parent;P=BASE/'data/lining_regions.json';A=read(P)
from PIL import ImageDraw

def extract(source):
    pm,a=prev.extract(source);sv=C['views']['side'];excluded=np.zeros_like(a['side_support'])
    for q in A['explicit_semantic_exclusions']:excluded|=polygon_mask(q['polygon'],sv['crop'])
    occupied=np.zeros_like(excluded)
    for i in A['side_visible_owner_priority']:occupied|=a[f'chart_{i}_side']
    reports=[]
    for q in A['side_regions']:
        i=q['provisional_front_chart'];domain=polygon_mask(q['semantic_domain'],sv['crop']);actual=domain&a['side_support'];visible=actual&~excluded&~occupied
        a[f'lining_{i}_side_candidate']=visible;a[f'lining_{i}_unknown_overlap']=actual&occupied&~excluded
        a[f'lining_{i}_semantic_domain']=domain;a[f'lining_{i}_footwear_unknown']=actual&excluded
        reports.append({'id':q['id'],'provisional_front_chart':i,'semantic_domain_pixels':int(domain.sum()),'actual_cloth_candidate_pixels':int(actual.sum()),
          'visible_nonduplicated_candidate_pixels':int(visible.sum()),'earlier_side_chart_overlap_unknown_pixels':int((actual&occupied&~excluded).sum()),
          'footwear_candidate_conflict_pixels':int((actual&excluded).sum()),'front_owned_pixels':int(a[f'owned_{i}'].sum()),
          'actual_example_pixel_rgb':source[q['example_actual_pixel'][1],q['example_actual_pixel'][0]].tolist(),
          'identity':'PROVISIONAL semantic pairing only; no observed material-point correspondence','hidden_root':None})
        if not visible.any():raise ValueError('No measured visible lining input for '+q['id'])
        occupied|=visible
    a['side_footwear_semantic_unknown']=excluded&a['side_support']
    a['side_lining_owned_union']=a['lining_5_side_candidate']|a['lining_6_side_candidate']
    a['side_lining_domain_union']=a['lining_5_semantic_domain']|a['lining_6_semantic_domain']
    relevant=a['side_lining_domain_union']&a['side_support'];explained=occupied|excluded
    coverage={'measured_cloth_pixels_in_lining_domains':int(relevant.sum()),'covered_by_known_side_chart_or_lining_candidate_or_footwear_unknown':int((relevant&explained).sum()),
      'unassigned_relevant_pixels':int((relevant&~explained).sum()),'lining_candidate_overlap_pixels':int((a['lining_5_side_candidate']&a['lining_6_side_candidate']).sum()),
      'front_chart5_chart6_overlap_pixels':int((a['owned_5']&a['owned_6']).sum()),'front_masks_unchanged':True,
      'coverage_is_semantic_accounting_not_geometry_or_same_panel_identity_pass':True}
    m={'schema':'riverstone.split_lining_measurements.v1','actual_pixel_sha256':rawsha(source),'source_file_sha256':pm['source_file_sha256'],'source_status':pm['source_status'],
      'previous_measurement':pm,'regions':reports,'coverage':coverage,'dependencies':pm['dependencies']+[{'path':str(p.relative_to(REPO)),'sha256':sha(p)} for p in [P,Path(__file__)]],
      'arrays_digest':digest({k:rawsha(v) for k,v in a.items()})}
    return m,a

def validate(m,a,source):
    if not m or m.get('schema')!='riverstone.split_lining_measurements.v1':raise ValueError('Independent measured lining regions required')
    if m['actual_pixel_sha256']!=rawsha(source):raise ValueError('Wrong source pixels')
    if m['arrays_digest']!=digest({k:rawsha(v) for k,v in a.items()}):raise ValueError('Changed measured inputs')
    for dep in m['dependencies']:
        if sha(REPO/dep['path'])!=dep['sha256']:raise ValueError('Changed dependency '+dep['path'])

def load():
    m=gzread(BASE/'evidence/measurement.json.gz');a=dict(np.load(BASE/'evidence/measurement.npz'));assert m['arrays_file_sha256']==sha(BASE/'evidence/measurement.npz');validate(m,a,SOURCE);return m,a

def run():
    m,a=extract(SOURCE);np.savez_compressed(BASE/'evidence/measurement.npz',**a);m['arrays_file_sha256']=sha(BASE/'evidence/measurement.npz');gzwrite(BASE/'evidence/measurement.json.gz',m)
    canvas=Image.new('RGB',(1152,620),'white');d=ImageDraw.Draw(canvas);d.text((12,10),'ACTUAL INPUT OWNERSHIP06 | cyan chart5 / orange chart6 | magenta footwear unknown | pair identity provisional',fill='black')
    for j,name in enumerate(['front','side']):
        view=C['views'][name];x0,y0,x1,y1=view['crop'];rgb=SOURCE[y0:y1,x0:x1].astype(float)
        for index,col in [(5,[0,175,190]),(6,[220,120,20])]:
            mask=a[f'owned_{index}'] if name=='front' else a[f'lining_{index}_side_candidate'];rgb[mask]=.5*rgb[mask]+.5*np.array(col)
        if name=='side':
            mask=a['side_footwear_semantic_unknown'];rgb[mask]=.5*rgb[mask]+.5*np.array([220,0,160])
        im=Image.fromarray(np.uint8(np.clip(rgb,0,255))).crop((0,375,x1-x0,624));im.thumbnail((556,550));canvas.paste(im,(j*576+10,50));d.text((j*576+10,590),name+' measured regions; dark gaps retain occlusion/unknown',fill='black')
    canvas.save(BASE/'generated/lining_input_ownership.jpg',quality=87)
    print(json.dumps({'regions':m['regions'],'coverage':m['coverage'],'measurement_sha256':sha(BASE/'evidence/measurement.json.gz')}))

if __name__=='__main__':run()
