"""Configure the frozen common polygon opening author; no asset-specific code."""
import argparse,resource,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent.parent))
import author as shared

def main(directory):
    directory=directory.resolve();shared.HERE=directory
    (directory/'generated').mkdir(parents=True,exist_ok=True)
    before=shared.sha(shared.__file__);shared.author();assert shared.sha(shared.__file__)==before
    shared.write(directory/'authoring_provenance.json',{'schema':'riverstone.facility.polygon_author_config.v1','shared_author_path':str(Path(shared.__file__).relative_to(shared.ROOT)),'shared_author_sha256':before,'rules_sha256':shared.sha(directory/'rules.v1.json'),'wrapper_sha256':shared.sha(__file__),'compile_calls':0,'max_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'runtime_activation':False})
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('rules_directory',type=Path);main(p.parse_args().rules_directory)
