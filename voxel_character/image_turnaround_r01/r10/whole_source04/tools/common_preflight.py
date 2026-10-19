from physical_depth import *
import review_surface as view

def master_from_source():
 m,a=load();s=np.load(BASE/'generated/continuous_costume.npz');v,f,ch=s['vertices'],s['triangles'],s['charts'];ma=base.make_master(m,a,v,f,ch,SOURCE);ma['id']='approved_violet_physical_depth_costume04';ma['extensions'].update({'generator_sha256':sha(Path(__file__).with_name('physical_depth.py')),'depth_contract_sha256':sha(P),'measurement_sha256':sha(BASE/'evidence/measurement.json.gz'),'continuous_source_sha256':sha(BASE/'generated/continuous_costume.npz'),'source_shape_status':'UNAPPROVED, rear separation contradictions and solver iteration limit remain','diagnostic_compile_only':True});return ma,ch

def run():
 t=time.monotonic();ma,ch=master_from_source();ops=ma['components'][0]['operations'];counts={}
 for i in sorted(set(ch.tolist())):
  small={**ma,'components':[{**ma['components'][0],'operations':[op for op,j in zip(ops,ch) if j==i]}]};counts[str(i)]=view.candidate_count(small,.025)
 h=digest(ma);compressed=gzip.compress(canonical(ma),mtime=0);out={'master_semantic_sha256':h,'source_recipe':'Rebuild exactly using common_preflight.master_from_source(); compressed source vertices/faces and independent measured input are authoritative, not render textures.','common_grammar':'Triangle normal-thickness prisms adapted to existing common extrusion; same25mm thickness/origin','common25_candidate_counts_by_chart':counts,'total_actual_compiler_AABB_candidates':sum(counts.values()),'operations':len(ops),'compressed_fullmaster_bytes_if_written':len(compressed),'fullmaster_stored':False,'master_regeneration_required_because_budget':True,'elapsed_seconds':time.monotonic()-t,'peak_rss_mib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024,'compiler_sha256':sha(REPO/'voxel_character/common/core.py'),'render_exporter_sha256':sha(REPO/'voxel_character/common/render_data.py'),'mesher_sha256':sha(REPO/'voxel_character/tools/mesh.py'),'script_sha256':sha(__file__)};write(BASE/'evidence/common_preflight.json',out);print(json.dumps(out))
if __name__=='__main__':run()
