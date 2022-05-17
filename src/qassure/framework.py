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


class Severity(enum.IntEnum):
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
    """ Manages the audit report, which is a list of tuples. Wraps the list but changes ``append()`` to work better for
        this purpose.
     """

    def __init__(self):
        """ Constructor"""
        self.report_items = []

    def __len__(self):
        return len(self.report_items)

    def __getitem__(self, k):
        return self.report_items[k]

    def __iter__(self):
        return iter(self.report_items)

    def append(self, severity, message, source):
        """ Appends a report to the report list

        :param severity: The severity to report the error as
        :type severity: qassure.framework.Severity
        :param message: The message related to the error
        :type message: str
        :param source: The source of the error
        :type source: str
        """
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
        """ Adds an item to the report. Mostly intended to be used from ``qassure.framework.ValueInspector`` to report
            on deficiencies.

        :param severity: The severity to log as
        :type severity: qassure.framework.Severity
        :param message: The message to log
        :type message: str
        :param last_frame: Optional. If provided, it should be the most relevant frame to tracing where the error was
            raised
        :type last_frame: traceback.FrameSummary
        """
        source = "Unknown"
        if last_frame:
            source = "File \"{}\", line {}, in {}: {}".format(
                last_frame.filename,
                last_frame.lineno,
                last_frame.name,
                last_frame.line
            )
        self.report.append(severity, message, source)

    def claim(self, value, severity: Severity = Severity.ERROR, object_name=None):
        """ Retrieves a ValueInspector object that can be used to make claims about a value::

        :param value: The value to make claims about
        :type value: any
        :param severity: The severity of failing those claims
        :type severity: qassure.framework.Severity
        :param object_name: A name to use for the object in error message. If not provided, one will attempt to be loaded from the stack trace.
        :return: A class to use for making claims about the value.
        :rtype: qassure.framework.ClaimInspector
        """
        if object_name is None:
            object_name = "[provided value]"
            stack = traceback.extract_stack()
            stack.reverse()
            for frame in stack:
                if hasattr(Auditor, frame.name):
                    continue
                test_object_name = self._parse_frame_line_for_arg(frame.line)
                if test_object_name:
                    object_name = "[{}]".format(test_object_name)
                break
        return ClaimInspector(self, severity, value, object_name)

    def _parse_frame_line_for_arg(self, line):
        """ Helper method to extract the first argument from a method call on a Python line from a stack trace."""
        # No method call is on the line
        if "(" not in line:
            return None     # pragma: no cover
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
        """ Runs the audit if it hasn't already been run.

            The main purpose of this approach is to allow claims to raise
            :class:`qassure.framework.BlockingDeficiencyError` when appropriate so that the audit ends gracefully.
        """
        if not self.qa_run_flag:
            try:
                self.audit()
            except BlockingDeficiencyError:
                self.is_blocked = True

    @abc.abstractmethod
    def audit(self):
        """ Subclasses should implement this with their own testing methods. """
        pass     # pragma: no cover


class ClaimInspector:
    """  Responsible for making claims about a value

        :param agent: The agent managing the report
        :type agent: qassure.framework.Auditor
        :param error_level: The severity of any deficiencies.
        :type error_level: qassure.framework.Severity
        :param value: The value to inspect
        :type value: any
        :param object_name: A useful value to show in error messages, defaults to [provided value]
        :type object_name: str
    """

    def __init__(self, agent: Auditor, error_level: Severity, value: t.Any, object_name=None):
        """ Constructor """
        self.agent = agent
        self.error_level = error_level
        self.value = value
        self.object_name = object_name if object_name else "[provided value]"

    def _report_deficiency(self, msg):
        """ Reports a deficiency to the audit report

        :param msg: The message to send
        :type msg: str
        :raises qassure.framework.BlockingDeficiencyError: If the severity was set to ``BLOCKER``.
        """
        stack = traceback.extract_stack()
        stack.reverse()
        last_frame = None
        for frame in stack:
            # Skip the internal stuff within ValueInspector
            if hasattr(ClaimInspector, frame.name) or frame.name.startswith("__"):
                continue     # pragma: no cover
            last_frame = frame
            break
        self.agent.add_report_item(self.error_level, msg, last_frame)
        if self.error_level == Severity.BLOCKER:
            raise BlockingDeficiencyError()

    def is_truthy(self, msg=None):
        """ Checks if the value is truthy

        :param msg: The message to set if the claim is false, or None to use the default
        :type msg: str
        """
        if not self.value:
            msg = msg or "{} is not truthy, should be".format(self.object_name)
            self._report_deficiency(msg)
        return self

    def is_none(self, msg=None):
        """ Checks if the value is None.

        :param msg: The message to set if the claim is false, or None to use the default
        :type msg: str
        """
        if self.value is not None:
            msg = msg or "{} is not none, should be".format(self.object_name)
            self._report_deficiency(msg)
        return self

    def is_not_none(self, msg=None):
        """ Checks if the value is not None.

        :param msg: The message to set if the claim is false, or None to use the default
        :type msg: str
        """
        if self.value is None:
            msg = msg or "{} is None, should not be".format(self.object_name)
            self._report_deficiency(msg)
        return self

    def is_type(self, cls: type, msg=None):
        """ Checks if the value is an instance of a type, using isinstance().

        :param cls: The type to check against
        :type cls: type
        :param msg: The message to set if the claim is false, or None to use the default
        :type msg: str
        """
        if not isinstance(self.value, cls):
            msg = msg or "{} is not an instance of {}".format(self.object_name, cls)
            self._report_deficiency(msg)
        return self

    def is_callable(self, msg=None):
        """ Checks if the value is callable, using callable()

        :param msg: The message to set if the claim is false, or None to use the default
        :type msg: str
        """
        if not callable(self.value):
            msg = msg or "{} is not callable".format(self.object_name)
            self._report_deficiency(msg)
        return self

    def is_equal_to(self, value, msg=None):
        """ Checks if the value is None.

        :param value: The value to check against
        :type value: any
        :param msg: The message to set if the claim is false, or None to use the default
        :type msg: str
        """
        if not self.value == value:
            msg = msg or "{} is not equal to {}".format(self.object_name, value)
            self._report_deficiency(msg)
        return self

    def if_not_none(self):
        """ Only continue checking claims if the value is not None """
        if self.value is None:
            return NoOpInspector()
        return self

    def if_is_type(self, cls: type):
        """ Only continue checking claims if the value is an instance of the given type.

        :param cls: The type to check against
        :type cls: type
        """
        if not isinstance(self.value, cls):
            return NoOpInspector()
        return self

    def contains(self, value, msg=None):
        """ Checks that the value contains another value

        :param value: The value to check is in self.value
        :type value: any
        :param msg: The message to set if the claim is false, or None to use the default
        :type msg: str
        """
        if value not in self.value:
            msg = msg or "{} does not contain value {}".format(self.object_name, value)
            self._report_deficiency(msg)
        return self

    def raises(self, exception_type: type, *args, msg=None, **kwargs):
        """ Checks that calling the value with the given args and kwargs raises the given exception.

        :param exception_type: The type of exception that should be raised.
        :type type: Exception
        :param msg: The message to set if the claim is false, or None to use the default
        :type msg: str
        """
        msg = msg or "{} does not raise exception {}".format(self.object_name, exception_type)
        try:
            self.value(*args, **kwargs)
            self._report_deficiency(msg)
        except exception_type as ex:
            pass
        return self


class NoOpInspector:
    """ For use with the ``if_*()`` methods, this is a version of :class:`qassure.framework.ClaimInspector` that doesn't
        report any errors ever. Returned if an ``if_*()`` method is not true. """

    def __init__(self):
        pass

    def __getattr__(self, item):
        return self

    def __call__(self, *args, **kwargs):
        return self
