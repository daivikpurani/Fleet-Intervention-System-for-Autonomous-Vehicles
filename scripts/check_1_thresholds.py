#!/usr/bin/env python3
"""Check 1: Verify thresholds are loaded at startup."""

import json
import logging
import sys
from pathlib import Path

# Add workspace root to path
workspace_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(workspace_root))

# Import using importlib to handle hyphen in directory name
import importlib.util

# First load the thresholds module
thresholds_path = workspace_root / "services" / "anomaly-service" / "config" / "thresholds.py"
spec_thresholds = importlib.util.spec_from_file_location("thresholds", thresholds_path)
thresholds_module = importlib.util.module_from_spec(spec_thresholds)
spec_thresholds.loader.exec_module(thresholds_module)

# Then load config module
config_path = workspace_root / "services" / "anomaly-service" / "config.py"
spec_config = importlib.util.spec_from_file_location("anomaly_config", config_path)
config_module = importlib.util.module_from_spec(spec_config)

# Set up the module's __package__ and import dependencies
config_module.__package__ = "services.anomaly_service"
config_module.load_thresholds = thresholds_module.load_thresholds

spec_config.loader.exec_module(config_module)

AnomalyConfig = config_module.AnomalyConfig

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Load thresholds.json
thresholds_path = workspace_root / "services" / "anomaly-service" / "config" / "thresholds.json"

if not thresholds_path.exists():
    logger.error(f"thresholds.json not found at {thresholds_path}")
    sys.exit(1)

with open(thresholds_path, "r") as f:
    threshold_data = json.load(f)

logger.info("=" * 60)
logger.info("CHECK 1: Thresholds are actually being used")
logger.info("=" * 60)
logger.info(f"\nLoaded thresholds.json:")
logger.info(f"  Dataset: {threshold_data.get('dataset_id')}")
logger.info(f"  Scenes: {threshold_data.get('golden_scene_ids')}")
logger.info(f"  Generated: {threshold_data.get('generated_at')}")

thresholds = threshold_data.get("thresholds", {})
logger.info("\nThreshold values from JSON:")
for rule_name, rule_thresholds in thresholds.items():
    logger.info(f"  {rule_name}: {rule_thresholds}")

# Now load config and check thresholds
logger.info("\nLoading AnomalyConfig...")
config = AnomalyConfig()

logger.info("\nThresholds loaded by AnomalyConfig:")
for rule_name, rule_thresholds in config.thresholds.items():
    logger.info(f"  {rule_name}: {rule_thresholds}")

# Compare
logger.info("\nComparing JSON vs Config thresholds...")
default_thresholds = {
    "sudden_deceleration": {"warning": -3.0, "critical": -5.0},
    "centroid_jump": {"warning": 5.0, "critical": 10.0},
    "velocity_spike": {"warning": 10.0, "critical": 20.0},
    "label_instability": {"warning": 0.3, "critical": 0.5},
    "dropout_proxy": {"agent_count_drop_warning": 5},
}

all_match_json = True
any_match_defaults = False

for rule_name in thresholds.keys():
    json_vals = thresholds.get(rule_name, {})
    config_vals = config.thresholds.get(rule_name, {})
    default_vals = default_thresholds.get(rule_name, {})
    
    if config_vals == default_vals:
        logger.warning(f"  ✗ {rule_name}: Matches DEFAULTS (not loaded from JSON)")
        any_match_defaults = True
        all_match_json = False
    elif config_vals == json_vals:
        logger.info(f"  ✓ {rule_name}: Matches JSON (correctly loaded)")
    else:
        logger.warning(f"  ? {rule_name}: Different from both JSON and defaults")
        logger.warning(f"     JSON: {json_vals}")
        logger.warning(f"     Config: {config_vals}")
        all_match_json = False

if all_match_json and not any_match_defaults:
    logger.info("\n✓ CHECK 1 PASSED: All thresholds match JSON (not defaults)")
    sys.exit(0)
else:
    logger.error("\n✗ CHECK 1 FAILED: Some thresholds may be using defaults")
    sys.exit(1)

