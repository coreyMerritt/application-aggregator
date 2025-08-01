import logging
import time
import undetected_chromedriver as uc
from models.configs.linkedin_config import LinkedinConfig
from models.configs.quick_settings import QuickSettings
from models.configs.universal_config import UniversalConfig
from services.misc.database_manager import DatabaseManager
from services.misc.proxy_manager import ProxyManager
from services.misc.selenium_helper import SeleniumHelper
from services.pages.linkedin_login_page import LinkedinLoginPage
from services.pages.linkedin_job_listings_page import LinkedinJobListingsPage
from services.query_url_builders.linkedin_query_url_builder import LinkedinQueryUrlBuilder


class LinkedinOrchestrationEngine:
  __driver: uc.Chrome
  __linkedin_config: LinkedinConfig
  __universal_config: UniversalConfig
  __database_manager: DatabaseManager
  __linkedin_login_page: LinkedinLoginPage
  __linkedin_job_listings_page: LinkedinJobListingsPage

  def __init__(
    self,
    driver: uc.Chrome,
    selenium_helper: SeleniumHelper,
    database_manager: DatabaseManager,
    universal_config: UniversalConfig,
    quick_settings: QuickSettings,
    linkedin_config: LinkedinConfig,
    proxy_manager: ProxyManager
  ):
    self.__driver = driver
    self.__linkedin_config = linkedin_config
    self.__universal_config = universal_config
    self.__linkedin_login_page = LinkedinLoginPage(
      driver,
      selenium_helper,
      linkedin_config
    )
    self.__linkedin_job_listings_page = LinkedinJobListingsPage(
      driver,
      selenium_helper,
      database_manager,
      universal_config,
      quick_settings,
      linkedin_config,
      proxy_manager
    )

  def apply(self):
    logging.debug("Applying...")
    self.__linkedin_login_page.login()
    query_terms = self.__universal_config.search.terms.match
    if not query_terms or len(query_terms) == 0:
      query_terms = [""]
    for search_term in query_terms:
      self.__go_to_query(search_term)
      self.__linkedin_job_listings_page.apply_to_all_matching_jobs()

  def __go_to_query(self, search_term: str) -> None:
    query_url_builder = LinkedinQueryUrlBuilder(self.__linkedin_config, self.__universal_config)
    query_url = query_url_builder.build(search_term)
    logging.debug("Going to %s", query_url)
    self.__driver.get(query_url)
    while not 'linkedin.com/jobs/search-results' in self.__driver.current_url:
      logging.debug("Waiting for url to include: linkedin.com/jobs/search-results...")
      time.sleep(0.5)
