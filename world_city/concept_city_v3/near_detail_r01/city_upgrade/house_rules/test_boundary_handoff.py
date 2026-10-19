import json
import hashlib
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import types
import unittest
from unittest.mock import patch
import checkpoint_queue
import prepare_boundary_handoff as handoff

class BoundaryHandoffContracts(unittest.TestCase):
    def test_handoff_exits_before_importing_common_or_helpers(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);(root/'.queue_handoff').write_text('controlled restart')
            source='import sys,json,os,hashlib\nfrom pathlib import Path\nHERE=Path(__file__).resolve().parent\nraise AssertionError("sampling imported")\n'
            script=root/'engine.py';script.write_text(handoff.build(source))
            result=subprocess.run([sys.executable,str(script),'toy'],capture_output=True,text=True)
            self.assertEqual(result.returncode,77)
            report=json.loads(result.stdout);self.assertFalse(report['cell_sampling_started'])
            self.assertTrue(report['before_common_import'])

    def test_explicit_handoff_preserves_log_and_gets_fresh_timeout(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);logs=root/'logs';logs.mkdir();old=logs/'toy.compile.log'
            old.write_text(json.dumps({'status':'PENDING_QUEUE_CONTROLLER_HANDOFF','asset_key':'toy','before_common_import':True,'cell_sampling_started':False})+'\n')
            evidence=old.read_bytes()
            with patch.object(checkpoint_queue.subprocess,'run',return_value=types.SimpleNamespace(returncode=0)) as run:
                result=checkpoint_queue.execute(['engine','toy'],root,'toy',logs)
            self.assertEqual(result['state'],'COMPILE_COMPLETE');self.assertEqual(run.call_args.kwargs['timeout'],900)
            self.assertEqual(old.read_bytes(),evidence);self.assertTrue((logs/'toy.after_handoff.compile.log').exists())

    def test_only_explicit_marker_hash_acknowledges_cli_fence(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);marker=root/'.queue_handoff';marker.write_text('unique controller fence')
            source='import sys,json,os,hashlib\nfrom pathlib import Path\nHERE=Path(__file__).resolve().parent\nraise SystemExit(9)\n'
            script=root/'engine.py';script.write_text(handoff.build(source))
            env=dict(os.environ,RIVERSTONE_QUEUE_HANDOFF_SHA256=hashlib.sha256(marker.read_bytes()).hexdigest())
            self.assertEqual(subprocess.run([sys.executable,str(script),'toy'],env=env,capture_output=True).returncode,9)
            marker.write_text('new fence')
            self.assertEqual(subprocess.run([sys.executable,str(script),'toy'],env=env,capture_output=True).returncode,77)

    def test_unavailable_session_receipt_requires_exact_log_and_marker_hash(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);logs=root/'logs';logs.mkdir();path=logs/'toy.compile.log'
            path.write_text('Compilation paused before common import for approved compiler migration\n')
            receipt={'status':'SESSION_UNAVAILABLE_BEFORE_SAMPLING','asset_key':'toy','cell_sampling_started':False,
                     'preserved_log_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'handoff_marker_sha256':'abc'}
            path.with_suffix('.controller_handoff.json').write_text(json.dumps(receipt))
            with patch.dict(os.environ,{'RIVERSTONE_QUEUE_HANDOFF_SHA256':'wrong'}),patch.object(checkpoint_queue.subprocess,'run') as run,self.assertRaises(ValueError):
                checkpoint_queue.execute(['engine'],root,'toy',logs)
            run.assert_not_called()
            with patch.dict(os.environ,{'RIVERSTONE_QUEUE_HANDOFF_SHA256':'abc'}),patch.object(checkpoint_queue.subprocess,'run',return_value=types.SimpleNamespace(returncode=0)):
                self.assertEqual(checkpoint_queue.execute(['engine'],root,'toy',logs)['state'],'COMPILE_COMPLETE')

    def test_controller_wait_occurs_without_child_or_sampling_timeout(self):
        import compile_house_queue as queue
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);marker=root/'.compile_pause';marker.write_text('facility lease');state={}
            with patch.object(queue,'HERE',root),patch.object(queue.b,'atomic_json'),patch.object(queue.time,'sleep',side_effect=lambda _:marker.unlink()) as sleep,patch.object(queue.subprocess,'run') as spawn:
                queue.wait_at_boundary(state,'extension','toy',0)
            self.assertEqual(state['state'],'PAUSED_AT_ASSET_BOUNDARY');sleep.assert_called_once_with(1);spawn.assert_not_called()

if __name__=='__main__':unittest.main()
