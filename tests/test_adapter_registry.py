from hal_runtime.adapter_registry import AdapterRegistry
from hal_runtime.cli import EXIT_OK, main


def test_builtin_registry_has_three_safe_adapters():
    adapters = AdapterRegistry().list_adapters()

    assert len(adapters) >= 3
    assert [adapter.info.adapter_id for adapter in adapters[:3]] == [
        "mock_sensor_tile_adapter",
        "mock_routing_tile_adapter",
        "mock_memory_tile_adapter",
    ]
    assert all(adapter.info.simulation_only is True for adapter in adapters)
    assert all(adapter.info.hardware_control_enabled is False for adapter in adapters)
    assert all(
        adapter.info.claim_boundary == "simulation_only_not_certified"
        for adapter in adapters
    )


def test_list_adapters_command_exits_zero(capsys):
    result = main(["list-adapters"])

    output = capsys.readouterr().out
    assert result == EXIT_OK
    assert "mock_sensor_tile_adapter" in output
    assert "assign_workload" in output

