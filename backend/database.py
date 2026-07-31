import os
from dotenv import load_dotenv
from sqlalchemy import create_engine

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise Exception("DATABASE_URL not found")


engine = create_engine(
    DATABASE_URL,
    connect_args={
        "sslmode": "require"
    },
    pool_pre_ping=True,
)


def get_engine():
    return engine