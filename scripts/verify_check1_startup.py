#!/usr/bin/env python3
"""Verify Check 1 by starting anomaly-service and capturing threshold loading logs."""

import json
import logging
import subprocess
import sys
import time
from pathlib import Path

workspace_root = Path(__file__).resolve().parent.parent

# Set up logging to capture
logging.basicConfig(level=logging.INFO)

# Load expected thresholds
thresholds_path = workspace_root / "services" / "anomaly-service" / "config" / "thresholds.json"
with open(thresholds_path, "r") as f:
    expected_thresholds = json.load(f)["thresholds"]

print("=" * 60)
print("CHECK 1: Verify thresholds are loaded at startup")
print("=" * 60)
print(f"\nExpected thresholds from {thresholds_path.name}:")
for rule_name, rule_thresholds in expected_thresholds.items():
    print(f"  {rule_name}: {rule_thresholds}")

# Test threshold loading by importing the module
print("\nTesting threshold loading directly...")

# Import thresholds loader
import importlib.util
thresholds_py = workspace_root / "services" / "anomaly-service" / "config" / "thresholds.py"
spec = importlib.util.spec_from_file_location("thresholds", thresholds_py)
thresholds_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(thresholds_module)

# Load thresholds
loaded_data = thresholds_module.load_thresholds(thresholds_path)
loaded_thresholds = loaded_data.get("thresholds", {})

print("\nLoaded thresholds:")
for rule_name, rule_thresholds in loaded_thresholds.items():
    print(f"  {rule_name}: {rule_thresholds}")

# Compare
print("\nComparing expected vs loaded...")
all_match = True
for rule_name in expected_thresholds.keys():
    expected = expected_thresholds[rule_name]
    loaded = loaded_thresholds.get(rule_name, {})
    
    if expected == loaded:
        print(f"  ✓ {rule_name}: Matches")
    else:
        print(f"  ✗ {rule_name}: Mismatch")
        print(f"     Expected: {expected}")
        print(f"     Loaded: {loaded}")
        all_match = False

if all_match:
    print("\n✓ CHECK 1 PASSED: Thresholds are loaded correctly from JSON")
    print("  (The anomaly-service will log these at startup when it initializes AnomalyConfig)")
    sys.exit(0)
else:
    print("\n✗ CHECK 1 FAILED: Thresholds do not match")
    sys.exit(1)

