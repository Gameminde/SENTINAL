"""Cancellation token for mission execution.

Task 4 / Requirement 4 (F-A3.10) — reactive kill-switch interruption.

A :class:`CancellationToken` is a thread-safe flag shared between the
kill-switch subsystem and the mission runner. The runner polls
``token.is_cancelled`` between plan steps (and organ adapters SHOULD poll
it before each network I/O boundary) so that revocation takes effect
within one phase boundary on sync workers and within one event-loop tick
on async workers (see Requirement 4 / CP-4.2 Bounded Latency).

The token is intentionally tiny and dependency-free: a single
``threading.Event`` under the hood. Cancellation is idempotent.
"""

from __future__ import annotations

import threading


class CancellationToken:
    """Thread-safe, idempotent cancellation flag.

    Usage::

        token = CancellationToken()
        # producer: kill-switch subsystem
        token.cancel()
        # consumer: mission runner / organ adapter
        if token.is_cancelled:
            raise MissionRevokedException("mission_revoked: cancellation token fired.")
    """

    __slots__ = ("_event",)

    def __init__(self) -> None:
        self._event = threading.Event()

    @property
    def is_cancelled(self) -> bool:
        """True once :meth:`cancel` has been called at least once."""
        return self._event.is_set()

    def cancel(self) -> None:
        """Flip the flag. Idempotent — calling twice has no additional effect.

        Thread-safe: :class:`threading.Event.set` is guaranteed atomic
        with respect to :class:`threading.Event.is_set` so concurrent
        callers see a consistent view.
        """
        self._event.set()

    def wait(self, timeout: float | None = None) -> bool:
        """Block until cancelled or timeout. Returns ``True`` if cancelled.

        Provided for async/concurrent worker patterns; the mission runner
        itself polls :attr:`is_cancelled` synchronously between plan steps.
        """
        return self._event.wait(timeout=timeout)
