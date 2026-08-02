"""Test database, classifier artifacts and one live prediction."""

from __future__ import annotations

import json

from services.live_harvest_service import (
    get_live_devices,
    get_live_health,
    predict_live_harvest,
)


def main() -> None:
    print("LIVE HEALTH")
    print(
        json.dumps(
            get_live_health(),
            indent=2,
        )
    )

    devices = get_live_devices()

    print("\nDEVICES")
    print(devices)

    if not devices:
        print(
            "No devices were returned by "
            "the database."
        )
        return

    print(
        f"\nPREDICTION FOR {devices[0]}"
    )
    print(
        json.dumps(
            predict_live_harvest(
                devices[0],
                history_hours=168,
            ),
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
