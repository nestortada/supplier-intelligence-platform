from typing import Annotated

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy import text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.user_profile import UserProfile


DEFAULT_PROFILE_NAME = "Alex Mercer"


def get_or_create_default_profile(db: Session) -> UserProfile:
    profile = db.query(UserProfile).order_by(UserProfile.id.asc()).first()
    if profile is not None:
        return profile

    profile = UserProfile(name=DEFAULT_PROFILE_NAME)
    db.add(profile)
    db.commit()
    db.refresh(profile)
    return profile


def get_active_profile_id(
    x_profile_id: Annotated[int | None, Header(alias="X-Profile-Id")] = None,
    db: Session = Depends(get_db),
) -> int:
    if x_profile_id is None:
        return get_or_create_default_profile(db).id

    profile = db.get(UserProfile, x_profile_id)
    if profile is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found.")
    return profile.id


def is_default_profile(db: Session, profile_id: int) -> bool:
    return get_or_create_default_profile(db).id == profile_id


def scoped_profile_filter(model, profile_id: int, db: Session):
    condition = model.profile_id == profile_id
    if is_default_profile(db, profile_id):
        condition = condition | model.profile_id.is_(None)
    return condition


def ensure_profile_schema(engine: Engine) -> None:
    if engine.dialect.name != "sqlite":
        return

    with engine.begin() as connection:
        connection.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS user_profiles (
                    id INTEGER NOT NULL PRIMARY KEY,
                    name VARCHAR(120) NOT NULL,
                    avatar_data_url TEXT,
                    created_at DATETIME,
                    updated_at DATETIME
                )
                """
            )
        )
        default_profile_id = connection.execute(text("SELECT id FROM user_profiles ORDER BY id ASC LIMIT 1")).scalar()
        if default_profile_id is None:
            connection.execute(
                text(
                    """
                    INSERT INTO user_profiles (name, created_at, updated_at)
                    VALUES (:name, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                    """
                ),
                {"name": DEFAULT_PROFILE_NAME},
            )
            default_profile_id = connection.execute(text("SELECT id FROM user_profiles ORDER BY id ASC LIMIT 1")).scalar()

        for table_name in ("suppliers", "products", "email_campaigns", "email_logs", "background_jobs"):
            columns = {
                row[1]
                for row in connection.execute(text(f"PRAGMA table_info({table_name})")).fetchall()
            }
            if "profile_id" not in columns:
                connection.execute(text(f"ALTER TABLE {table_name} ADD COLUMN profile_id INTEGER"))
            connection.execute(
                text(f"UPDATE {table_name} SET profile_id = :profile_id WHERE profile_id IS NULL"),
                {"profile_id": default_profile_id},
            )
