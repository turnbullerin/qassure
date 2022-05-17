from qassure import Auditor, Severity


class BaseAuditor(Auditor):

    def audit(self):
        pass


class TruthyClass:

    def __init__(self, should_be):
        self.should_be = should_be

    def __bool__(self):
        return bool(self.should_be)


def function_example():
    pass


class CallableClass:

    def __call__(self):
        return "five"


class AuditorNoFailures(Auditor):

    def audit(self):
        self.claim(1).is_truthy()
        self.claim(1, Severity.WARNING).is_truthy()
        self.claim(1, Severity.CRITICAL).is_truthy()
        self.claim(1, Severity.ERROR).is_truthy()
        self.claim(1, Severity.BLOCKER).is_truthy()


class AuditorWithWarning(Auditor):

    def audit(self):
        self.claim(1).is_truthy()
        self.claim(0, Severity.WARNING).is_truthy()
        self.claim(1, Severity.CRITICAL).is_truthy()
        self.claim(1, Severity.ERROR).is_truthy()
        self.claim(1, Severity.BLOCKER).is_truthy()
