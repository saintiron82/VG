"""Exact shared grammar regeneration and bounded compile candidate accounting."""
from fit_width import *
import review_surface as view

def master_from_source():
    m,a=load();s=np.load(BASE/'generated/continuous_costume.npz');v,f,ch=s['vertices'],s['triangles'],s['charts'];ma=base.make_master(m,a,v,f,ch,SOURCE)
    ma['id']='approved_violet_measured_width_costume07';ma['extensions'].update({'generator_sha256':sha(Path(__file__).with_name('fit_width.py')),'measured_width_contract_sha256':sha(P),
      'measurement_sha256':sha(BASE/'evidence/measurement.json.gz'),'continuous_source_sha256':sha(BASE/'generated/continuous_costume.npz'),
      'representation':'Independent actual primary masks and height-aligned two-boundary width constraints; inferred intermediate curvature; existing common extrusion adapter',
      'source_shape_status':'UNAPPROVED; same-panel roles provisional, residual/rear solver limits retained','diagnostic_compile_only':True})
    return ma,ch

def run():
    start=time.monotonic();ma,ch=master_from_source();ops=ma['components'][0]['operations'];counts={}
    for i in sorted(set(ch.tolist())):
        sub={**ma,'components':[{**ma['components'][0],'operations':[op for op,k in zip(ops,ch) if k==i]}]};counts[str(i)]=view.candidate_count(sub,.025)
    out={'master_semantic_sha256':digest(ma),'source_recipe':'common_preflight07.master_from_source() from stored measured inputs, source and code',
      'full_master_stored':False,'source_geometry_sha256':sha(BASE/'generated/continuous_costume.npz'),'by_chart_candidate_cells':counts,'total_candidates':sum(counts.values()),'operations':len(ops),
      'pitch_m':.025,'normal_thickness_m':.025,'origin':[0,0,0],'compiler_sha256':sha(REPO/'voxel_character/common/core.py'),
      'render_exporter_sha256':sha(REPO/'voxel_character/common/render_data.py'),'mesher_sha256':sha(REPO/'voxel_character/tools/mesh.py'),
      'script_sha256':sha(__file__),'seconds':time.monotonic()-start,'peak_rss_mib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024}
    write(BASE/'evidence/common_preflight.json',out);print(json.dumps(out))

if __name__=='__main__':run()
