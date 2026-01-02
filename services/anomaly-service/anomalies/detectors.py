"""Rule-based anomaly detectors.

Orchestrates evaluation of all anomaly rules.
"""

import logging
from typing import Dict, List, Optional

from services.schemas.events import RawTelemetryEvent

from .rules import (
    AnomalyResult,
    DropoutProxyRule,
    PerceptionInstabilityRule,
    SuddenDecelerationRule,
)

logger = logging.getLogger(__name__)


class AnomalyDetector:
    """Orchestrates anomaly detection using rule-based logic."""

    def __init__(self, thresholds: Optional[Dict] = None):
        """Initialize anomaly detector with rules.

        Args:
            thresholds: Dictionary of thresholds from config
        """
        self.sudden_deceleration_rule = SuddenDecelerationRule(thresholds)
        self.perception_instability_rule = PerceptionInstabilityRule(thresholds)
        self.dropout_proxy_rule = DropoutProxyRule(thresholds)

    def detect(
        self,
        event: RawTelemetryEvent,
        features: dict,
        frames: List,
        active_agent_count: Optional[int] = None,
        prev_active_agent_count: Optional[int] = None,
    ) -> List[AnomalyResult]:
        """Detect anomalies for a telemetry event.

        Args:
            event: Current telemetry event
            features: Extracted features
            frames: Telemetry frames from ring buffer
            active_agent_count: Current active agent count (for dropout proxy)
            prev_active_agent_count: Previous active agent count (for dropout proxy)

        Returns:
            List of AnomalyResult objects (only triggered anomalies)
        """
        anomalies = []

        # Evaluate sudden deceleration rule
        result = self.sudden_deceleration_rule.evaluate(event, features, frames)
        if result.triggered:
            anomalies.append(result)

        # Evaluate perception instability rule
        result = self.perception_instability_rule.evaluate(
            event, features, frames
        )
        if result.triggered:
            anomalies.append(result)

        # Evaluate dropout proxy rule
        result = self.dropout_proxy_rule.evaluate(
            event,
            features,
            frames,
            active_agent_count,
            prev_active_agent_count,
        )
        if result.triggered:
            anomalies.append(result)

        return anomalies
