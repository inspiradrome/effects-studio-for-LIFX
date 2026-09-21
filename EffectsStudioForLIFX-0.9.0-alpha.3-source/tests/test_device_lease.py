from effects_studio.device_lease import DeviceLease


def test_second_lease_is_refused_until_first_releases(tmp_path) -> None:
    path = tmp_path / "tube.lock"
    first = DeviceLease(path)
    second = DeviceLease(path)

    assert first.acquire() is True
    assert second.acquire() is False
    first.release()
    assert second.acquire() is True
    second.release()


def test_lease_acquire_is_idempotent(tmp_path) -> None:
    lease = DeviceLease(tmp_path / "tube.lock")

    assert lease.acquire() is True
    assert lease.acquire() is True
    lease.release()
