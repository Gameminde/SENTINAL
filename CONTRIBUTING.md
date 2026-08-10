# Contributing to Sentinel Control

Thank you for your interest in Sentinel Control.

Sentinel is an experimental cognitive operating system for AI agents. The project is trying to make increasingly capable AI systems able to understand browsers, computers, workspaces, and long-running missions while keeping authority, evidence, replay, revocation, and kill outside the model.

Because the trust boundary is part of the product, contributions are evaluated for more than whether they work once. They should preserve Sentinel's authority model and make their claims inspectable.

## Where contributions help most

High-value contributions include:

- browser perception, world-state quality, recovery, and evidence
- computer-use perception and governed desktop foundations
- long-horizon mission reliability, checkpoints, progress, and replay
- model-facing state compression and cognitive interfaces
- workers, workflows, memory, telemetry, and proof systems
- tests that expose false-positive completion or hidden side effects
- documentation that makes architecture and current maturity easier to understand
- small, well-scoped fixes that remove duplicated or obsolete execution paths

Before implementing a large new capability surface, consider opening an issue describing the problem, proposed boundary, expected authority requirements, and how it would be tested.

## Development setup

Sentinel Core currently requires Python 3.11 or newer.

```bash
git clone https://github.com/Gameminde/SENTINAL.git
cd SENTINAL/sentinel-control/services/sentinel-core
python -m venv .venv
```

Activate the environment.

macOS / Linux:

```bash
source .venv/bin/activate
```

Windows PowerShell:

```powershell
.venv\Scripts\Activate.ps1
```

Install the core package and test dependencies:

```bash
python -m pip install --upgrade pip
pip install -e ".[test]"
```

For work that needs the Cloak browser integration:

```bash
pip install -e ".[test,cloak]"
```

Run the test suite:

```bash
pytest
```

The project also defines a `slow` pytest marker for long-running benchmark/property tests. During iteration you can exclude it with:

```bash
pytest -m "not slow"
```

## Contribution principles

### 1. Do not turn data into authority

Model output, memory, telemetry, receipts, browser state, desktop state, skill metadata, or worker output must not silently grant permission.

If a change introduces a new real-world effect, identify the authority boundary explicitly.

### 2. Preserve evidence

Important actions should remain inspectable. A successful return value is not sufficient evidence that an external effect occurred correctly.

Prefer designs that make before/after state, receipts, terminal records, and replay stronger.

### 3. Replay must not re-execute side effects

Historical inspection should never accidentally repeat a browser submission, external write, message send, payment-like action, desktop effect, or other material operation.

### 4. Respect revocation and kill

Long-running work must remain interruptible. New execution surfaces should not bypass mission kill or revocation semantics.

### 5. Memory is context, not permission

Persistent memory may help the model understand history or preferences. It must not become an implicit authorization mechanism.

### 6. Be precise about maturity

Use terms such as `experimental`, `local foundation`, `fake/injected`, `sandbox`, `live-proven`, or `product-proven` accurately.

Do not promote an implementation claim simply because code exists or a deterministic test passes.

### 7. Prefer convergence over capability sprawl

Sentinel already has many organs. Contributions that make existing browser, computer, mission, worker, memory, and proof systems cooperate reliably are usually more valuable than adding another disconnected tool.

## Pull requests

Keep pull requests focused where possible.

A good PR description should explain:

- what problem is being solved
- why the change belongs in Sentinel
- which authority or trust boundaries are affected
- what evidence/tests were used
- what remains unproven
- whether the change performs or enables any external side effect

For changes to authority-sensitive surfaces, include tests covering denied or revoked paths as well as the successful path.

## Tests

Add or update tests when behavior changes.

Particularly valuable tests cover:

- authority rejection
- kill/revocation behavior
- idempotency and duplicate prevention
- replay without re-execution
- redaction and secret non-persistence
- browser/session recovery
- before/after evidence
- incomplete or failed mission truth
- model claims that are stronger than the available evidence

## Security-sensitive changes

If you discover a vulnerability or a way to bypass Sentinel's authority, evidence, secret, replay, or revocation boundaries, do not publish exploit details in a public issue. Follow the process in `SECURITY.md`.

## Licensing

By contributing to this repository, you agree that your contributions are provided under the repository's Apache License 2.0.

See [`LICENSE`](LICENSE).

## Project status

Sentinel is pre-release research and engineering software. APIs, architecture, and internal contracts may change quickly while the project converges on a canonical runtime.

The goal is not to make Sentinel appear finished.

The goal is to make it powerful, useful, inspectable, and increasingly difficult to fool about what it actually did.
