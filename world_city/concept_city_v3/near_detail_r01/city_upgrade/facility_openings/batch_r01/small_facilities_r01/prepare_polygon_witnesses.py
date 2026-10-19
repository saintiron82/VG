"""Reserve and prepare finite source-coordinate rays using the frozen verifier."""
import importlib.util,json,resource,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;B=HERE.parent;ROOT=B.parents[5]
sys.path[:0]=[str(B/'sampler_v2'),str(B.parent.parent/'house_rules')]
import reserved_io_r04 as rio
from output_reservations_v3 import ReservationBook
p=B/'polygon_sources/emitted_qa/verify_polygon_windows.py';spec=importlib.util.spec_from_file_location('independent_polygon_rays',p);v=importlib.util.module_from_spec(spec);spec.loader.exec_module(v)
def main(directory):
 resource.setrlimit(resource.RLIMIT_AS,(256*1024**2,256*1024**2));d=directory.resolve();catalog=d/'canonical/generated/catalog.json';rules=d/'rules.v1.json';rows=v.load(catalog)['assets'];identity={'catalog':v.ref(catalog),'rules':v.ref(rules),'driver':v.ref(__file__),'verifier':v.ref(p)};cfg=v.load(B.parent.parent/'house_rules/shared_output_budget.v2.json');book=ReservationBook(ROOT/cfg['book_path'],ROOT,[ROOT/x for x in cfg['retained_roots']],cfg['limit_bytes'],min_free_disk_bytes=cfg['min_free_disk_bytes']);key='facility_source_rays:'+d.name;scopes=[{'directory':str(p.parent.relative_to(ROOT)),'prefix':r['asset_key']+'.source_witnesses'} for r in rows]+[{'directory':str(HERE.relative_to(ROOT)),'prefix':'prepare_polygon_witnesses.py'},{'directory':str((d/'source_ray_validation').relative_to(ROOT)),'prefix':''}];book.reserve(key,scopes,500000,identity);book.acquire_writer(key);w=rio.ReservedWriter(book,key,B,scopes,ROOT)
 try:
  author,_=v.modules();v.write=w.write;reports=[v.prepare_asset(r,catalog,rules,author) for r in rows];report={'all_pass':all(r['source_witnesses_pass'] for r in reports),'assets':reports,'identity':identity,'sampling_scope':'Finite 1D source predicates only; no compile_master call or 3D cell enumeration. Actual emitted quads remain pending.'};w.write(d/'source_ray_validation/report.json',report);assert report['all_pass'];book.release(key,identity,'Source-coordinate polygon witnesses ready; actual emitted render QA still required.');print(json.dumps(report),flush=True)
 finally:w.close()
if __name__=='__main__':main(Path(sys.argv[1]))
