# StorePulse AI — Alert Deduplicator & State Machine
# Developer: Omkar Gurav
# Prevents continuous snapshot spamming using alert fingerprints and cooldown windows

import time
import threading
from typing import Dict, Tuple, Optional, Set

class AlertDeduplicator:
    """
    Maintains alert lifecycle state and enforces fingerprint cooldowns.
    
    Fingerprint structure:
    `{alert_type}:{store_id}:{zone_id}`
    """

    def __init__(self, default_cooldown_seconds: float = 30.0):
        self.default_cooldown_seconds = default_cooldown_seconds
        self._lock = threading.Lock()
        # fingerprint -> last_triggered_time
        self._last_triggered: Dict[str, float] = {}
        # fingerprint -> current_active_alert_id
        self._active_alert_ids: Dict[str, str] = {}

    def should_trigger(
        self,
        fingerprint: str,
        cooldown_seconds: Optional[float] = None
    ) -> Tuple[bool, Optional[str]]:
        """
        Determine if an alert event should trigger a new record and snapshot.

        Returns:
            (should_trigger: bool, existing_alert_id: Optional[str])
            - If should_trigger is True and existing_alert_id is None -> New alert event.
            - If should_trigger is True and existing_alert_id is set -> Cooldown refreshed snapshot.
            - If should_trigger is False -> Suppressed duplicate within cooldown window.
        """
        cooldown = cooldown_seconds if cooldown_seconds is not None else self.default_cooldown_seconds
        now = time.time()

        with self._lock:
            if fingerprint not in self._active_alert_ids:
                # Brand new alert
                return True, None

            last_time = self._last_triggered.get(fingerprint, 0.0)
            existing_id = self._active_alert_ids.get(fingerprint)

            if (now - last_time) >= cooldown:
                # Cooldown expired while condition continues
                return True, existing_id

            # Still active within cooldown window -> suppress duplicate
            return False, existing_id

    def record_trigger(self, fingerprint: str, alert_id: str):
        """Record that an alert has been triggered."""
        with self._lock:
            self._last_triggered[fingerprint] = time.time()
            self._active_alert_ids[fingerprint] = alert_id

    def resolve(self, fingerprint: str) -> Optional[str]:
        """Mark an alert condition as resolved and return its alert_id."""
        with self._lock:
            active_id = self._active_alert_ids.pop(fingerprint, None)
            self._last_triggered.pop(fingerprint, None)
            return active_id

    def is_active(self, fingerprint: str) -> bool:
        """Check if an alert fingerprint is currently active."""
        with self._lock:
            return fingerprint in self._active_alert_ids

    def get_active_fingerprints(self) -> Set[str]:
        """Return all currently active fingerprints."""
        with self._lock:
            return set(self._active_alert_ids.keys())

    def reset(self):
        """Reset deduplication state."""
        with self._lock:
            self._last_triggered.clear()
            self._active_alert_ids.clear()

# Global instance
deduplicator = AlertDeduplicator()
