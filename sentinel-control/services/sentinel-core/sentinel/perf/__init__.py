"""Sentinel Performance Runtime Foundation.

This package installs the measurement, hot/cold-state, cache-correctness,
async-scheduling, workspace-delta, and benchmark-gate foundation for the
Sentinel runtime. It is intentionally additive: nothing existing moves, and
integration into existing modules happens by constructor injection or
call-site wrapping at reserved hook points.

Layering rule (enforced; do not violate)
----------------------------------------

    measure  -->  hot_cold  -->  caches / sched / workspace  -->  bench

Read "A --> B" as "B may import from A". The layers are strictly directed;
`bench` is fan-in only: no other layer imports from `bench`.

Concretely:

* ``measure``    depends on nothing inside ``sentinel/perf/``.
* ``hot_cold``   may import from ``measure``.
* ``caches``     may import from ``hot_cold`` and ``measure``.
* ``sched``      may import from ``hot_cold`` and ``measure``.
* ``workspace``  may import from ``hot_cold`` and ``measure``.
* ``bench``      may import from ``measure``, ``hot_cold``, ``caches``,
  ``sched``, and ``workspace``. No ``perf`` layer imports from ``bench``.

Rationale: measurement must land before any optimization it would measure;
caches and schedulers reference (never duplicate) cold-stored receipts and
artifacts; benchmarks aggregate all prior phases and must not be a runtime
dependency of the hot path.

Phase ordering (A --> B --> C --> D --> E --> F) is mandatory and mirrors
the layering above.
"""
