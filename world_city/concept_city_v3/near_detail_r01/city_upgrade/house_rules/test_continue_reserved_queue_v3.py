import copy
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import continue_reserved_queue_v3 as q


class QueueTests(unittest.TestCase):
    def setUp(self):
        self.job = q.HERE/'jobs/ordinary_r2_2b48237662aa54.job.v3_r02.json'
        self.row = {'job_path': str(self.job.relative_to(q.ROOT)), 'job_sha256': q.runner.a.sha(self.job)}

    def test_completed_actual_house_verified_without_compile(self):
        with patch.object(q.subprocess, 'run', side_effect=AssertionError('No resampling')):
            self.assertEqual(q.complete_record(self.row)['asset_key'], 'ordinary_r2_2b48237662aa54')

    def test_changed_job_refused(self):
        row = dict(self.row, job_sha256='0'*64)
        with self.assertRaisesRegex(ValueError, 'identity changed'):
            q.complete_record(row)

    def test_changed_artifact_refused(self):
        real = q.runner.a.sha
        def sha(path):
            return '0'*64 if str(path).endswith('.render.json.gz') else real(path)
        with patch.object(q.runner.a, 'sha', side_effect=sha):
            with self.assertRaisesRegex(ValueError, 'artifact changed'):
                q.complete_record(self.row)

    def test_incomplete_qa_refused(self):
        real = q.runner.a.load
        def load(path):
            value = real(path)
            if str(path).endswith('.handoff.json'):
                value = copy.deepcopy(value)
                value['independent_qa']['pass'] = False
            return value
        with patch.object(q.runner.a, 'load', side_effect=load):
            with self.assertRaisesRegex(ValueError, 'Incomplete verification'):
                q.complete_record(self.row)

    def test_atomic_state_and_preserve_orphan(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)/'state.json'
            q.save(p, {'a': 1})
            self.assertEqual(q.runner.a.load(p), {'a': 1})
            p.with_name(p.name+'.tmp').write_text('failure evidence')
            with self.assertRaisesRegex(ValueError, 'interrupted'):
                q.save(p, {'a': 2})
            self.assertEqual(q.runner.a.load(p), {'a': 1})


if __name__ == '__main__':
    unittest.main()
