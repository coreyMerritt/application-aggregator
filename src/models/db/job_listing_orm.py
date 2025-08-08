from datetime import datetime, timezone
from sqlalchemy import Column, DateTime, Float, Integer, String
from sqlalchemy.orm import relationship
from models.db.base import Base


class JobListingORM(Base):
  __tablename__ = 'job_listings'
  id = Column(Integer, primary_key=True)
  job_title = Column(String)
  company = Column(String)
  location = Column(String)
  min_pay = Column(Float, nullable=True)
  max_pay = Column(Float, nullable=True)
  min_yoe = Column(Integer, nullable=True)
  max_yoe = Column(Integer, nullable=True)
  description = Column(String)
  platform = Column(String)
  url = Column(String)
  timestamp = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
  applications = relationship("ApplicationORM", back_populates="job_listing")
