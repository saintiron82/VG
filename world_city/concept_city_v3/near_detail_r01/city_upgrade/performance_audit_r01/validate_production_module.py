"""Bounded validation of opt-in module; does not touch runtime callers."""
import hashlib,importlib,json,pathlib,resource,signal,sys,time
HERE=pathlib.Path(__file__).resolve().parent;ROOT=HERE.parents[4];sys.path.insert(0,str(ROOT));sys.dont_write_bytecode=True;resource.setrlimit(resource.RLIMIT_AS,(512*1024**2,512*1024**2));signal.alarm(30)
from voxel_character.common import core
original_compile=core.compile_master;original_helpers={n:getattr(core,n) for n in ('prepare_shape','contains','inside_polygon','validate_master','transform')};before=hashlib.sha256(pathlib.Path(core.__file__).read_bytes()).hexdigest()
from voxel_character.common import exact_sampling_v2 as fast
assert core.compile_master is original_compile
assert all(getattr(fast,n) is f and getattr(core,n) is f for n,f in original_helpers.items())
selection=json.loads((HERE/'selection.json').read_text());master=json.loads((HERE/'bounded_master.json').read_text());kw={'cell_bounds':selection['bounds'],'max_candidate_cells':300000,'max_output_cells':100000}
t=time.perf_counter();a=core.compile_master(master,{'pitch':.05},**kw);ref_seconds=time.perf_counter()-t
t=time.perf_counter();b=fast.compile_master_v2(master,{'pitch':.05},**kw);fast_seconds=time.perf_counter()-t
assert {k:v for k,v in a.items() if k!='compiler_source_hash'}=={k:v for k,v in b.items() if k not in ('compiler_source_hash','compiler_provenance')}
expected=fast.REFERENCE_CORE_SHA256;fast.REFERENCE_CORE_SHA256='0'*64
try:
 try:fast.compile_master_v2({},{});raise AssertionError('Reference mismatch must fail before evaluating master')
 except fast.ReferenceCompilerMismatch as error:guard=str(error)
finally:fast.REFERENCE_CORE_SHA256=expected
assert core.compile_master is original_compile and hashlib.sha256(pathlib.Path(core.__file__).read_bytes()).hexdigest()==before
# The same existing synthetic fixture has already been tested at both pitches.
report={'production_module':str(pathlib.Path(fast.__file__).relative_to(ROOT)),'provenance':fast.get_sampler_provenance(),'reference_source_unchanged':True,'default_compile_function_unchanged':True,'reference_helpers_shared_not_replaced':True,'reference_mismatch_fails_before_sampling':True,'guard_message':guard,'real_region_full_result_exact_except_compiler_source_hash_and_additive_provenance':True,'payload_hash':a['payload_hash'],'candidate_cells':a['candidate_cells'],'occupied_cells':len(a['cells']),'reference_seconds':ref_seconds,'v2_seconds':fast_seconds,'speedup':ref_seconds/fast_seconds,'peak_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'production_runtime_activation':False}
(HERE/'production_module_validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
