#!/usr/bin/env python3
"""Publish CTest failures as check annotations.

Workflow job logs need repository admin rights to download, even in a public
repository. Annotations do not, so a failed run can still be diagnosed from the
public API: this prints one ::error annotation per failed test with the output
CTest captured for it in LastTest.log.
"""
import re
import sys
from pathlib import Path

MAX_TESTS = 4
MAX_CHARS = 6000


def escape(text):
    # The workflow command escapes: percent, carriage return and newline.
    return text.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")


def failed_tests(log):
    at = log.rfind("The following tests FAILED:")
    if at < 0:
        return []
    names = []
    for line in log[at:].splitlines()[1:]:
        if not line.strip():
            if names:
                break
            continue
        if line.startswith("Errors while running CTest"):
            break
        match = re.match(r"\s*\d+\s+-\s+(\S+)", line)
        if match:
            names.append(match.group(1))
    return names


def test_output(log, name):
    # Each entry starts with "<n>/<total> Testing: <name>" and ends at the next one.
    match = re.search(r"^\d+/\d+ Testing: " + re.escape(name) + r"\s*$", log, re.M)
    if not match:
        return ""
    rest = log[match.end():]
    following = re.search(r"^\d+/\d+ Testing: ", rest, re.M)
    if following:
        rest = rest[: following.start()]
    output = rest.find("Output:")
    if output >= 0:
        rest = rest[output + len("Output:"):]
    return rest.strip("-\n ")[:MAX_CHARS]


def main():
    log = Path(sys.argv[1]).read_text(errors="replace")
    names = failed_tests(log)
    if not names:
        print("::error title=CTest::No test failure summary in " + sys.argv[1])
        return 1
    for name in names[:MAX_TESTS]:
        print(f"::error title=CTest {name}::{escape(test_output(log, name) or name)}")
    if len(names) > MAX_TESTS:
        print("::error title=CTest failures::" + escape(", ".join(names[MAX_TESTS:])))
    return 0


if __name__ == "__main__":
    sys.exit(main())
