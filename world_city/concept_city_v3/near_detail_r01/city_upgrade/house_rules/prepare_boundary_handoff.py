"""Add explicit pre-import controller handoff; apply only at an idle boundary."""
from pathlib import Path

BLOCK="""if (__name__=='__main__' and (HERE/'.queue_handoff').exists() and
        os.environ.get('RIVERSTONE_QUEUE_HANDOFF_SHA256')!=hashlib.sha256((HERE/'.queue_handoff').read_bytes()).hexdigest()):
    print(json.dumps({'status':'PENDING_QUEUE_CONTROLLER_HANDOFF','asset_key':sys.argv[1],
        'before_common_import':True,'cell_sampling_started':False}),flush=True)
    raise SystemExit(77)
"""

def build(source):
    if 'PENDING_QUEUE_CONTROLLER_HANDOFF' in source:raise ValueError('Handoff already installed')
    return source.replace("HERE=Path(__file__).resolve().parent\n","HERE=Path(__file__).resolve().parent\n"+BLOCK,1)

if __name__=='__main__':
    path=Path(__file__).resolve().parent/'layered_compile.py'
    path.write_text(build(path.read_text()))
