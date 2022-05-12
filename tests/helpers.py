from qassure import Auditor


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

