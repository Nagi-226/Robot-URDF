"""Joint animation engine — eased interpolation and real-time follow.

Adopted from text-to-cad's jointAnimation.js:
  - Quintic easing (Ken Perlin smootherstep) for fixed-duration tweens
  - Exponential moving average for real-time slider response
  - Angular wrap-around for continuous/revolute joints
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field


# ---------------------------------------------------------------------------
# Core math
# ---------------------------------------------------------------------------

def ease_quintic(t: float) -> float:
    """Ken Perlin's smootherstep: zero velocity and acceleration at 0 and 1.

    f(t) = 6*t^5 - 15*t^4 + 10*t^3
    """
    t = max(0.0, min(1.0, t))
    return t * t * t * (t * (6.0 * t - 15.0) + 10.0)


def wrap_angle_delta_deg(delta_deg: float) -> float:
    """Wrap angular delta to [-180, 180) for shortest-path rotation."""
    wrapped = ((delta_deg + 180.0) % 360.0 + 360.0) % 360.0 - 180.0
    if wrapped == -180.0 and delta_deg > 0:
        return 180.0
    return wrapped


def _clamp_joint_value(value: float, lower: float, upper: float) -> float:
    return max(lower, min(upper, value))


# ---------------------------------------------------------------------------
# Animation state
# ---------------------------------------------------------------------------

@dataclass
class AnimationState:
    """Tracks animation progress for a set of joints."""

    target_values: dict[str, float] = field(default_factory=dict)
    start_values: dict[str, float] = field(default_factory=dict)
    current_values: dict[str, float] = field(default_factory=dict)
    elapsed_ms: float = 0.0
    duration_ms: float = 840.0
    done: bool = True


@dataclass
class JointAnimationConfig:
    duration_ms: float = 840.0
    follow_smoothing_ms: float = 240.0
    epsilon: float = 0.001


# ---------------------------------------------------------------------------
# Interpolation (eased tween)
# ---------------------------------------------------------------------------

def interpolate_joint_values(
    current: dict[str, float],
    targets: dict[str, float],
    progress: float,
    wrapped_joints: set[str] | None = None,
    joint_limits: dict[str, tuple[float, float]] | None = None,
    epsilon: float = 0.001,
) -> tuple[dict[str, float], bool]:
    """Eased interpolation for a fixed-duration tween.

    Args:
        current: current joint values by name.
        targets: desired target joint values by name.
        progress: tween progress in [0, 1].
        wrapped_joints: joint names that should use angular wrap-around.
        joint_limits: {name: (lower, upper)} for clamping.
        epsilon: tolerance for "done" check.

    Returns:
        (values_by_name, done) — done is True when all joints reached target.
    """
    if wrapped_joints is None:
        wrapped_joints = set()
    if joint_limits is None:
        joint_limits = {}

    eased_progress = ease_quintic(max(0.0, min(1.0, progress)))
    result: dict[str, float] = {}
    all_done = True

    for name, target in sorted(targets.items()):
        start = current.get(name, target)
        delta = target - start

        if name in wrapped_joints:
            delta = wrap_angle_delta_deg(delta)

        value = start + delta * eased_progress

        # Clamp to limits
        limits = joint_limits.get(name)
        if limits is not None:
            value = _clamp_joint_value(value, *limits)

        result[name] = value

        # Check if done (within epsilon of target)
        remaining = abs(delta * (1.0 - eased_progress))
        if remaining > epsilon and progress < 1.0:
            all_done = False

    return result, all_done


# ---------------------------------------------------------------------------
# Exponential follow (real-time)
# ---------------------------------------------------------------------------

def advance_joint_values(
    current: dict[str, float],
    targets: dict[str, float],
    delta_ms: float,
    smoothing_ms: float = 240.0,
    wrapped_joints: set[str] | None = None,
    joint_limits: dict[str, tuple[float, float]] | None = None,
    epsilon: float = 0.001,
) -> tuple[dict[str, float], bool]:
    """Exponential moving average follow for real-time joint control.

    After `smoothing_ms` milliseconds, a joint covers ~63% of the
    remaining gap.  No overshoot, proportional to elapsed time.

    Args:
        current: current joint values by name.
        targets: target joint values by name.
        delta_ms: elapsed milliseconds since last update.
        smoothing_ms: EMA smoothing constant in ms.
        wrapped_joints: joint names for angular wrap-around.
        joint_limits: {name: (lower, upper)} for clamping.
        epsilon: tolerance for "done" check.

    Returns:
        (values_by_name, done).
    """
    if wrapped_joints is None:
        wrapped_joints = set()
    if joint_limits is None:
        joint_limits = {}

    # alpha = 1 - e^(-dt/tau)
    dt = max(delta_ms, 0.0)
    tau = max(smoothing_ms, 1.0)
    alpha = min(max(1.0 - math.exp(-dt / tau), 0.0), 1.0)

    result: dict[str, float] = {}
    all_done = True

    for name, target in sorted(targets.items()):
        start = current.get(name, target)
        delta = target - start

        if name in wrapped_joints:
            delta = wrap_angle_delta_deg(delta)

        value = start + delta * alpha

        limits = joint_limits.get(name)
        if limits is not None:
            value = _clamp_joint_value(value, *limits)

        result[name] = value

        remaining = abs(target - value)
        if remaining > epsilon:
            all_done = False

    return result, all_done


# ---------------------------------------------------------------------------
# Joint value maps comparison
# ---------------------------------------------------------------------------

def joint_maps_close(
    a: dict[str, float],
    b: dict[str, float],
    epsilon: float = 0.001,
) -> bool:
    """True when all joint values in both maps match within epsilon."""
    all_names = set(a) | set(b)
    for name in all_names:
        if abs(a.get(name, 0.0) - b.get(name, 0.0)) > epsilon:
            return False
    return True
