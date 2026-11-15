import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parents[1]/'scripts'))
from presentation import description,movement
class PresentationTests(unittest.TestCase):
 def test_unknown_is_not_new(self):
  self.assertEqual(movement({}),'Not shown by source')
 def test_exact_labels(self):
  for value in ('New Entry','Re-entry','Non-Mover'):
   self.assertEqual(movement({'profile_metadata':{'movement':value,'movement_places':None}}),value)
 def test_places(self):
  self.assertEqual(movement({'profile_metadata':{'movement':'Down','movement_places':26}}),'Down · 26 places')
 def test_summary_no_nationality_guess(self):
  d={'name':'Example','rankings':[{'rank':1,'year':2026}],'origin':'UK/Finland','styles':['House'],'best_known_for':'Live sets'}
  self.assertIn('From: UK/Finland.',description(d));self.assertNotIn('nationality',description(d))
