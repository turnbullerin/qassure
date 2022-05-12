import enum
import typing as t
import traceback


class Severity(enum.Enum):

    BLOCKER = 50
    CRITICAL = 40
    ERROR = 30
    WARNING = 20
    INFO = 10


class BlockingDeficiencyError(Exception):
    pass


class Agent:

    def __init__(self):
        self.report = []
        self.qa_run_flag = False
        self.is_blocked = False

    def get_deficiency_report(self):
        self.run_audit()
        return self.report

    def add_report_item(self, severity: Severity, message: str, last_frame: traceback.FrameSummary = None):
        source = "Unknown"
        if last_frame:
            source = "File \"{}\", line {}, in {}: {}".format(
                last_frame.filename,
                last_frame.lineno,
                last_frame.name,
                last_frame.line
            )
        self.report.append((severity, message, source))

    def inspect(self, value, severity: Severity = Severity.ERROR, object_name=None):
        stack = traceback.extract_stack()
        stack.reverse()
        if object_name is None:
            object_name = "[provided value]"
            for frame in stack:
                if hasattr(Agent, frame.name):
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

    def audit(self):
        pass


class ValueInspector:

    def __init__(self, agent: Agent, error_level: Severity, value: t.Any, object_name=None):
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

    def is_equal_to(self, value, msg=None):
        if not self.value == value:
            msg = msg or "{} is not equal to {}".format(self.object_name, value)
            self.report_deficiency(msg)

    def if_not_none(self):
        if self.value is None:
            return NoOpInspector()
        return self

    def if_is_type(self, cls: type):
        if not isinstance(self.value, cls):
            return NoOpInspector()
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


class Brain(Agent):

    def get_value(self, txt=None):
        return None

    def stuff(self):
        self.inspect("None", Severity.CRITICAL).is_none()
