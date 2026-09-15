import unittest
import run

PASS="[SCB] matched=200 mismatched=0\nUVM_INFO : 5\nUVM_WARNING : 1\nUVM_ERROR : 0\nUVM_FATAL : 0"
FAIL="[SCB] matched=180 mismatched=20\nUVM_INFO : 5\nUVM_WARNING : 1\nUVM_ERROR : 20\nUVM_FATAL : 0\nSCB_MISMATCH_EXPECTED"
class ClassificationTests(unittest.TestCase):
 def test_duplicate_severity_cannot_hide_an_error(self):
  text='[SCB] matched=200 mismatched=0\nUVM_INFO : 1\nUVM_ERROR : 1\nUVM_ERROR : 0\nUVM_FATAL : 0'
  self.assertFalse(run.classify(text,0,False,False))
 def test_real_pass(self): self.assertTrue(run.classify(PASS,0,False,False))
 def test_exit_zero_alone_fails(self): self.assertFalse(run.classify("",0,False,False))
 def test_correct_rejects_mismatch(self): self.assertFalse(run.classify(FAIL,0,False,False))
 def test_mutant_requires_named_marker(self): self.assertTrue(run.classify(FAIL,0,False,True))
 def test_mutant_rejects_arbitrary_error(self): self.assertFalse(run.classify(FAIL.replace("SCB_MISMATCH_EXPECTED",""),1,False,True))
 def test_mutant_rejects_nonzero_exit_even_with_markers(self): self.assertFalse(run.classify(FAIL,1,False,True))
 def test_timeout_never_passes(self): self.assertFalse(run.classify(FAIL,124,True,True))
 def test_duplicate_scoreboard_summary_fails(self): self.assertFalse(run.classify(PASS+"\n"+PASS,0,False,False))
if __name__=="__main__": unittest.main()
