from datetime import datetime, timezone
from sqlalchemy import Column, DateTime, Float, Integer, String
from models.db.base import Base


class JobApplicationORM(Base):
  __tablename__ = 'job_applications'
  id = Column(Integer, primary_key=True)
  first_name = Column(String)
  last_name = Column(String)
  job_title = Column(String)
  company = Column(String)
  location = Column(String)
  min_pay = Column(Float, nullable=True)
  max_pay = Column(Float, nullable=True)
  url = Column(String)
  timestamp = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
