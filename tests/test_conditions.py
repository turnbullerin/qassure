import unittest
import qassure
import qassure.framework
import tests.helpers as helpers


class TestAgent(unittest.TestCase):

    def test_add_report_item(self):
        agent = helpers.BaseAuditor()
        self.assertEqual(len(agent.report), 0)
        agent.add_report_item(
            qassure.Severity.BLOCKER,
            "test message",
            None
        )
        self.assertEqual(len(agent.report), 1)
        self.assertEqual(agent.report[0][0], qassure.Severity.BLOCKER)
        self.assertEqual(agent.report[0][1], "test message")
        self.assertEqual(agent.report[0][2], "Unknown")
        agent.add_report_item(
            qassure.Severity.CRITICAL,
            "test message2",
            None
        )
        self.assertEqual(len(agent.report), 2)
        self.assertEqual(agent.report[0][0], qassure.Severity.BLOCKER)
        self.assertEqual(agent.report[0][1], "test message")
        self.assertEqual(agent.report[0][2], "Unknown")
        self.assertEqual(agent.report[1][0], qassure.Severity.CRITICAL)
        self.assertEqual(agent.report[1][1], "test message2")
        self.assertEqual(agent.report[1][2], "Unknown")

    def test_blocking_failure(self):
        class AuditorForTesting(qassure.Auditor):
            def audit(self):
                self.claim(None, qassure.Severity.BLOCKER).is_not_none()
                self.claim(1).is_type(str)
        obj = AuditorForTesting()
        obj.run_audit()
        self.assertEqual(len(obj.report), 1)
        self.assertTrue(obj.is_blocked)

    def test_preblocking_failure(self):
        class AuditorForTesting(qassure.Auditor):
            def audit(self):
                self.claim(2).is_type(str)
                self.claim(None, qassure.Severity.BLOCKER).is_not_none()
                self.claim(1).is_type(str)
        obj = AuditorForTesting()
        obj.run_audit()
        self.assertEqual(len(obj.report), 2)
        self.assertTrue(obj.is_blocked)

    def test_inspector_creation(self):
        agent = helpers.BaseAuditor()
        inspector = agent.claim("a", qassure.Severity.BLOCKER, "abc")
        self.assertEqual(inspector.error_level, qassure.Severity.BLOCKER)
        self.assertEqual(inspector.object_name, "abc")
        self.assertEqual(inspector.value, "a")
        inspector = agent.claim("b", qassure.Severity.CRITICAL)
        self.assertEqual(inspector.error_level, qassure.Severity.CRITICAL)
        self.assertEqual(inspector.value, "b")
        self.assertEqual(inspector.object_name, '["b"]')
        inspector = agent.claim(None, qassure.Severity.ERROR)
        self.assertEqual(inspector.error_level, qassure.Severity.ERROR)
        self.assertIsNone(inspector.value)
        self.assertEqual(inspector.object_name, '[None]')
        self.value = 5
        inspector = agent.claim(self.value, qassure.Severity.WARNING)
        self.assertEqual(inspector.error_level, qassure.Severity.WARNING)
        self.assertEqual(inspector.value, 5)
        self.assertEqual(inspector.object_name, '[self.value]')
        self.value = lambda: True
        inspector = agent.claim(self.value())
        self.assertTrue(inspector.value)
        self.assertEqual(inspector.object_name, '[self.value()]')


class TestInspector(unittest.TestCase):

    def setUp(self):
        self.agent = helpers.BaseAuditor()

    def test_report_deficiency(self):
        inspector = self.agent.claim("test", qassure.Severity.BLOCKER)
        self.assertRaises(qassure.framework.BlockingDeficiencyError, inspector._report_deficiency, "test message")
        self.assertEqual(len(self.agent.report), 1)
        self.assertEqual(self.agent.report[0][0], qassure.Severity.BLOCKER)
        self.assertEqual(self.agent.report[0][1], "test message")
        inspector = self.agent.claim("test2", qassure.Severity.CRITICAL)
        inspector._report_deficiency("test message2")
        self.assertEqual(len(self.agent.report), 2)
        self.assertEqual(self.agent.report[0][0], qassure.Severity.BLOCKER)
        self.assertEqual(self.agent.report[0][1], "test message")
        self.assertEqual(self.agent.report[1][0], qassure.Severity.CRITICAL)
        self.assertEqual(self.agent.report[1][1], "test message2")
        inspector = self.agent.claim("test2", qassure.Severity.ERROR)
        inspector._report_deficiency("test message3")
        inspector = self.agent.claim("test2", qassure.Severity.WARNING)
        inspector._report_deficiency("test message4")
        self.assertEqual(len(self.agent.report), 4)
        self.assertEqual(self.agent.report[2][0], qassure.Severity.ERROR)
        self.assertEqual(self.agent.report[2][1], "test message3")
        self.assertEqual(self.agent.report[3][0], qassure.Severity.WARNING)
        self.assertEqual(self.agent.report[3][1], "test message4")

    def assertIsDeficiency(self, call, *args):
        before_count = len(self.agent.report)
        call(*args)
        self.assertEqual(len(self.agent.report), before_count + 1)

    def assertIsNotDeficiency(self, call, *args):
        before_count = len(self.agent.report)
        call(*args)
        self.assertEqual(len(self.agent.report), before_count)

    def test_is_none(self):
        self.assertIsDeficiency(self.agent.claim("foo").is_none, "test message")
        self.assertEqual(self.agent.report[-1][1], "test message")
        self.assertIsNotDeficiency(self.agent.claim(None).is_none)
        self.assertIsDeficiency(self.agent.claim("").is_none)
        self.assertIsDeficiency(self.agent.claim(0).is_none)
        self.assertIsDeficiency(self.agent.claim(5).is_none)
        self.assertIsDeficiency(self.agent.claim(False).is_none)
        self.assertIsDeficiency(self.agent.claim(True).is_none)

    def test_is_not_none(self):
        self.assertIsNotDeficiency(self.agent.claim("foo").is_not_none)
        self.assertIsDeficiency(self.agent.claim(None).is_not_none, "test message2")
        self.assertEqual(self.agent.report[-1][1], "test message2")
        self.assertIsNotDeficiency(self.agent.claim("").is_not_none)
        self.assertIsNotDeficiency(self.agent.claim(0).is_not_none)
        self.assertIsNotDeficiency(self.agent.claim(5).is_not_none)
        self.assertIsNotDeficiency(self.agent.claim(False).is_not_none)
        self.assertIsNotDeficiency(self.agent.claim(True).is_not_none)

    def test_is_truthy(self):
        self.assertIsNotDeficiency(self.agent.claim(True).is_truthy)
        self.assertIsDeficiency(self.agent.claim(False).is_truthy)
        self.assertIsNotDeficiency(self.agent.claim(5).is_truthy)
        self.assertIsDeficiency(self.agent.claim(0).is_truthy)
        self.assertIsNotDeficiency(self.agent.claim(-5).is_truthy)
        self.assertIsNotDeficiency(self.agent.claim(1).is_truthy)
        self.assertIsNotDeficiency(self.agent.claim(-1).is_truthy)
        self.assertIsNotDeficiency(self.agent.claim("abcde").is_truthy)
        self.assertIsDeficiency(self.agent.claim(range(0)).is_truthy)
        self.assertIsNotDeficiency(self.agent.claim(range(0, 5)).is_truthy)
        self.assertIsDeficiency(self.agent.claim("").is_truthy)
        self.assertIsDeficiency(self.agent.claim(None).is_truthy)
        self.assertIsDeficiency(self.agent.claim(0.0).is_truthy)
        self.assertIsDeficiency(self.agent.claim(0.0j).is_truthy)
        self.assertIsDeficiency(self.agent.claim([]).is_truthy)
        self.assertIsDeficiency(self.agent.claim({}).is_truthy)
        self.assertIsDeficiency(self.agent.claim(tuple()).is_truthy)
        self.assertIsNotDeficiency(self.agent.claim([0]).is_truthy)
        self.assertIsNotDeficiency(self.agent.claim(["0"]).is_truthy)
        self.assertIsNotDeficiency(self.agent.claim(["False"]).is_truthy)
        self.assertIsNotDeficiency(self.agent.claim(["abcd"]).is_truthy)
        self.assertIsNotDeficiency(self.agent.claim(["None"]).is_truthy)
        self.assertIsNotDeficiency(self.agent.claim([False]).is_truthy)
        self.assertIsNotDeficiency(self.agent.claim([None]).is_truthy)
        self.assertIsNotDeficiency(self.agent.claim({0}).is_truthy)
        self.assertIsNotDeficiency(self.agent.claim({False}).is_truthy)
        self.assertIsNotDeficiency(self.agent.claim({None}).is_truthy)
        self.assertIsNotDeficiency(self.agent.claim((0,)).is_truthy)
        self.assertIsNotDeficiency(self.agent.claim((False,)).is_truthy)
        self.assertIsNotDeficiency(self.agent.claim((None,)).is_truthy)
        self.assertIsNotDeficiency(self.agent.claim({"a", "c", "d"}).is_truthy)
        self.assertIsNotDeficiency(self.agent.claim({"0": False}).is_truthy)
        self.assertIsNotDeficiency(self.agent.claim({"a": "a", "c": "b", "d": "f"}).is_truthy)
        self.assertIsNotDeficiency(self.agent.claim((0,)).is_truthy)
        self.assertIsNotDeficiency(self.agent.claim((1, 2, 3)).is_truthy)
        self.assertIsDeficiency(self.agent.claim(helpers.TruthyClass(False)).is_truthy)
        self.assertIsNotDeficiency(self.agent.claim(helpers.TruthyClass(True)).is_truthy)

    def test_is_type(self):
        self.assertIsNotDeficiency(self.agent.claim("five").is_type, str)
        self.assertIsNotDeficiency(self.agent.claim(5).is_type, int)
        self.assertIsNotDeficiency(self.agent.claim(True).is_type, bool)
        self.assertIsNotDeficiency(self.agent.claim(self).is_type, self.__class__)
        self.assertIsNotDeficiency(self.agent.claim(4.3).is_type, float)
        self.assertIsNotDeficiency(self.agent.claim([]).is_type, list)
        self.assertIsNotDeficiency(self.agent.claim(["a", "b", 4]).is_type, list)
        self.assertIsNotDeficiency(self.agent.claim({"a", "b"}).is_type, set)
        self.assertIsNotDeficiency(self.agent.claim({"a": "c", "b": "d"}).is_type, dict)
        self.assertIsNotDeficiency(self.agent.claim(("a",)).is_type, tuple)
        self.assertIsNotDeficiency(self.agent.claim(self).is_type, unittest.TestCase)
        self.assertIsDeficiency(self.agent.claim("5").is_type, int)
        self.assertIsDeficiency(self.agent.claim(0).is_type, bool)

    def test_is_callable(self):
        self.assertIsNotDeficiency(self.agent.claim(TestAgent).is_callable)
        self.assertIsNotDeficiency(self.agent.claim(TestAgent.assertEqual).is_callable)
        self.assertIsNotDeficiency(self.agent.claim(helpers.function_example).is_callable)
        self.assertIsNotDeficiency(self.agent.claim(lambda: "hello world").is_callable)
        self.assertIsDeficiency(self.agent.claim("hello world").is_callable)
        self.assertIsDeficiency(self.agent.claim(5).is_callable)
        self.assertIsDeficiency(self.agent.claim(False).is_callable)
        self.assertIsDeficiency(self.agent.claim(None).is_callable)
        self.assertIsDeficiency(self.agent.claim(2.32).is_callable)
        self.assertIsNotDeficiency(self.agent.claim(helpers.TruthyClass).is_callable)
        self.assertIsDeficiency(self.agent.claim(helpers.TruthyClass("huh")).is_callable)
        self.assertIsNotDeficiency(self.agent.claim(helpers.CallableClass()).is_callable)

    def test_is_equal_to(self):
        self.assertIsNotDeficiency(self.agent.claim(5).is_equal_to, 5)
        self.assertIsDeficiency(self.agent.claim(5).is_equal_to, "5")
        self.assertIsDeficiency(self.agent.claim("").is_equal_to, False)
        self.assertIsDeficiency(self.agent.claim("").is_equal_to, 0)

    def test_if_not_none(self):
        self.assertIsDeficiency(self.agent.claim("five").if_not_none().is_type, int)
        self.assertIsNotDeficiency(self.agent.claim(None).if_not_none().is_type, int)

    def test_if_is_type(self):
        self.assertIsDeficiency(self.agent.claim("five").if_is_type(str).is_equal_to, 5)
        self.assertIsNotDeficiency(self.agent.claim("five").if_is_type(int).is_equal_to, 5)

    def test_contains(self):
        self.assertIsNotDeficiency(self.agent.claim({"one": 1}).contains, "one")
        self.assertIsDeficiency(self.agent.claim({"one": 1}).contains, 1)
        self.assertIsDeficiency(self.agent.claim({}).contains, "one")
        self.assertIsNotDeficiency(self.agent.claim(["one"]).contains, "one")
        self.assertIsDeficiency(self.agent.claim([1, 1, 1, 1, 2]).contains, "one")
        self.assertIsDeficiency(self.agent.claim([]).contains, "one")

    def test_raises(self):
        self.assertIsDeficiency(self.agent.claim(int).raises, ValueError, "1")
        self.assertIsNotDeficiency(self.agent.claim(int).raises, ValueError, "one")
