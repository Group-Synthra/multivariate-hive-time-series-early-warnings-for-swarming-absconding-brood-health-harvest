"""Quick end-to-end test after training the live-compatible model."""

from __future__ import annotations

from services.live_harvest_service import get_live_devices, get_live_health, predict_live_hui


def main() -> None:
    print("Live health:")
    print(get_live_health())

    devices = get_live_devices()
    print(f"Devices: {devices}")

    if not devices:
        raise RuntimeError("No IoT devices were returned by the database.")

    device_id = devices[0]
    print(f"Testing prediction for: {device_id}")
    print(predict_live_hui(device_id))


if __name__ == "__main__":
    main()
