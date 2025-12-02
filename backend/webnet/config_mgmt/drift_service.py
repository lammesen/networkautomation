"""Service for configuration drift detection and analysis."""

import difflib
import logging
from typing import Optional

from django.utils import timezone

from webnet.config_mgmt.models import ConfigSnapshot, ConfigDrift, DriftAlert
from webnet.users.models import User

logger = logging.getLogger(__name__)


class DriftService:
    """Service for detecting and analyzing configuration drift."""

    def detect_drift(
        self,
        snapshot_from: ConfigSnapshot,
        snapshot_to: ConfigSnapshot,
        user: Optional[User] = None,
    ) -> ConfigDrift:
        """Detect drift between two snapshots.

        Args:
            snapshot_from: Earlier snapshot
            snapshot_to: Later snapshot
            user: User who triggered the backup (optional)

        Returns:
            ConfigDrift object with analysis results
        """
        # Check if drift already exists
        existing = ConfigDrift.objects.filter(
            snapshot_from=snapshot_from, snapshot_to=snapshot_to
        ).first()
        if existing:
            return existing

        # Calculate diff
        diff_lines = list(
            difflib.unified_diff(
                snapshot_from.config_text.splitlines(),
                snapshot_to.config_text.splitlines(),
                lineterm="",
            )
        )

        # Count changes
        additions = sum(
            1 for line in diff_lines if line.startswith("+") and not line.startswith("+++")
        )
        deletions = sum(
            1 for line in diff_lines if line.startswith("-") and not line.startswith("---")
        )
        total_lines = len(diff_lines)
        has_changes = additions > 0 or deletions > 0

        # Generate summary
        diff_summary = self._generate_summary(diff_lines)

        # Create drift record
        drift = ConfigDrift.objects.create(
            device=snapshot_to.device,
            snapshot_from=snapshot_from,
            snapshot_to=snapshot_to,
            additions=additions,
            deletions=deletions,
            changes=additions + deletions,
            total_lines=total_lines,
            has_changes=has_changes,
            diff_summary=diff_summary,
            triggered_by=user,
        )

        # Send ChatOps notification if drift detected
        if has_changes:
            try:
                from webnet.chatops.slack_service import notify_drift_detected
                from webnet.chatops.teams_service import notify_drift_detected_teams

                notify_drift_detected(drift)
                notify_drift_detected_teams(drift)
            except Exception as e:
                logger.warning(f"Failed to send drift notification: {e}")

        return drift

    def detect_consecutive_drifts(
        self, device_id: int, user: Optional[User] = None
    ) -> list[ConfigDrift]:
        """Detect drift for consecutive snapshots of a device.

        Args:
            device_id: Device ID to analyze
            user: User who triggered the analysis

        Returns:
            List of ConfigDrift objects
        """
        snapshots = list(ConfigSnapshot.objects.filter(device_id=device_id).order_by("created_at"))

        drifts = []
        for i in range(len(snapshots) - 1):
            drift = self.detect_drift(snapshots[i], snapshots[i + 1], user)
            drifts.append(drift)

        return drifts

    def analyze_drift_for_alert(
        self, drift: ConfigDrift, threshold: int = 50
    ) -> Optional[DriftAlert]:
        """Analyze drift and create alert if changes exceed threshold.

        Args:
            drift: ConfigDrift to analyze
            threshold: Number of changes to trigger an alert

        Returns:
            DriftAlert if created, None otherwise
        """
        if not drift.has_changes:
            return None

        # Determine severity based on change magnitude
        total_changes = drift.additions + drift.deletions
        if total_changes >= threshold * 2:
            severity = "critical"
            message = f"Critical configuration drift detected on {drift.device.hostname}: {total_changes} lines changed"
        elif total_changes >= threshold:
            severity = "warning"
            message = f"Significant configuration drift detected on {drift.device.hostname}: {total_changes} lines changed"
        else:
            # Don't create alert for minor changes
            return None

        # Check if alert already exists
        existing = DriftAlert.objects.filter(drift=drift).first()
        if existing:
            return existing

        # Create alert
        alert = DriftAlert.objects.create(
            drift=drift,
            severity=severity,
            status="open",
            message=message,
        )

        return alert

    def _generate_summary(self, diff_lines: list[str]) -> str:
        """Generate a human-readable summary of changes.

        Args:
            diff_lines: List of unified diff lines

        Returns:
            Summary string
        """
        if not diff_lines:
            return "No changes detected"

        # Extract changed sections
        sections = []
        current_section = None

        for line in diff_lines:
            # Look for section headers (common in network configs)
            if line.startswith("@@"):
                if current_section:
                    sections.append(current_section)
                current_section = line
            elif line.startswith(("+", "-")) and not line.startswith(("+++", "---")):
                # Track actual changes
                if current_section and "interface " in line.lower():
                    sections.append(f"Interface configuration changed: {line[1:].strip()}")
                elif current_section and "hostname " in line.lower():
                    sections.append(f"Hostname changed: {line[1:].strip()}")
                elif current_section and "ip address " in line.lower():
                    sections.append(f"IP address changed: {line[1:].strip()}")

        if not sections:
            return "Configuration lines modified"

        return "; ".join(sections[:5])  # Limit to first 5 changes

    def get_drift_timeline(self, device_id: int, days: int = 30) -> list[ConfigDrift]:
        """Get drift timeline for a device.

        Args:
            device_id: Device ID
            days: Number of days to look back

        Returns:
            List of ConfigDrift objects
        """
        from datetime import timedelta

        cutoff = timezone.now() - timedelta(days=days)
        return list(
            ConfigDrift.objects.filter(device_id=device_id, detected_at__gte=cutoff)
            .select_related("snapshot_from", "snapshot_to", "triggered_by")
            .order_by("-detected_at")
        )

    def get_change_frequency(self, device_id: int, days: int = 30) -> dict[str, int]:
        """Calculate change frequency for a device.

        Args:
            device_id: Device ID
            days: Number of days to analyze

        Returns:
            Dictionary with change statistics
        """
        from datetime import timedelta

        cutoff = timezone.now() - timedelta(days=days)
        drifts = ConfigDrift.objects.filter(
            device_id=device_id, detected_at__gte=cutoff, has_changes=True
        )

        total_drifts = drifts.count()
        total_additions = sum(d.additions for d in drifts)
        total_deletions = sum(d.deletions for d in drifts)

        return {
            "total_changes": total_drifts,
            "total_additions": total_additions,
            "total_deletions": total_deletions,
            "avg_changes_per_drift": (
                (total_additions + total_deletions) / total_drifts if total_drifts > 0 else 0
            ),
            "days_analyzed": days,
        }
