"""
Scanner integrations for STIG compliance testing.

Each scanner wraps an external tool (OpenSCAP, InSpec, cloud APIs) and
produces standardized TestResult objects that map to STIG rules.
"""

from pretorin.scanners.base import ScannerBase, TestResult, ScannerInfo

__all__ = ["ScannerBase", "TestResult", "ScannerInfo"]
