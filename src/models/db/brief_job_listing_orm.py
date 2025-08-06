from datetime import datetime, timezone
from sqlalchemy import Column, DateTime, Float, Integer, String
from models.db.base import Base


class BriefJobListingORM(Base):
  __tablename__ = 'brief_job_listings'
  id = Column(Integer, primary_key=True)
  first_name = Column(String)
  last_name = Column(String)
  job_title = Column(String)
  company = Column(String)
  location = Column(String)
  min_pay = Column(Float, nullable=True)
  max_pay = Column(Float, nullable=True)
  platform = Column(String)
  url = Column(String)
  ignore_category = Column(String, nullable=True)
  ignore_term = Column(String, nullable=True)
  timestamp = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
