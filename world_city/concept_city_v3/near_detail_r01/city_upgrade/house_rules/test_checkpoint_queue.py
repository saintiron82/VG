import json
from pathlib import Path
import subprocess
import tempfile
import types
import unittest
from unittest.mock import patch
import checkpoint_queue as q


class CheckpointQueueContracts(unittest.TestCase):
    def checkpoint(self,root,status='PENDING_RESUMABLE_CHECKPOINT',sessions=1):
        (root/'toy.layered.checkpoint').mkdir(exist_ok=True)
        (root/'toy.layered.checkpoint_sessions.json').write_text(json.dumps({'sessions':[
            {'status':status,'wall_limit_seconds':900} for _ in range(sessions)]}))
        (root/'toy.layered.resumable.json').write_text(json.dumps({'status':status,'session':sessions,'max_sessions':2,'total_wall_budget_seconds':1800}))

    def test_soft_stop_resumes_once_and_preserves_logs(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);calls=[]
            def run(command,**kwargs):
                calls.append(command)
                if len(calls)==1:self.checkpoint(root)
                return types.SimpleNamespace(returncode=75 if len(calls)==1 else 0)
            with patch.object(q.subprocess,'run',side_effect=run):result=q.execute(['python','engine'],root,'toy',root/'logs')
            self.assertEqual(result['execution'],2)
            self.assertNotIn('--resume-checkpoint',calls[0]);self.assertIn('--resume-checkpoint',calls[1])
            self.assertEqual(len(list((root/'logs').glob('*.log'))),2)

    def test_existing_soft_stop_restarts_only_second_session(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);self.checkpoint(root)
            with patch.object(q.subprocess,'run',return_value=types.SimpleNamespace(returncode=0)) as run:
                self.assertEqual(q.execute(['python','engine'],root,'toy',root/'logs')['execution'],2)
            self.assertEqual(run.call_count,1);self.assertIn('--resume-checkpoint',run.call_args.args[0])

    def test_exhausted_or_failed_checkpoint_rejected_without_process(self):
        for status,sessions in [('PENDING_RESUMABLE_CHECKPOINT',2),('FAILED_PRESERVED',1)]:
            with self.subTest(status=status),tempfile.TemporaryDirectory() as d:
                root=Path(d);self.checkpoint(root,status,sessions)
                with patch.object(q.subprocess,'run') as run,self.assertRaises(ValueError):q.execute(['engine'],root,'toy',root/'logs')
                run.assert_not_called()

    def test_timeout_does_not_blindly_restart(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            with patch.object(q.subprocess,'run',side_effect=subprocess.TimeoutExpired('engine',900)) as run:
                result=q.execute(['engine'],root,'toy',root/'logs')
            self.assertEqual(run.call_count,1);self.assertEqual(result['state'],'PENDING_TIME_LIMIT')

    def test_old_failed_log_preserved(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);logs=root/'logs';logs.mkdir();(logs/'toy.compile.log').write_text('evidence')
            with patch.object(q.subprocess,'run') as run,self.assertRaises(ValueError):q.execute(['engine'],root,'toy',logs)
            run.assert_not_called();self.assertEqual((logs/'toy.compile.log').read_text(),'evidence')

if __name__=='__main__':unittest.main()
