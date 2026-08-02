from __future__ import annotations

import os

from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()

database_url = os.getenv("DATABASE_URL")
sslmode = os.getenv("DATABASE_SSLMODE", "require")

if not database_url:
    raise RuntimeError("DATABASE_URL is not configured.")

engine = create_engine(
    database_url,
    connect_args={"sslmode": sslmode},
    pool_pre_ping=True,
    pool_size=3,
    max_overflow=2,
)

query = text(
    """
    SELECT
        device_id,
        recorded_at,
        reading_at,
        internal_temp,
        internal_humidity,
        internal_co2,
        total_weight,
        external_temp,
        external_humidity,
        battery_voltage
    FROM public.beehive_readings
    ORDER BY COALESCE(reading_at, recorded_at) DESC
    LIMIT 5
    """
)

try:
    with engine.connect() as connection:
        server_time = connection.execute(
            text("SELECT NOW()")
        ).scalar_one()

        rows = connection.execute(query).mappings().all()

        print(f"Database connected successfully.")
        print(f"Database server time: {server_time}")
        print(f"Rows returned: {len(rows)}")

        for row in rows:
            print(dict(row))

finally:
    engine.dispose()