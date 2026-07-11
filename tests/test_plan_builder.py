from copy import deepcopy

from hal_runtime.plan_builder import build_runtime_plan
from hal_runtime.profile_loader import load_profile
from hal_runtime.safety_gate import SafetyGate


def _build(profile):
    return build_runtime_plan(profile, SafetyGate().evaluate(profile))


def test_valid_profile_creates_planned_assignment():
    plan = _build(load_profile("samples/recovery_profile.json"))

    assert len(plan.actions) == 1
    assert plan.actions[0].action_type == "assign_workload"
    assert plan.actions[0].status == "planned"
    assert plan.actions[0].route_id == "ROUTE_WL_SC_01"
    assert plan.blocked_actions == ()
    assert plan.plan_status == "planned"
    assert plan.plan_block_reasons == ()


def test_missing_routes_enters_degraded_mode_without_actions():
    profile = load_profile("samples/degraded_missing_routes_profile.json")
    gate = SafetyGate().evaluate(profile)
    plan = build_runtime_plan(profile, gate)

    assert gate.degraded_mode is True
    assert plan.actions == ()
    assert plan.blocked_actions == ()
    assert plan.plan_status == "degraded_no_execution_plan"
    assert plan.plan_block_reasons == ("preferred_routes_missing",)


def test_non_candidate_route_is_blocked():
    profile = deepcopy(load_profile("samples/recovery_profile.json"))
    profile["preferred_routes"][0]["route_status"] = "unverified"

    plan = _build(profile)

    assert plan.actions == ()
    assert plan.blocked_actions[0].reason == "route_status_must_be_candidate_simulated"


def test_unknown_action_is_blocked_while_valid_assignment_remains_planned():
    plan = _build(load_profile("samples/unknown_action_profile.json"))

    assert len(plan.actions) == 1
    assert len(plan.blocked_actions) == 1
    assert plan.blocked_actions[0].action_type == "rebalance_cluster"
    assert plan.blocked_actions[0].reason == "unsupported_action_source"
    assert plan.plan_status == "planned_with_blocks"
    assert "unsupported_action_source" in plan.plan_block_reasons


def test_unknown_workload_role_is_blocked():
    profile = deepcopy(load_profile("samples/recovery_profile.json"))
    profile["assigned_workloads"][0]["role"] = "unknown_role"

    plan = _build(profile)

    assert plan.actions == ()
    assert plan.blocked_actions[0].reason == "workload_role_not_allowed"


def test_failed_gate_never_builds_actions():
    profile = deepcopy(load_profile("samples/recovery_profile.json"))
    profile["hardware_control_enabled"] = True

    plan = _build(profile)

    assert plan.actions == ()
    assert plan.blocked_actions == ()
    assert plan.plan_status == "blocked_by_safety_gate"
    assert plan.plan_block_reasons == ("hardware_control_enabled_must_be_false",)

