
from datetime import datetime, timedelta, timezone
import logging
from typing import List, Tuple
from urllib.parse import quote_plus
from sqlalchemy import create_engine, desc, func
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker, Session
from entities.abc_job_listing import JobListing
from models.configs.system_config import DatabaseConfig
from models.configs.universal_config import UniversalConfig
from models.db.application_orm import ApplicationORM
from models.db.base import Base
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

  def create_new_job_listing(
    self,
    job_listing: JobListing,
    platform: Platform
  ) -> None:
    job_listing_orm = self.__build_job_listing_orm(job_listing, platform)
    with self.get_session() as session:
      job_listing_entry = session.query(JobListingORM).filter_by(
        job_title=job_listing_orm.job_title,
        company=job_listing_orm.company,
        location=job_listing_orm.location,
        platform=platform.value,
      ).first()
      if job_listing_entry:
        if job_listing_entry.min_pay != job_listing.get_min_pay():
          job_listing_entry.min_pay = job_listing.get_min_pay()
        if job_listing_entry.max_pay != job_listing.get_max_pay():
          job_listing_entry.max_pay = job_listing.get_max_pay()
        if job_listing_entry.min_yoe != job_listing.get_min_yoe():
          job_listing_entry.min_yoe = job_listing.get_min_yoe()
        if job_listing_entry.max_yoe != job_listing.get_max_yoe():
          job_listing_entry.max_yoe = job_listing.get_max_yoe()
        if job_listing_entry.description != job_listing.get_description():
          job_listing_entry.description = job_listing.get_description()
        if job_listing_entry.url != job_listing.get_url():
          job_listing_entry.url = job_listing.get_url()
        session.commit()
      else:
        session.add(job_listing_orm)
        session.commit()

  def create_new_application(
    self,
    universal_config: UniversalConfig,
    job_listing: JobListing,
    platform: Platform
  ) -> None:
    applied = job_listing.get_ignore_category() is None and job_listing.get_ignore_term() is None
    with self.get_session() as session:
      job_listing_orm = session.query(JobListingORM).filter_by(
        job_title=job_listing.get_title(),
        company=job_listing.get_company(),
        location=job_listing.get_location(),
        platform=platform.value
      ).first()
      if not job_listing_orm:
        job_listing_orm = self.__build_job_listing_orm(job_listing, platform)
        session.add(job_listing_orm)
        session.flush()
      application_orm = ApplicationORM(
        first_name=universal_config.about_me.name.first,
        last_name=universal_config.about_me.name.last,
        applied=applied,
        ignore_category=job_listing.get_ignore_category(),
        ignore_term=job_listing.get_ignore_term(),
        job_listing=job_listing_orm
      )
      application_entry = session.query(ApplicationORM).filter_by(
        first_name=application_orm.first_name,
        last_name=application_orm.last_name,
        applied=applied,
        ignore_category=application_orm.ignore_category,
        ignore_term=application_orm.ignore_term,
        job_listing_id=job_listing_orm.id
      ).first()
      if not application_entry:
        session.add(application_orm)
        session.commit()

  def get_highest_job_listing_ignore_keywords(self, limit=10) -> List[Tuple[str, str, int]]:
    with self.get_session() as session:
      top_ignore_terms_query = (
        session.query(
          JobListingORM.ignore_category,
          JobListingORM.ignore_term,
          func.count(JobListingORM.id).label("count")    # pylint: disable=not-callable
        )
        .filter(JobListingORM.ignore_category.isnot(None))
        .filter(JobListingORM.ignore_term.isnot(None))
        .group_by(
          JobListingORM.ignore_category,
          JobListingORM.ignore_term
        )
        .order_by(func.count(JobListingORM.id).desc())   # pylint: disable=not-callable
        .limit(limit)
      )
      top_ignore_terms = top_ignore_terms_query.all()
      return top_ignore_terms

  def log_rate_limit_block(self, ip_address: str, platform: Platform) -> None:
    logging.warning("Rate limited by %s on address: %s", platform.value, ip_address)
    rate_limit = RateLimitORM(
      ip_address=ip_address,
      platform=platform.value
    )
    with self.get_session() as session:
      session.add(rate_limit)
      session.commit()

  def get_rate_limit_time_delta(self, ip_address: str, platform: Platform | None = None) -> timedelta:
    with self.get_session() as session:
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

  def __build_job_listing_orm(self, job_listing: JobListing, platform: Platform) -> JobListingORM:
    job_listing_orm = JobListingORM(
      job_title=job_listing.get_title(),
      company=job_listing.get_company(),
      location=job_listing.get_location(),
      min_pay=job_listing.get_min_pay(),
      max_pay=job_listing.get_max_pay(),
      min_yoe=job_listing.get_min_yoe(),
      max_yoe=job_listing.get_max_yoe(),
      description=job_listing.get_description(),
      platform=platform.value,
      url=job_listing.get_url()
    )
    return job_listing_orm
