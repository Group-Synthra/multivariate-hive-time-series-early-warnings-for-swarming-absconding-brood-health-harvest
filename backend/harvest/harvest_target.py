"""Create a future 72-hour harvest-event target from historical harvest=0/1 data."""

from __future__ import annotations

import numpy as np
import pandas as pd


TARGET_COLUMN = "harvest_within_72h"


def _collapse_positive_rows_to_events(
    hive_df: pd.DataFrame,
    *,
    label_column: str,
    merge_gap_hours: int,
) -> pd.DatetimeIndex:
    """
    Convert consecutive harvest=1 rows into one event timestamp.

    The first positive row is kept. Another positive row is treated as a new
    event only when it is more than merge_gap_hours after the previous kept
    event.
    """
    positive = hive_df.loc[
        hive_df[label_column].eq(1),
        "timestamp",
    ].sort_values()

    if positive.empty:
        return pd.DatetimeIndex([])

    kept = [positive.iloc[0]]

    for timestamp in positive.iloc[1:]:
        gap_hours = (
            timestamp - kept[-1]
        ).total_seconds() / 3600

        if gap_hours > merge_gap_hours:
            kept.append(timestamp)

    return pd.DatetimeIndex(kept)


def create_future_harvest_target(
    hourly_df: pd.DataFrame,
    *,
    label_column: str = "harvest",
    horizon_hours: int = 72,
    post_event_exclusion_hours: int = 24,
    merge_gap_hours: int = 12,
) -> pd.DataFrame:
    """
    Create target=1 when a harvest event occurs after the current row and within
    the next horizon_hours.

    Rows are excluded when:
    - their full future horizon is not observable near the dataset end;
    - they are actual event rows;
    - they occur within post_event_exclusion_hours after a harvest.
    """
    required = {"timestamp", "hive_id", label_column}
    missing = sorted(required - set(hourly_df.columns))

    if missing:
        raise ValueError(
            f"Historical dataset is missing columns: {missing}"
        )

    data = hourly_df.copy()
    data["timestamp"] = pd.to_datetime(
        data["timestamp"],
        errors="coerce",
        utc=True,
    )
    data[label_column] = (
        pd.to_numeric(
            data[label_column],
            errors="coerce",
        )
        .fillna(0)
        .gt(0)
        .astype(int)
    )

    data = data.dropna(
        subset=["timestamp", "hive_id"]
    )
    data = data.sort_values(
        ["hive_id", "timestamp"]
    ).reset_index(drop=True)

    output_frames: list[pd.DataFrame] = []

    for _, hive_df in data.groupby(
        "hive_id",
        sort=False,
    ):
        hive_df = hive_df.copy()
        timestamps = pd.DatetimeIndex(
            hive_df["timestamp"]
        )

        event_times = _collapse_positive_rows_to_events(
            hive_df,
            label_column=label_column,
            merge_gap_hours=merge_gap_hours,
        )

        next_event_values = np.full(
            len(hive_df),
            np.datetime64("NaT"),
            dtype="datetime64[ns]",
        )
        previous_event_values = np.full(
            len(hive_df),
            np.datetime64("NaT"),
            dtype="datetime64[ns]",
        )

        if len(event_times) > 0:
            event_ns = event_times.tz_convert(
                "UTC"
            ).tz_localize(None).to_numpy(
                dtype="datetime64[ns]"
            )
            row_ns = timestamps.tz_convert(
                "UTC"
            ).tz_localize(None).to_numpy(
                dtype="datetime64[ns]"
            )

            next_indices = np.searchsorted(
                event_ns,
                row_ns,
                side="right",
            )
            valid_next = next_indices < len(event_ns)
            next_event_values[valid_next] = event_ns[
                next_indices[valid_next]
            ]

            previous_indices = (
                np.searchsorted(
                    event_ns,
                    row_ns,
                    side="left",
                )
                - 1
            )
            valid_previous = previous_indices >= 0
            previous_event_values[
                valid_previous
            ] = event_ns[
                previous_indices[valid_previous]
            ]

        next_event = pd.to_datetime(
            next_event_values,
            utc=True,
        )
        previous_event = pd.to_datetime(
            previous_event_values,
            utc=True,
        )

        hive_df["next_harvest_timestamp"] = next_event
        hive_df["previous_harvest_timestamp"] = previous_event

        hive_df["hours_until_next_harvest"] = (
            hive_df["next_harvest_timestamp"]
            - hive_df["timestamp"]
        ).dt.total_seconds() / 3600

        hive_df["hours_since_previous_harvest"] = (
            hive_df["timestamp"]
            - hive_df["previous_harvest_timestamp"]
        ).dt.total_seconds() / 3600

        hive_df[TARGET_COLUMN] = (
            hive_df["hours_until_next_harvest"]
            .gt(0)
            & hive_df["hours_until_next_harvest"]
            .le(horizon_hours)
        ).astype(int)

        final_timestamp = hive_df["timestamp"].max()
        horizon_is_observed = (
            hive_df["timestamp"]
            <= final_timestamp
            - pd.Timedelta(hours=horizon_hours)
        )

        outside_post_event_period = (
            hive_df["hours_since_previous_harvest"].isna()
            | hive_df[
                "hours_since_previous_harvest"
            ].gt(post_event_exclusion_hours)
        )

        not_event_row = hive_df[label_column].eq(0)

        hive_df["target_row_eligible"] = (
            horizon_is_observed
            & outside_post_event_period
            & not_event_row
        )

        output_frames.append(hive_df)

    result = pd.concat(
        output_frames,
        ignore_index=True,
    )

    return result.sort_values(
        ["hive_id", "timestamp"]
    ).reset_index(drop=True)
