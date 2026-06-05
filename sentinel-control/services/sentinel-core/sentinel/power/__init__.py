from sentinel.power.runtime import (
    PowerActuatorCapabilityLevel,
    PowerActuatorFamily,
    PowerMissionGraph,
    PowerMissionPlan,
    PowerMissionTimeline,
    PowerMissionTimelineItem,
    PowerRuntimeConfig,
    PowerRuntimeResult,
    PowerRuntimeStatus,
    PowerStepResult,
    PowerStepStatus,
    SentinelPowerRuntimeV0,
)

__all__ = [
    "PowerActuatorCapabilityLevel",
    "PowerActuatorFamily",
    "PowerMissionGraph",
    "PowerMissionPlan",
    "PowerMissionTimeline",
    "PowerMissionTimelineItem",
    "PowerRuntimeConfig",
    "PowerRuntimeResult",
    "PowerRuntimeStatus",
    "PowerStepResult",
    "PowerStepStatus",
    "SentinelPowerRuntimeV0",
    "run_power_fabric_orchestration_demo",
]


def __getattr__(name: str):
    if name == "run_power_fabric_orchestration_demo":
        from sentinel.power.demo import run_power_fabric_orchestration_demo

        return run_power_fabric_orchestration_demo
    raise AttributeError(name)
