from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import get_settings


settings = get_settings()

engine_options = {"pool_pre_ping": True, "pool_recycle": 300}
if settings.is_production and settings.database_url.startswith("postgresql"):
    # Neon requires TLS. Existing query parameters remain authoritative.
    engine_options["connect_args"] = {"sslmode": "require"}
engine = create_engine(settings.database_url, **engine_options)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, class_=Session)


def get_db() -> Session:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
