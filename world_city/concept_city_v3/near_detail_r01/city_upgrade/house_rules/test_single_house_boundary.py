import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch
import compile_one_house_boundary as one

class SingleHouseBoundary(unittest.TestCase):
    def test_only_next_asset_and_exact_rules_forwarded_with_stop(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);(root/'.queue_handoff').write_text('fence')
            with patch.object(one.queue,'HERE',root),patch.object(one.queue.a,'load',return_value={'completed':[{'asset_key':'done'}]}),patch.object(one.queue,'phases',return_value=[{'keys':['done','next','later']}]),patch.object(one.queue,'run',return_value=0) as run:
                self.assertEqual(one.run('next',root/'rules'),0)
            self.assertEqual(run.call_args.kwargs['stop_after_asset'],'next');self.assertTrue(run.call_args.kwargs['parent_boundary_worker']);self.assertEqual(set(run.call_args.kwargs['asset_rules']),{'next'})
    def test_later_asset_rejected_before_controller_or_sampling(self):
        with patch.object(one.queue.a,'load',return_value={'completed':[]}),patch.object(one.queue,'phases',return_value=[{'keys':['next','later']}]),patch.object(one.queue,'run') as run,self.assertRaisesRegex(ValueError,'next approved'):
            one.run('later','rules')
        run.assert_not_called()
if __name__=='__main__':unittest.main()
