
from datetime import datetime, timedelta, timezone
import logging
from urllib.parse import quote_plus
from sqlalchemy import create_engine, desc
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker, Session
from entities.abc_brief_job_listing import BriefJobListing
from entities.abc_job_listing import JobListing
from models.configs.system_config import DatabaseConfig
from models.configs.universal_config import UniversalConfig
from models.db.base import Base
from models.db.brief_job_listing_orm import BriefJobListingORM
from models.db.job_listing_orm import JobListingORM
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

  def create_new_brief_job_listing(
    self,
    universal_config: UniversalConfig,
    brief_job_listing: BriefJobListing,
    platform: Platform
  ) -> None:
    brief_job_listing_orm = BriefJobListingORM(
      first_name=universal_config.about_me.name.first,
      last_name=universal_config.about_me.name.last,
      job_title=brief_job_listing.get_title(),
      company=brief_job_listing.get_company(),
      location=brief_job_listing.get_location(),
      min_pay=brief_job_listing.get_min_pay(),
      max_pay=brief_job_listing.get_max_pay(),
      platform=platform.value,
      ignore_category=brief_job_listing.get_ignore_category(),
      ignore_term=brief_job_listing.get_ignore_term()
    )
    session = self.get_session()
    entry = session.query(BriefJobListingORM).filter_by(
      first_name=brief_job_listing_orm.first_name,
      last_name=brief_job_listing_orm.last_name,
      job_title=brief_job_listing_orm.job_title,
      company=brief_job_listing_orm.company,
      location=brief_job_listing_orm.location,
      min_pay=brief_job_listing_orm.min_pay,
      max_pay=brief_job_listing_orm.max_pay,
      platform=platform.value,
      ignore_category=brief_job_listing_orm.ignore_category,
      ignore_term=brief_job_listing_orm.ignore_term
    ).first()
    if not entry:
      session.add(brief_job_listing_orm)
      session.commit()
    session.close()

  def create_new_job_listing(
    self,
    universal_config: UniversalConfig,
    job_listing: JobListing,
    url: str,
    platform: Platform
  ) -> None:
    applied = job_listing.get_ignore_category() is None and job_listing.get_ignore_term() is None
    job_listing_orm = JobListingORM(
      first_name=universal_config.about_me.name.first,
      last_name=universal_config.about_me.name.last,
      job_title=job_listing.get_title(),
      company=job_listing.get_company(),
      location=job_listing.get_location(),
      min_pay=job_listing.get_min_pay(),
      max_pay=job_listing.get_max_pay(),
      platform=platform.value,
      url=url,
      applied=applied,
      ignore_category=job_listing.get_ignore_category(),
      ignore_term=job_listing.get_ignore_term()
    )
    session = self.get_session()
    entry = session.query(JobListingORM).filter_by(
      first_name=job_listing_orm.first_name,
      last_name=job_listing_orm.last_name,
      job_title=job_listing_orm.job_title,
      company=job_listing_orm.company,
      location=job_listing_orm.location,
      min_pay=job_listing_orm.min_pay,
      max_pay=job_listing_orm.max_pay,
      min_yoe=job_listing_orm.min_yoe,
      max_yoe=job_listing_orm.max_yoe,
      description=job_listing_orm.description,
      platform=platform.value,
      applied=applied,
      ignore_category=job_listing_orm.ignore_category,
      ignore_term=job_listing_orm.ignore_term
    ).first()
    if entry:
      if entry.url != url:
        entry.url = url
        session.commit()
    else:
      session.add(job_listing_orm)
      session.commit()
    session.close()

  def log_rate_limit_block(self, ip_address: str, platform: Platform) -> None:
    logging.warning("Rate limited by %s on address: %s", platform.value, ip_address)
    rate_limit = RateLimitORM(
      ip_address=ip_address,
      platform=platform.value
    )
    session = self.get_session()
    session.add(rate_limit)
    session.commit()
    session.close()

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
    session.close()
    if last_rate_limit_from_host is None:
      return timedelta.max
    assert isinstance(last_rate_limit_from_host, RateLimitORM)
    last_logged_rate_limit_timestamp = last_rate_limit_from_host.timestamp
    assert isinstance(last_logged_rate_limit_timestamp, datetime)
    now = datetime.now(timezone.utc)
    time_delta = now - last_logged_rate_limit_timestamp
    return time_delta
