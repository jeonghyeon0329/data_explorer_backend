from sqlalchemy import BigInteger, Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from datetime import datetime, timezone
from app.models.user_model import Base


class Dataset(Base):
    __tablename__ = "datasets"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    file_type = Column(String(10), nullable=False)          # csv | xlsx | json
    original_filename = Column(String(255), nullable=False)
    file_size = Column(BigInteger, nullable=False)
    row_count = Column(Integer, nullable=False, default=0)
    column_count = Column(Integer, nullable=False, default=0)
    storage_path = Column(String(500), nullable=False)
    is_public = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))


class DatasetColumn(Base):
    __tablename__ = "dataset_columns"

    id = Column(Integer, primary_key=True, autoincrement=True)
    dataset_id = Column(Integer, ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False, index=True)
    column_name = Column(String(255), nullable=False)
    column_order = Column(Integer, nullable=False)
    dtype = Column(String(50), nullable=False)              # int | float | bool | datetime | str
    null_count = Column(Integer, nullable=False, default=0)
    unique_count = Column(Integer, nullable=False, default=0)
    min_value = Column(String(255), nullable=True)
    max_value = Column(String(255), nullable=True)
    sample_values = Column(Text, nullable=True)             # JSON 배열 문자열
