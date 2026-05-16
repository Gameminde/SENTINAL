"""Browser receipt wrapper façade (Task 5 / Wave D1.5).

This module provides a single helper,
:func:`wrap_browser_execution_receipt`, that wraps an existing legacy
browser receipt (e.g. :class:`BrowserFormSubmitReceipt`,
:class:`BrowserUploadAuthorizedReceipt`,
:class:`BrowserDownloadQuarantineReceipt`, the five advanced-authority
receipts under :class:`BrowserV3Receipt`, and any other
``SentinelModel``-derived browser receipt) into an
:class:`sentinel.organs.receipts.OrganExecutionReceipt`.

Design doctrine
---------------

1. **Composition, not inheritance.** The legacy browser receipt is
   referenced from the new :class:`OrganExecutionReceipt` via
   ``output_ref`` (carrying the legacy receipt id as a URI-shaped
   pointer ``"browser-receipt://<LegacyClassName>/<receipt_id>"``) and
   a structured ``metadata`` dict that is forwarded into
   ``output_summary``. The legacy receipt object itself is NOT
   mutated, NOT subclassed, and its ``id`` / ``receipt_hash`` (for
   v3 receipts) is NOT recomputed.

2. **Official factory only.** The wrapper calls
   :meth:`OrganExecutionReceipt.started` — the one code path that
   re-computes ``action_payload_hash`` from ``execution_action_payload``
   and raises :class:`ReceiptIntegrityError` on mismatch. The wrapper
   never constructs :class:`OrganExecutionReceipt` directly with a
   forged hash.

3. **Integrity rides the factory.** If the caller supplies an
   ``execution_action_payload`` that does not match
   ``dry_run.action_payload_hash``, the factory raises; the wrapper
   propagates that error unchanged. There is no try/except inside the
   wrapper.

4. **Minimal adapter shape.** The wrapper accepts only what the
   factory needs plus the legacy receipt. It does not introduce a new
   pydantic model for the wrapped pair — that would be its own
   schema surface to audit. Callers who want structured inspection
   can read ``execution_receipt.output_ref`` and re-fetch the legacy
   object from their own store.

This façade is the staging point for Wave D3, when the seven executor
files will start producing `OrganExecutionReceipt`-wrapped outputs via
this helper. Today (post-Wave D1.5) no executor calls the helper; it
is available for Wave D3 without requiring further API design.

See also:
    * ``tests/test_browser_receipt_wrapper.py``
    * :meth:`sentinel.organs.receipts.OrganExecutionReceipt.started`
    * :class:`sentinel.organs.dry_run.OrganDryRunReceipt`
"""

from __future__ import annotations

from typing import Any, Mapping

from pydantic import BaseModel

from sentinel.organs.authority import OrganAuthorityEnvelope
from sentinel.organs.contracts import OrganPromotionLevel
from sentinel.organs.dry_run import OrganDryRunReceipt
from sentinel.organs.kill_switch import OrganKillSwitch
from sentinel.organs.receipts import OrganExecutionReceipt
from sentinel.shared.events import EventBus


#: The URI scheme used to encode a legacy browser receipt reference in
#: :class:`OrganExecutionReceipt.output_ref`. Kept as a module-level
#: constant so downstream tests and doc generators can assert on it.
LEGACY_RECEIPT_URI_SCHEME: str = "browser-receipt"


def _legacy_receipt_uri(browser_receipt: Any) -> str:
    """Return a URI-shaped pointer for a legacy browser receipt.

    ``browser-receipt://<LegacyClassName>/<receipt_id>``
    """
    class_name = type(browser_receipt).__name__
    receipt_id = getattr(browser_receipt, "id", None)
    if not receipt_id:
        raise ValueError(
            "Legacy browser receipt must expose a non-empty `id` attribute "
            f"to be wrapped; got type={class_name!r}."
        )
    return f"{LEGACY_RECEIPT_URI_SCHEME}://{class_name}/{receipt_id}"


def _legacy_receipt_summary(
    browser_receipt: Any,
    extra_metadata: Mapping[str, Any] | None,
) -> str:
    """Build a compact ``output_summary`` string.

    The summary encodes the legacy class name, its id, and optional
    caller-supplied metadata keys (values are stringified). Downstream
    auditors can parse it deterministically because the separator is
    the pipe character which is not present in any SentinelModel id.
    """
    class_name = type(browser_receipt).__name__
    receipt_id = getattr(browser_receipt, "id", "")
    parts = [f"browser_receipt_type={class_name}", f"browser_receipt_id={receipt_id}"]
    if extra_metadata:
        for key in sorted(extra_metadata):
            value = extra_metadata[key]
            parts.append(f"{key}={value}")
    return " | ".join(parts)


def wrap_browser_execution_receipt(
    *,
    browser_receipt: BaseModel,
    dry_run: OrganDryRunReceipt,
    authority: OrganAuthorityEnvelope,
    kill_switch: OrganKillSwitch,
    execution_action_payload: dict[str, Any],
    trace_refs: list[str],
    promotion_level: OrganPromotionLevel = OrganPromotionLevel.L6_LIMITED_EXECUTION,
    metadata: Mapping[str, Any] | None = None,
    execution_completed: bool = True,
    event_bus: EventBus | None = None,
) -> OrganExecutionReceipt:
    """Wrap an existing browser legacy receipt in an
    :class:`OrganExecutionReceipt` without mutating the legacy object.

    Parameters
    ----------
    browser_receipt
        The legacy browser receipt (e.g.
        :class:`BrowserFormSubmitReceipt`,
        :class:`BrowserV3Receipt` subclass instance). Must be a
        pydantic :class:`BaseModel` with a non-empty ``id`` attribute.
        The object is not modified.
    dry_run
        The paired :class:`OrganDryRunReceipt`. Its
        ``action_payload_hash`` is the cryptographic anchor the
        :meth:`OrganExecutionReceipt.started` factory enforces.
    authority
        The execution-authorised :class:`OrganAuthorityEnvelope`.
        Must carry ``execution_authorized=True`` and
        ``dry_run_only=False``.
    kill_switch
        The organ's :class:`OrganKillSwitch`. Must not be triggered.
    execution_action_payload
        The canonical ``{"action": ..., "preview": ...}`` dict that
        was executed. The factory recomputes its hash and raises
        :class:`sentinel.organs.exceptions.ReceiptIntegrityError` on
        mismatch with the dry-run.
    trace_refs
        Non-empty list of event-bus trace references. The factory
        appends its own ``ORGAN_EXECUTION_RECEIPT_RECORDED`` event id
        to this list when ``event_bus`` is provided.
    promotion_level
        Execution promotion tier. Defaults to
        :attr:`OrganPromotionLevel.L6_LIMITED_EXECUTION` per doctrine;
        ``started()`` rejects lower tiers.
    metadata
        Optional structured annotations merged into
        ``output_summary`` for the auditor trail.
    execution_completed
        Flag passed through to the factory. Defaults to ``True`` for
        the common case where the legacy receipt already carries a
        completed result.
    event_bus
        Optional :class:`EventBus`. When supplied, the factory emits a
        ``ORGAN_EXECUTION_RECEIPT_RECORDED`` event and the returned
        receipt's ``trace_refs`` include that event id.

    Returns
    -------
    OrganExecutionReceipt
        A new receipt whose ``output_ref`` is the
        ``browser-receipt://<type>/<id>`` URI of the wrapped legacy
        receipt, whose ``action_payload_hash`` equals
        ``dry_run.action_payload_hash``, and whose ``receipt_hash`` is
        computed deterministically by the factory.

    Raises
    ------
    ReceiptIntegrityError
        If ``execution_action_payload`` hashes to a value that does
        not match ``dry_run.action_payload_hash``.
    ValueError
        If the legacy receipt has no ``id``, or if authority /
        kill-switch preconditions fail inside the factory.
    """
    output_ref = _legacy_receipt_uri(browser_receipt)
    output_summary = _legacy_receipt_summary(browser_receipt, metadata)
    return OrganExecutionReceipt.started(
        dry_run,
        authority,
        kill_switch,
        promotion_level=promotion_level,
        output_summary=output_summary,
        trace_refs=list(trace_refs),
        execution_action_payload=execution_action_payload,
        output_ref=output_ref,
        execution_completed=execution_completed,
        event_bus=event_bus,
    )


__all__ = [
    "LEGACY_RECEIPT_URI_SCHEME",
    "wrap_browser_execution_receipt",
]
