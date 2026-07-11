import json

from hal_runtime.review_decision import validate_review_decision


def _decision():
    return json.loads(open("samples/review_decision_approved.json", encoding="utf-8").read())


def test_reviewer_id_is_required():
    decision = _decision()
    decision["reviewer_id"] = ""

    valid, reasons, _ = validate_review_decision(decision)

    assert valid is False
    assert "review_decision_reviewer_id_missing" in reasons


def test_all_acknowledgements_must_be_true():
    decision = _decision()
    decision["acknowledged_limitations"]["dry_run_only"] = False

    valid, reasons, _ = validate_review_decision(decision)

    assert valid is False
    assert "review_decision_acknowledgement_missing:dry_run_only" in reasons


def test_approved_scope_and_human_approval_are_required():
    decision = _decision()
    decision["approved_for"] = "production"
    decision["human_review_approved"] = False

    valid, reasons, _ = validate_review_decision(decision)

    assert valid is False
    assert "review_decision_approved_for_not_dry_run_only" in reasons
    assert "review_decision_human_review_approved_false" in reasons


def test_review_decision_hardware_control_enabled_blocks():
    decision = _decision()
    decision["hardware_control_enabled"] = True

    valid, reasons, _ = validate_review_decision(decision)

    assert valid is False
    assert "review_decision_hardware_control_enabled_true" in reasons
