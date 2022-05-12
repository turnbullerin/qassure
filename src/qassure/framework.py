"""

Provides a framework for creating quality assurance audits on digital files to ensure their integrity and reporting on
any deficiencies. For example, one might use this framework to manage the validation of files created by a script to
ensure they follow a specific format by parsing it and running the auditor on the resulting data structure.

At the core, this framework is similar to unittest or other testing frameworks. However, one key difference is that the
auditor is robust to failures; unless a failure is defined to be a blocker, the audit will continue and all deficiencies
will be reported.

"""
import enum
import typing as t
import traceback
import abc


class Severity(enum.Enum):
    """ The severity of a deficiency """

    BLOCKER = 50
    """ The audit cannot proceed because of this error. """

    CRITICAL = 40
    """ A deficiency that has a serious impact on the end-user and must be resolved"""

    ERROR = 30
    """ A deficiency that impacts the end-user and should be resolved"""

    WARNING = 20
    """ A deficiency that is less than ideal, but will not significantly impact the end-user"""

    INFO = 10
    """ This severity is for sharing messages that do not require resolution """


class BlockingDeficiencyError(Exception):
    """ Error to raise when something is blocking further auditing """
    pass


class AuditReport:

    def __init__(self):
        self.report_items = []

    def __len__(self):
        return len(self.report_items)

    def __getitem__(self, k):
        return self.report_items[k]

    def __setitem__(self, k, value):
        self.report_items[k] = value

    def __delitem__(self, k):
        del self.report_items[k]

    def __iter__(self):
        return iter(self.report_items)

    def append(self, severity, message, source):
        self.report_items.append((severity, message, source))


class Auditor(abc.ABC):
    """ Manages the audit process. This class is never instantiated directly; instead, sub-classes should be implemented
        by passing in the data to be audited in the constructor and implementing the ``audit()`` method with the tests::

            from qassure import Auditor, Severity

            class AuditDateFormatDict(Auditor):
                ''' Checks if the value is a dict with a date and format key '''

                def __init__(self, test_value):
                    self.test_value = test_value

                def audit(self):
                    # Make sure test_value is a dict. This a BLOCKER because we can't check the keys of non-dicts.
                    self.inspect(self.test_value, Severity.BLOCKER).is_instance(dict)

                    # Make sure the dict has a date key
                    self.inspect(self.test_value).does_contain("date")

                    # Make sure the dict has a format key
                    self.inspect(self.test_value).does_contain("format")

            # Will have one BLOCKER message, because it is not a dict
            auditor = AuditDateFormatDict("not a dict")

            # Will have two ERROR messages, because it is a dict but has the wrong keys
            auditor = AuditDateFormatDict({"foo": 0, "bar": 1})

            # Passes
            auditor = AuditDateFormatDict({"date": None, "format": None})

    """

    def __init__(self):
        """ Constructor """
        self.report = AuditReport()
        self.qa_run_flag = False
        self.is_blocked = False

    def get_report(self) -> AuditReport:
        """ Runs the audit if it hasn't been run and returns the report

            :returns: The audit report
            :rtype: qassure.framework.AuditReport
        """
        self.run_audit()
        return self.report

    def passed(self, max_level=Severity.WARNING):
        """ Runs the audit if it hasn't been run and returns whether any deficiencies exceed the given severity.

            :param max_level: The maximum severity level that can be encountered.
            :type max_level: qassure.framework.Severity
            :returns: Whether any errors with severity greater than ``max_level`` were encountered.
            :rtype: bool
        """
        for m in self.report:
            if m[0] > max_level:
                return False
        return True

    def add_report_item(self, severity: Severity, message: str, last_frame: traceback.FrameSummary = None):
        source = "Unknown"
        if last_frame:
            source = "File \"{}\", line {}, in {}: {}".format(
                last_frame.filename,
                last_frame.lineno,
                last_frame.name,
                last_frame.line
            )
        self.report.append(severity, message, source)

    def inspect(self, value, severity: Severity = Severity.ERROR, object_name=None):
        stack = traceback.extract_stack()
        stack.reverse()
        if object_name is None:
            object_name = "[provided value]"
            for frame in stack:
                if hasattr(Auditor, frame.name):
                    continue
                test_object_name = self._parse_frame_line_for_arg(frame.line)
                if test_object_name:
                    object_name = "[{}]".format(test_object_name)
                break
        return ValueInspector(self, severity, value, object_name)

    def _parse_frame_line_for_arg(self, line):
        if "(" not in line:
            return None
        start_at = line.find("(") + 1
        stack = [")"]
        buffer = ""
        escaped = False
        for i in range(start_at, len(line)):
            char = line[i]
            if not escaped:
                if char == stack[-1]:
                    stack = stack[:-1]
                    if not stack:
                        break
                elif char == "\"":
                    stack.append(char)
                elif char == "(":
                    stack.append(")")
            if char == "," and len(stack) == 1:
                return buffer
            buffer += char
        return buffer

    def run_audit(self):
        if not self.qa_run_flag:
            try:
                self.audit()
            except BlockingDeficiencyError:
                self.is_blocked = True

    @abc.abstractmethod
    def audit(self):
        pass


class ValueInspector:

    def __init__(self, agent: Auditor, error_level: Severity, value: t.Any, object_name=None):
        self.agent = agent
        self.error_level = error_level
        self.value = value
        self.object_name = object_name if object_name else "{provided value}"

    def report_deficiency(self, msg):
        stack = traceback.extract_stack()
        stack.reverse()
        last_frame = None
        for frame in stack:
            # Skip the internal stuff within ValueInspector
            if hasattr(ValueInspector, frame.name) or frame.name.startswith("__"):
                continue
            last_frame = frame
            break
        self.agent.add_report_item(self.error_level, msg, last_frame)
        if self.error_level == Severity.BLOCKER:
            raise BlockingDeficiencyError()

    def is_truthy(self, msg=None):
        if not self.value:
            msg = msg or "{} is not truthy, should be".format(self.object_name)
            self.report_deficiency(msg)
        return self

    def is_none(self, msg=None):
        if self.value is not None:
            msg = msg or "{} is not none, should be".format(self.object_name)
            self.report_deficiency(msg)
        return self

    def is_not_none(self, msg=None):
        if self.value is None:
            msg = msg or "{} is None, should not be".format(self.object_name)
            self.report_deficiency(msg)
        return self

    def is_type(self, cls: type, msg=None):
        if not isinstance(self.value, cls):
            msg = msg or "{} is not an instance of {}".format(self.object_name, cls)
            self.report_deficiency(msg)
        return self

    def is_callable(self, msg=None):
        if not callable(self.value):
            msg = msg or "{} is not callable".format(self.object_name)
            self.report_deficiency(msg)
        return self

    def is_equal_to(self, value, msg=None):
        if not self.value == value:
            msg = msg or "{} is not equal to {}".format(self.object_name, value)
            self.report_deficiency(msg)
        return self

    def if_not_none(self):
        if self.value is None:
            return NoOpInspector()
        return self

    def if_is_type(self, cls: type):
        if not isinstance(self.value, cls):
            return NoOpInspector()
        return self

    def does_contain(self, value, msg=None):
        if not value in self.value:
            msg = msg or "{} does not contain value {}".format(self.object_name, value)
            self.report_deficiency(msg)
        return self

    def raises(self, exception_type: type, *args, msg=None, **kwargs):
        msg = msg or "{} does not raise exception {}".format(self.object_name, exception_type)
        try:
            self.value(*args, **kwargs)
            self.report_deficiency(msg)
        except exception_type as ex:
            pass


class NoOpInspector:

    def __init__(self):
        pass

    def __getattr__(self, item):
        return self

    def __call__(self, *args, **kwargs):
        return self
