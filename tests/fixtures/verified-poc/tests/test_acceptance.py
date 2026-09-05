import unittest

from lab_poc import trigger


class VerifiedPoCAcceptanceTest(unittest.TestCase):
    def test_observable_lab_behavior(self):
        self.assertEqual(trigger("controlled-lab"), "verified:controlled-lab")
