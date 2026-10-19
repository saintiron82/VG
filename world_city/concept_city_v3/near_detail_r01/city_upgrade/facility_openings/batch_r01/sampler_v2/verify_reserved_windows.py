"""Run the frozen independent polygon verifier, then reserved-write its report."""
import argparse,importlib.util,json,resource,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;B=HERE.parent
sys.path.insert(0,str(B.parent))
import author as a
import reserved_io_r03 as reserved_io

def run(catalog,render):
    resource.setrlimit(resource.RLIMIT_AS,(256*1024*1024,256*1024*1024));cat=a.load(catalog);w=reserved_io.writer_for_catalog(cat,a.ROOT,B,a.HERE.parent/'house_rules');path=B/'polygon_sources/emitted_qa/verify_polygon_windows.py';spec=importlib.util.spec_from_file_location('frozen_polygon_witnesses',path);v=importlib.util.module_from_spec(spec);sys.modules[spec.name]=v;spec.loader.exec_module(v);_,stream=v.modules();witness=path.parent/(cat['asset_key']+'.source_witnesses.json');report=v.verify(witness,render,stream,save_report=False);report['reserved_driver_reference']={'path':str(Path(__file__).relative_to(a.ROOT)),'sha256':a.sha(__file__)};w.write(path.parent/(cat['asset_key']+'.emitted_geometry_qa.json'),report);assert report['all_pass'];print(json.dumps({k:report[k] for k in ['asset_key','all_pass','quad_count','render_sha256','failure_count','elapsed_seconds','max_rss_kib']}),flush=True)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('catalog',type=Path);p.add_argument('render',type=Path);q=p.parse_args();run(q.catalog.resolve(),q.render.resolve())
