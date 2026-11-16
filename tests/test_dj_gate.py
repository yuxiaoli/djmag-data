"""Offline contract for manual commissioning versus annual activation."""
from pathlib import Path
import itertools
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]

class DJGateTests(unittest.TestCase):
    def test_actual_workflow_expression_truth_table(self):
        text = (ROOT / '.github/workflows/annual.yml').read_text()
        expression = re.search(r'    if: >-\n(.*?)    runs-on:', text, re.S).group(1)
        expected_expression = "vars.SOURCE_COLLECTION_ENABLED == 'true' && (github.event_name == 'workflow_dispatch' || (github.event_name == 'schedule' && vars.DJ_ANNUAL_SYNC_ENABLED == 'true'))"
        self.assertEqual(' '.join(expression.split()), expected_expression)
        permitted = {('true', a, 'workflow_dispatch') for a in ('true','false','')} | {('true','true','schedule')}
        for source, annual, event in itertools.product(('true','false','','TRUE'), ('true','false',''), ('workflow_dispatch','schedule','push','pull_request')):
            with self.subTest(source=source, annual=annual, event=event):
                substituted = expression.replace('vars.SOURCE_COLLECTION_ENABLED',repr(source)).replace('vars.DJ_ANNUAL_SYNC_ENABLED',repr(annual)).replace('github.event_name',repr(event))
                actual = eval(' '.join(substituted.split()).replace('&&','and').replace('||','or'), {'__builtins__':{}}, {})
                self.assertEqual(actual, (source,annual,event) in permitted)

if __name__ == '__main__': unittest.main()
