from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from datetime import datetime, timezone
from app.models.user_model import Base


class Chart(Base):
    __tablename__ = "charts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    dataset_id = Column(Integer, ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    title = Column(String(255), nullable=False)
    chart_type = Column(String(20), nullable=False)         # bar | line | pie | scatter | histogram
    x_column = Column(String(255), nullable=True)
    y_column = Column(String(255), nullable=True)
    config_json = Column(Text, nullable=True)               # JSON 문자열 (aggregation, color 등)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
