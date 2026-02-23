# backend/app/db.py
from sqlmodel import SQLModel, Session
from typing import Generator

def init_db(engine):
    SQLModel.metadata.create_all(engine)

def get_session(engine) -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session