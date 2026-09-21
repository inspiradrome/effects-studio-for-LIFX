import pytest

from effects_studio.lifx_output import StudioOutput, TubeOutputConfig, decode_config, encode_config


def test_initial_status_identifies_configured_tube():
    output = StudioOutput(TubeOutputConfig(serial="d073d5000001", ip="192.0.2.10"))

    assert output.status() == {
        "mode": "lifx",
        "connected": False,
        "message": "Connecting to Tube",
        "serial": "d073d5000001",
        "ip": "192.0.2.10",
        "label": None,
        "playing": False,
    }


def test_device_selection_round_trips_through_local_settings():
    config = TubeOutputConfig(serial="d073d5000001", ip="192.0.2.10", brightness=0.64)

    assert decode_config(encode_config(config)) == config


@pytest.mark.asyncio
async def test_start_refuses_a_tube_leased_by_another_process(tmp_path):
    output = StudioOutput(
        TubeOutputConfig(serial="d073d5000001", ip="192.0.2.10"),
        settings_path=tmp_path / "device.json",
    )
    output._lease.acquire = lambda: False

    await output.start()

    assert output._task is None
    assert output.connected is False
    assert output.message == "Tube already in use by another Effects Studio"
