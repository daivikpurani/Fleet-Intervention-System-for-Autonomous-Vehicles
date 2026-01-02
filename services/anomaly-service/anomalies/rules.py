"""Threshold rules for anomaly detection.

Rules are dataset-grounded and use robust statistics (percentiles) from sample.zarr.
Thresholds should be computed from the dataset and set as constants.
"""

import logging
from typing import Dict, List, Optional

from services.schemas.events import RawTelemetryEvent

from .severity import CRITICAL, INFO, WARNING

logger = logging.getLogger(__name__)

# Default thresholds (fallback if not loaded from config)
DEFAULT_DECELERATION_WARNING = -3.0
DEFAULT_DECELERATION_CRITICAL = -5.0
DEFAULT_CENTROID_JUMP_WARNING = 5.0
DEFAULT_CENTROID_JUMP_CRITICAL = 10.0
DEFAULT_VELOCITY_SPIKE_WARNING = 10.0
DEFAULT_VELOCITY_SPIKE_CRITICAL = 20.0
DEFAULT_LABEL_INSTABILITY_WARNING = 0.3
DEFAULT_LABEL_INSTABILITY_CRITICAL = 0.5
DEFAULT_AGENT_COUNT_DROP_WARNING = 5
DEFAULT_MISSING_FRAMES_THRESHOLD = 3


class AnomalyResult:
    """Result of anomaly rule evaluation."""

    def __init__(
        self,
        triggered: bool,
        rule_name: str,
        severity: str,
        features: Dict,
        thresholds: Dict,
        explanation: str,
    ):
        """Initialize anomaly result.

        Args:
            triggered: Whether anomaly was detected
            rule_name: Name of the rule
            severity: Severity level (INFO, WARNING, CRITICAL)
            features: Feature values used in detection
            thresholds: Threshold values used
            explanation: Human-readable explanation
        """
        self.triggered = triggered
        self.rule_name = rule_name
        self.severity = severity
        self.features = features
        self.thresholds = thresholds
        self.explanation = explanation


class SuddenDecelerationRule:
    """Rule for detecting sudden deceleration.

    Triggered by large negative acceleration.
    Uses event-time windowing.
    Applies to both ego and agents.
    """

    def __init__(self, thresholds: Optional[Dict] = None):
        """Initialize rule with thresholds.

        Args:
            thresholds: Dictionary of thresholds from config
        """
        if thresholds is None:
            thresholds = {}
        
        decel_thresholds = thresholds.get("sudden_deceleration", {})
        self.warning_threshold = decel_thresholds.get(
            "warning", DEFAULT_DECELERATION_WARNING
        )
        self.critical_threshold = decel_thresholds.get(
            "critical", DEFAULT_DECELERATION_CRITICAL
        )

    def evaluate(
        self, event: RawTelemetryEvent, features: Dict, frames: List
    ) -> AnomalyResult:
        """Evaluate sudden deceleration rule.

        Args:
            event: Current telemetry event
            features: Extracted features
            frames: Telemetry frames from ring buffer

        Returns:
            AnomalyResult
        """
        acceleration = features.get("acceleration")

        if acceleration is None:
            return AnomalyResult(
                triggered=False,
                rule_name="sudden_deceleration",
                severity=WARNING,
                features={},
                thresholds={},
                explanation="Insufficient history for acceleration calculation",
            )

        # Check for sudden deceleration
        if acceleration <= self.critical_threshold:
            severity = CRITICAL
            explanation = f"Critical sudden deceleration: {acceleration:.2f} m/s²"
        elif acceleration <= self.warning_threshold:
            severity = WARNING
            explanation = f"Warning sudden deceleration: {acceleration:.2f} m/s²"
        else:
            return AnomalyResult(
                triggered=False,
                rule_name="sudden_deceleration",
                severity=WARNING,
                features={},
                thresholds={},
                explanation="No deceleration anomaly detected",
            )

        return AnomalyResult(
            triggered=True,
            rule_name="sudden_deceleration",
            severity=severity,
            features={
                "acceleration": acceleration,
                "speed": event.speed,
                "velocity": event.velocity,
            },
            thresholds={
                "deceleration_threshold_warning": self.warning_threshold,
                "deceleration_threshold_critical": self.critical_threshold,
            },
            explanation=explanation,
        )


class PerceptionInstabilityRule:
    """Rule for detecting perception instability.

    Checks for:
    - Track continuity gaps
    - Implausible centroid jumps
    - Velocity spikes beyond robust thresholds
    - Label probability instability (if available)
    """

    def __init__(self, thresholds: Optional[Dict] = None):
        """Initialize rule with thresholds.

        Args:
            thresholds: Dictionary of thresholds from config
        """
        if thresholds is None:
            thresholds = {}
        
        centroid_thresholds = thresholds.get("centroid_jump", {})
        self.centroid_jump_warning = centroid_thresholds.get(
            "warning", DEFAULT_CENTROID_JUMP_WARNING
        )
        self.centroid_jump_critical = centroid_thresholds.get(
            "critical", DEFAULT_CENTROID_JUMP_CRITICAL
        )
        
        velocity_thresholds = thresholds.get("velocity_spike", {})
        self.velocity_spike_warning = velocity_thresholds.get(
            "warning", DEFAULT_VELOCITY_SPIKE_WARNING
        )
        self.velocity_spike_critical = velocity_thresholds.get(
            "critical", DEFAULT_VELOCITY_SPIKE_CRITICAL
        )
        
        label_thresholds = thresholds.get("label_instability", {})
        self.label_instability_warning = label_thresholds.get(
            "warning", DEFAULT_LABEL_INSTABILITY_WARNING
        )
        self.label_instability_critical = label_thresholds.get(
            "critical", DEFAULT_LABEL_INSTABILITY_CRITICAL
        )

    def evaluate(
        self, event: RawTelemetryEvent, features: Dict, frames: List
    ) -> AnomalyResult:
        """Evaluate perception instability rule.

        Args:
            event: Current telemetry event
            features: Extracted features
            frames: Telemetry frames from ring buffer

        Returns:
            AnomalyResult
        """
        triggered = False
        triggers = []
        feature_values = {}
        threshold_values = {}
        has_critical = False

        # Check for implausible centroid jumps
        centroid_displacement = features.get("centroid_displacement")
        if centroid_displacement is not None:
            feature_values["centroid_displacement"] = centroid_displacement
            threshold_values["centroid_jump_warning"] = self.centroid_jump_warning
            threshold_values["centroid_jump_critical"] = self.centroid_jump_critical

            if centroid_displacement > self.centroid_jump_warning:
                triggered = True
                is_critical = centroid_displacement > self.centroid_jump_critical
                if is_critical:
                    has_critical = True
                severity_level = CRITICAL if is_critical else WARNING
                triggers.append(
                    f"Implausible centroid jump: {centroid_displacement:.2f} m ({severity_level})"
                )

        # Check for velocity spikes
        if len(frames) >= 2:
            prev_frame = frames[-2]
            curr_frame = frames[-1]

            prev_speed = prev_frame.speed
            curr_speed = curr_frame.speed
            speed_change = abs(curr_speed - prev_speed)

            feature_values["speed_change"] = speed_change
            threshold_values["velocity_spike_warning"] = self.velocity_spike_warning
            threshold_values["velocity_spike_critical"] = self.velocity_spike_critical

            if speed_change > self.velocity_spike_warning:
                triggered = True
                is_critical = speed_change > self.velocity_spike_critical
                if is_critical:
                    has_critical = True
                severity_level = CRITICAL if is_critical else WARNING
                triggers.append(
                    f"Velocity spike: {speed_change:.2f} m/s change ({severity_level})"
                )

        # Check for label probability instability
        if event.label_probabilities is not None and len(frames) >= 2:
            prev_frame = frames[-2]
            if prev_frame.label_probabilities is not None:
                prev_max_prob = max(prev_frame.label_probabilities)
                curr_max_prob = max(event.label_probabilities)
                prob_change = abs(curr_max_prob - prev_max_prob)

                feature_values["label_probability_change"] = prob_change
                threshold_values["label_instability_warning"] = self.label_instability_warning
                threshold_values["label_instability_critical"] = self.label_instability_critical

                if prob_change > self.label_instability_warning:
                    triggered = True
                    is_critical = prob_change > self.label_instability_critical
                    if is_critical:
                        has_critical = True
                    severity_level = CRITICAL if is_critical else WARNING
                    triggers.append(
                        f"Label probability instability: {prob_change:.3f} change ({severity_level})"
                    )

        if not triggered:
            return AnomalyResult(
                triggered=False,
                rule_name="perception_instability",
                severity=WARNING,
                features={},
                thresholds={},
                explanation="No perception instability detected",
            )

        # Determine severity: CRITICAL if any trigger is critical or multiple triggers
        if has_critical or len(triggers) >= 2:
            severity = CRITICAL
        else:
            severity = WARNING

        return AnomalyResult(
            triggered=True,
            rule_name="perception_instability",
            severity=severity,
            features=feature_values,
            thresholds=threshold_values,
            explanation="; ".join(triggers),
        )


class DropoutProxyRule:
    """Rule for detecting dropout proxy.

    Explicitly labeled as a proxy, not sensor failure.
    Checks for:
    - Sudden drop in active agent count
    - Missing frames across many vehicles
    """

    def __init__(self, thresholds: Optional[Dict] = None):
        """Initialize rule with thresholds.

        Args:
            thresholds: Dictionary of thresholds from config
        """
        if thresholds is None:
            thresholds = {}
        
        dropout_thresholds = thresholds.get("dropout_proxy", {})
        self.agent_count_drop_warning = dropout_thresholds.get(
            "agent_count_drop_warning", DEFAULT_AGENT_COUNT_DROP_WARNING
        )
        self.missing_frames_threshold = DEFAULT_MISSING_FRAMES_THRESHOLD

    def evaluate(
        self,
        event: RawTelemetryEvent,
        features: Dict,
        frames: List,
        active_agent_count: Optional[int],
        prev_active_agent_count: Optional[int],
    ) -> AnomalyResult:
        """Evaluate dropout proxy rule.

        Args:
            event: Current telemetry event
            features: Extracted features
            frames: Telemetry frames from ring buffer
            active_agent_count: Current active agent count
            prev_active_agent_count: Previous active agent count

        Returns:
            AnomalyResult
        """
        triggered = False
        triggers = []
        feature_values = {}
        threshold_values = {}

        # Check for sudden drop in active agent count
        if (
            active_agent_count is not None
            and prev_active_agent_count is not None
        ):
            agent_count_drop = prev_active_agent_count - active_agent_count

            feature_values["active_agent_count"] = active_agent_count
            feature_values["prev_active_agent_count"] = prev_active_agent_count
            feature_values["agent_count_drop"] = agent_count_drop
            threshold_values[
                "agent_count_drop_warning"
            ] = self.agent_count_drop_warning

            if agent_count_drop >= self.agent_count_drop_warning:
                triggered = True
                triggers.append(
                    f"Sudden drop in active agent count: {agent_count_drop} agents"
                )

        # Check for missing frames (track continuity gaps)
        if len(frames) >= 2:
            prev_frame = frames[-2]
            frame_gap = event.frame_index - prev_frame.frame_index

            feature_values["frame_gap"] = frame_gap
            threshold_values["missing_frames_threshold"] = self.missing_frames_threshold

            if frame_gap > self.missing_frames_threshold:
                triggered = True
                triggers.append(
                    f"Track continuity gap: {frame_gap} frames missing"
                )

        if not triggered:
            return AnomalyResult(
                triggered=False,
                rule_name="dropout_proxy",
                severity=INFO,
                features={},
                thresholds={},
                explanation="No dropout proxy detected",
            )

        # Dropout proxy is always INFO severity (explicitly labeled as proxy)
        return AnomalyResult(
            triggered=True,
            rule_name="dropout_proxy",
            severity=INFO,
            features=feature_values,
            thresholds=threshold_values,
            explanation="Dropout proxy: " + "; ".join(triggers),
        )
