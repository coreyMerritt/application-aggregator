
from datetime import datetime, timedelta, timezone
from urllib.parse import quote_plus
from sqlalchemy import create_engine, desc
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker, Session
from entities.abc_brief_job_listing import BriefJobListing
from models.configs.system_config import DatabaseConfig
from models.configs.universal_config import UniversalConfig
from models.db.base import Base
from models.db.job_application import JobApplicationORM
from models.db.rate_limit import RateLimitORM
from models.enums.platform import Platform



class DatabaseManager:
  __engine: Engine
  __session_factory: sessionmaker

  def __init__(self, database_config: DatabaseConfig):
    engine = database_config.engine
    username = database_config.username

    password = quote_plus(database_config.password)
    host = database_config.host
    port = database_config.port
    name = database_config.name
    self.__engine = create_engine(f"{engine}://{username}:{password}@{host}:{port}/{name}")
    Base.metadata.create_all(self.__engine)
    self.__session_factory = sessionmaker(bind=self.__engine)

  def get_session(self) -> Session:
    return self.__session_factory()

  def create_new_job_application_entry(
    self,
    universal_config: UniversalConfig,
    brief_job_listing: BriefJobListing,
    url: str,
    platform: Platform
  ) -> None:
    job_application = JobApplicationORM(
      first_name=universal_config.about_me.name.first,
      last_name=universal_config.about_me.name.last,
      job_title=brief_job_listing.get_title(),
      company=brief_job_listing.get_company(),
      location=brief_job_listing.get_location(),
      min_pay=brief_job_listing.get_min_pay(),
      max_pay=brief_job_listing.get_max_pay(),
      platform=platform.value,
      url=url
    )
    session = self.get_session()
    ENTRY_EXISTS = session.query(JobApplicationORM).filter_by(
      first_name=job_application.first_name,
      last_name=job_application.last_name,
      job_title=job_application.job_title,
      company=job_application.company,
      location=job_application.location,
      min_pay=job_application.min_pay,
      max_pay=job_application.max_pay
    ).first()
    if not ENTRY_EXISTS:
      session.add(job_application)
      session.commit()

  def log_rate_limit_block(self, ip_address: str, platform: Platform) -> None:
    rate_limit = RateLimitORM(
      ip_address=ip_address,
      platform=platform.value
    )
    session = self.get_session()
    session.add(rate_limit)
    session.commit()

  def get_rate_limit_time_delta(self, ip_address: str, platform: Platform | None = None) -> timedelta:
    session = self.get_session()
    if platform:
      last_rate_limit_from_host = (
        session.query(RateLimitORM)
          .filter(RateLimitORM.ip_address == ip_address)
          .filter(RateLimitORM.platform == platform.value)
          .order_by(desc(RateLimitORM.timestamp))
          .first()
      )
    else:
      last_rate_limit_from_host = (
        session.query(RateLimitORM)
          .filter(RateLimitORM.ip_address == ip_address)
          .order_by(desc(RateLimitORM.timestamp))
          .first()
      )
    if last_rate_limit_from_host is None:
      return timedelta.max
    assert isinstance(last_rate_limit_from_host, RateLimitORM)
    last_logged_rate_limit_timestamp = last_rate_limit_from_host.timestamp
    assert isinstance(last_logged_rate_limit_timestamp, datetime)
    now = datetime.now(timezone.utc)
    time_delta = now - last_logged_rate_limit_timestamp
    return time_delta
