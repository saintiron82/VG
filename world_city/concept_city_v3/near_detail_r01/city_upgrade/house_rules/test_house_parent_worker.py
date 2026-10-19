import fcntl
import hashlib
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import compile_house_worker as w

class HouseParentWorker(unittest.TestCase):
    def fixture(self,root):
        (root/'compiled').mkdir();(root/'.queue_handoff').write_text('ack');(root/'.compile_pause').write_text('hold NEXT asset')
        (root/'compiled/house_queue.json').write_text(json.dumps({'state':'RUNNING','asset_key':'toy'}))
        return hashlib.sha256((root/'.queue_handoff').read_bytes()).hexdigest()
    def test_resume_of_current_asset_ignores_next_asset_pause_with_live_controller(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);token=self.fixture(root)
            with (root/'queue.lock').open('a') as controller:
                fcntl.flock(controller,fcntl.LOCK_EX|fcntl.LOCK_NB)
                with patch.object(w,'HERE',root),patch.dict(os.environ,{'RIVERSTONE_QUEUE_HANDOFF_SHA256':token}),patch.object(w.layer,'run',return_value={'status':'PASS'}) as engine:
                    self.assertEqual(w.run('toy',root/'compiled/out','catalog',render_only=True,resume=True),0)
                self.assertTrue(engine.call_args.args[-1]);self.assertTrue((root/'.compile_pause').exists())
    def test_explicit_checkpoint_hold_stops_before_second_sampling_budget(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);(root/'.checkpoint_pause').write_text(json.dumps({'asset_key':'toy'}))
            with patch.object(w,'HERE',root),patch.object(w,'verify_controller'),patch.object(w.layer,'run') as engine:
                self.assertEqual(w.run('toy',root/'compiled/out','catalog',render_only=True,resume=True),78)
                engine.assert_not_called()
    def test_detached_worker_refused_before_sampling(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);token=self.fixture(root)
            with patch.object(w,'HERE',root),patch.dict(os.environ,{'RIVERSTONE_QUEUE_HANDOFF_SHA256':token}),patch.object(w.layer,'run') as engine,self.assertRaisesRegex(ValueError,'controller lock'):
                w.run('toy',root/'compiled/out','catalog',render_only=True)
            engine.assert_not_called()
    def test_wrong_asset_refused_before_sampling(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);token=self.fixture(root)
            with patch.object(w,'HERE',root),patch.dict(os.environ,{'RIVERSTONE_QUEUE_HANDOFF_SHA256':token}),patch.object(w.layer,'run') as engine,self.assertRaisesRegex(ValueError,'active asset'):
                w.run('other',root/'compiled/out','catalog',render_only=True)
            engine.assert_not_called()
    def test_soft_stop_status_preserved(self):
        with patch.object(w,'verify_controller'),patch.object(w.layer,'run',return_value={'status':'PENDING_RESUMABLE_CHECKPOINT'}):
            self.assertEqual(w.run('toy',w.HERE/'compiled/toy','catalog',render_only=True),75)
    def test_outside_house_output_scope_rejected(self):
        with patch.object(w,'verify_controller'),patch.object(w.layer,'run') as engine,self.assertRaisesRegex(ValueError,'restricted'):
            w.run('toy','/tmp/out','catalog',render_only=True)
        engine.assert_not_called()
if __name__=='__main__':unittest.main()
