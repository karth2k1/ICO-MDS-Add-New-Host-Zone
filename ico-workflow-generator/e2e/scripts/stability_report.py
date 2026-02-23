#!/usr/bin/env python3
"""Summarize Playwright JUnit report for stability tracking."""

from __future__ import annotations

import argparse
import xml.etree.ElementTree as ET


def parse_junit(path: str) -> dict:
    tree = ET.parse(path)
    root = tree.getroot()

    tests = int(root.attrib.get("tests", 0))
    failures = int(root.attrib.get("failures", 0))
    errors = int(root.attrib.get("errors", 0))
    skipped = int(root.attrib.get("skipped", 0))
    time_sec = float(root.attrib.get("time", 0.0))

    executed = max(tests - skipped, 0)
    passed = max(executed - failures - errors, 0)
    pass_rate = (passed / executed * 100.0) if executed else 0.0

    return {
        "tests": tests,
        "executed": executed,
        "passed": passed,
        "failures": failures,
        "errors": errors,
        "skipped": skipped,
        "time_sec": time_sec,
        "pass_rate": pass_rate,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, help="Path to JUnit XML")
    args = parser.parse_args()

    metrics = parse_junit(args.input)
    print("E2E Stability Summary")
    print(f"tests={metrics['tests']}")
    print(f"executed={metrics['executed']}")
    print(f"passed={metrics['passed']}")
    print(f"failures={metrics['failures']}")
    print(f"errors={metrics['errors']}")
    print(f"skipped={metrics['skipped']}")
    print(f"time_sec={metrics['time_sec']:.2f}")
    print(f"pass_rate={metrics['pass_rate']:.2f}%")


if __name__ == "__main__":
    main()
