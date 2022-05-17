import unittest
import tests.helpers as helpers
from qassure import Severity


class TestAudit(unittest.TestCase):

    def test_report(self):
        audit = helpers.AuditorNoFailures()
        report = audit.get_report()
        self.assertFalse(audit.is_blocked)
        self.assertEqual(len(report.report_items), 0)
        item = sum([1 for item in report])
        self.assertEqual(item, 0)
        self.assertTrue(audit.passed(Severity.INFO))
        self.assertTrue(audit.passed(Severity.WARNING))
        self.assertTrue(audit.passed(Severity.ERROR))
        self.assertTrue(audit.passed(Severity.CRITICAL))

    def test_report_with_warning(self):
        audit = helpers.AuditorWithWarning()
        report = audit.get_report()
        self.assertFalse(audit.is_blocked)
        self.assertEqual(len(report.report_items), 1)
        item = sum([1 for item in report])
        self.assertEqual(item, 1)
        self.assertFalse(audit.passed(Severity.INFO))
        self.assertTrue(audit.passed(Severity.WARNING))
        self.assertTrue(audit.passed(Severity.ERROR))
        self.assertTrue(audit.passed(Severity.CRITICAL))



