Usage
=====

This package provides a framework that audits data according to a given specification and returns a report.

As an example, let's consider a python application which creates meteorological reports in CSV format. We want
to verify the CSV files before they are distributed to the public and provide a report on any issues so that
they can be addressed. This tool provides a framework for doing so in an easy-to-read fashion.

Audit Creation
--------------
Creating an audit is much like creating a test case, with a few small differences. Most implementations will
override the constructor to provide a piece of data to test and the ``audit()`` method to provide the tests.
All tests are done using the ``ClaimInspector`` which is created by calling ``claim()``.

The ``claim()`` method takes a value which we will make claims about using various methods. However, it also
takes an optional ``Severity`` which informs the system how bad the deficiency is if any of the tests fail.
These severities and their suggested interpretations are:

BLOCKER
    If the claim is False, then we prevent further execution of the audit. This should mostly be used if the
    claim failing means the rest of the audit may not providing any meaningful results. For example, if a CSV
    file cannot be parsed as a CSV file, this means we cannot inspect the contents. Any exceptions that are
    raised are considered blocking errors.

CRITICAL
    If the claim is False, this is a major deal-breaker about the structure but the audit can continue. For
    example, if a CSV file requires a specific column but this column is not present, this may be a CRITICAL
    error.

ERROR
    The default value, this is used for any major errors that should probably be addressed about the data before
    it is considered valid. For example, if a CSV file is missing certain dates that should be included, this may
    be a simple ERROR.

WARNING
    If the claim is False, this level suggests that it is a deficiency that may or may not need to be corrected.
    For example, if a value is NULL that probably shouldn't be NULL, but the data format allows it to be so, this
    would be a WARNING.

For example, our hypothetical meteorological data file might have an audit that looks something like this::

    from qassure import Auditor, Severity
    import csv
    import os

    class WeatherDataAuditor(Auditor):

        def __init__(self, csv_path):
            self.csv_path = csv_path

        def audit(self):
            self.claim(os.path.exists(self.csv_path), Severity.BLOCKER).is_true("File does not exist")
            with open(self.csv_path, "r") as handle:
                reader = csv.reader(handle)
                header = None
                for line in reader:
                    if header is None:
                        header = line
                        self.claim(header).equals(["Station", "Temperature (K)"], "Invalid header")
                    else:
                        self.claim(len(line)).equals(2, "Missing temperature data")
                        if len(line) == 2:
                            self.claim(line[1].isdigit()).is_true("Temperature is not an integer")

This example will check to make sure the CSV file exists and is parsable as a CSV, then proceeds to check that the
proper header is in place and that every line contains two elements, the second of which is an integer.

