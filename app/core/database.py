from contextlib import contextmanager
from typing import Callable, Generator, Any, Optional
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker, Session
from urllib.parse import urlparse


class DatabaseConnector:
    """데이터베이스 연결을 관리하는 래퍼.

    지원 DB:
    - sqlite:///path/to/file.db
    - postgresql+psycopg://user:pass@host:port/dbname
    - postgresql+psycopg2://user:pass@host:port/dbname
    - mysql+pymysql://user:pass@host:port/dbname
    """

    def __init__(self, db_url: str):
        self.db_url = db_url
        self.engine = self._create_engine(db_url)
        self.SessionLocal = sessionmaker(bind=self.engine, expire_on_commit=False)

    def _create_engine(self, db_url: str) -> Engine:
        parsed = urlparse(db_url)
        scheme = parsed.scheme

        if scheme == "sqlite":
            return create_engine(db_url, connect_args={"check_same_thread": False})

        if scheme in {"postgresql", "postgresql+psycopg", "postgresql+psycopg2"}:
            return create_engine(db_url)

        if scheme in {"mysql", "mysql+pymysql"}:
            return create_engine(db_url)

        raise ValueError(
            "Unsupported database URL. Supported schemes: sqlite, postgresql, mysql"
        )

    def connect(self) -> Session:
        return self.SessionLocal()

    def test_connection(self) -> None:
        with self.engine.connect() as connection:
            connection.execute(text("SELECT 1"))

    @contextmanager
    def session_scope(self) -> Generator[Session, None, None]:
        session = self.connect()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()


class DatabaseUtils:
    """DB 연결/세션을 안전하게 관리하기 위한 공통 유틸리티."""

    @staticmethod
    @contextmanager
    def session_scope(session_factory: Callable[[], Any]) -> Generator[Any, None, None]:
        session = session_factory()
        try:
            yield session
            if hasattr(session, "commit"):
                session.commit()
        except Exception:
            if hasattr(session, "rollback"):
                session.rollback()
            raise
        finally:
            if hasattr(session, "close"):
                session.close()

    @staticmethod
    @contextmanager
    def connection_scope(connect_callable: Callable[[], Any]) -> Generator[Any, None, None]:
        connection = connect_callable()
        try:
            yield connection
        except Exception:
            raise
        finally:
            if hasattr(connection, "close"):
                connection.close()
