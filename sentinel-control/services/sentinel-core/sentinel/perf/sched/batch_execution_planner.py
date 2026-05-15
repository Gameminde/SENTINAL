"""``BatchExecutionPlanner`` — safe read-only fusion (Phase D, Task 8.3).

This module groups queued organ actions into :class:`OrganActionBatch`
objects so the scheduler can fan out fusable read-only work in one go
instead of dispatching each call individually. It is a **pure planner**:
it owns no state, emits no ``EventBus`` events, mutates none of its
inputs, and performs no I/O. Given the same input list it returns the
same list of batches (deterministic).

Read-only invariant
-------------------
Fusion is **only** safe for read-only operations whose interleaving has
no observable side effects: file reads, HTTP HEAD requests, and
metadata fetches. Batching mutating actions (writes, deletes, network
mutations) would change observable behaviour because the order and
isolation of side effects would no longer be preserved by the scheduler.
Anything outside :data:`_FUSABLE_KINDS` therefore falls to a
single-action ``"sequential"`` batch — the planner never fuses an
unrecognised or write-bearing action.

Grouping rule
-------------
Two fusable actions are fused iff they share the **same**
``action_type`` and the **same** ``organ_id``. Mixing organs would
require the scheduler to dispatch one batch across organ boundaries,
which the Phase D scheduler does not do; mixing action types would
require the organ to know how to dispatch heterogeneous payloads,
which is also not part of the contract. The grouping is therefore the
strictest correct fusion: identical action shape on identical organ.

Order preservation
------------------
The output preserves the order of **first appearance** of each group's
first action in the input list. That is, if the first ``file_read``
on organ ``A`` appears at input index 2 and the first ``http_head`` on
organ ``B`` appears at input index 5, the ``file_read`` batch is
emitted before the ``http_head`` batch. Non-fusable actions retain
their own input position in the output ordering. This makes the planner
output stable and reviewable; it also means callers that already
ordered their input by deadline or priority will see that ordering
reflected in the batch sequence.

Determinism
-----------
Same input list (by value) → same output list (by value). The planner
holds no instance state, uses no clock, and consults no external
resource, so two consecutive calls with equal inputs produce equal
outputs.

Requirements covered: scheduling efficiency (implicit per Task 8.3).
"""

from __future__ import annotations

from pydantic import ConfigDict, Field

from sentinel.perf.sched.tool_call_queue import QueuedAction
from sentinel.shared.models import SentinelModel, new_id

# Sentinel marker used as the first element of a group key for
# non-fusable actions. The second element is the action's input
# index, which guarantees uniqueness so each non-fusable action gets
# its own ``"sequential"`` batch. The marker string is intentionally
# namespaced with double underscores so it cannot collide with any
# real ``action_type`` that the scheduler may add later.
_SEQUENTIAL_KEY_MARKER = "__sequential__"

# The closed set of action types that are safe to fuse. Anything
# outside this set falls to a single-action ``"sequential"`` batch.
# This set is intentionally conservative: adding a new fusable kind
# requires a corresponding scheduler change to actually dispatch the
# batch as a single unit, so the planner refuses to fuse anything
# until that contract is in place.
_FUSABLE_KINDS: frozenset[str] = frozenset(
    {"file_read", "http_head", "metadata_fetch"}
)


class OrganActionBatch(SentinelModel):
    """Frozen, deterministic group of queued actions handed to the scheduler.

    * ``batch_id`` — fresh ``"batch_*"`` identifier per batch instance.
      Defaulted via ``new_id`` so callers do not have to mint one.
    * ``actions`` — tuple of :class:`QueuedAction` items in their original
      input order. A tuple (rather than a list) is used because the
      model is frozen; pydantic accepts ``tuple[..., ...]`` natively.
    * ``kind`` — one of ``"file_read"``, ``"http_head"``,
      ``"metadata_fetch"``, ``"sequential"``. The first three indicate
      a fused read-only batch whose action type matches the string;
      ``"sequential"`` indicates a single-action batch for an action
      that was not fused (either its type is not in
      :data:`_FUSABLE_KINDS` or it was the only action with its
      ``(action_type, organ_id)`` key — though the latter case still
      uses the action_type kind, see :meth:`BatchExecutionPlanner.plan`).

    The model is frozen so a planned batch can be passed by reference
    to the scheduler and to ``EventBus`` subscribers without defensive
    copies.
    """

    batch_id: str = Field(default_factory=lambda: new_id("batch"))
    actions: tuple[QueuedAction, ...]
    kind: str

    model_config = ConfigDict(extra="forbid", frozen=True, use_enum_values=False)


class BatchExecutionPlanner:
    """Pure planner that fuses safe read-only actions into batches.

    No constructor state, no clock, no events, no mutation of input.
    Holds the read-only-fusion contract documented in the module
    docstring and re-iterated on :meth:`plan`. Two consecutive calls
    with equal input lists return equal output lists.

    Layering: the planner sits between :class:`ToolCallQueue` (which
    owns ordering and metrics) and :class:`AsyncOrganScheduler` (which
    owns dispatch). It performs no admission decision — that is the
    job of :class:`BackpressureController` (Task 8.2).
    """

    def plan(self, actions: list[QueuedAction]) -> list[OrganActionBatch]:
        """Group ``actions`` into batches per the read-only fusion rule.

        Behaviour:

        * **Empty input** → empty output.
        * **Fusable actions** (``action_type in _FUSABLE_KINDS``) are
          grouped by ``(action_type, organ_id)``. Each group emits one
          :class:`OrganActionBatch` whose ``kind`` equals the shared
          ``action_type`` and whose ``actions`` tuple is the group's
          actions in original input order. A group of size 1 still
          emits as a fused batch (its kind matches the action type) —
          this keeps the scheduler's dispatch path uniform across
          group sizes.
        * **Non-fusable actions** (``action_type not in _FUSABLE_KINDS``)
          each emit their own single-action :class:`OrganActionBatch`
          with ``kind="sequential"``. This includes mutating actions
          (writes, deletes), unknown action types, and any future
          action type not yet added to :data:`_FUSABLE_KINDS`.
        * **Order**: the output preserves the order of first
          appearance of each group's first action in ``actions``.
          Non-fusable actions retain their own input position in this
          ordering.
        * **Determinism**: equal input → equal output (modulo the
          ``batch_id`` which is freshly minted per call; this is the
          documented exception and is the reason equality should be
          checked on ``(kind, actions)``, not on the model as a whole,
          when verifying determinism in tests).

        The input list is not mutated. The returned list is a new
        list; mutating it does not affect the planner.
        """
        if not actions:
            return []

        # ``group_order`` records the order of first appearance of each
        # group key. ``groups`` maps each key to its accumulating list
        # of actions in input order. We use a list for ``group_order``
        # rather than a dict's insertion order alone so the intent
        # ("preserve first-appearance order") is explicit at the call
        # site that emits the batches.
        group_order: list[tuple[str, str | int]] = []
        groups: dict[tuple[str, str | int], list[QueuedAction]] = {}

        for index, action in enumerate(actions):
            if action.action_type in _FUSABLE_KINDS:
                key: tuple[str, str | int] = (action.action_type, action.organ_id)
                if key not in groups:
                    groups[key] = []
                    group_order.append(key)
                groups[key].append(action)
            else:
                # Each non-fusable action becomes its own group, keyed
                # by its input index so two non-fusable actions of the
                # same type never collide. The marker first element
                # signals "emit as sequential" without leaking a real
                # action type into the kind field.
                key = (_SEQUENTIAL_KEY_MARKER, index)
                groups[key] = [action]
                group_order.append(key)

        batches: list[OrganActionBatch] = []
        for key in group_order:
            items = groups[key]
            if key[0] == _SEQUENTIAL_KEY_MARKER:
                kind = "sequential"
            else:
                # ``key[0]`` is the shared ``action_type`` for this
                # fusable group, which also serves as the batch kind.
                kind = key[0]
            batches.append(OrganActionBatch(kind=kind, actions=tuple(items)))
        return batches


__all__ = [
    "BatchExecutionPlanner",
    "OrganActionBatch",
]
