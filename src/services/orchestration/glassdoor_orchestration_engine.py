import logging
import undetected_chromedriver as uc
from selenium.common.exceptions import TimeoutException
from models.configs.glassdoor_config import GlassdoorConfig
from models.configs.quick_settings import QuickSettings
from models.configs.universal_config import UniversalConfig
from services.query_url_builders.glassdoor_query_url_builder import GlassdoorQueryUrlBuilder
from services.misc.selenium_helper import SeleniumHelper
from services.pages.indeed_apply_now_page.indeed_apply_now_page import IndeedApplyNowPage
from services.pages.glassdoor_login_page import GlassdoorLoginPage
from services.pages.glassdoor_job_listings_page import GlassdoorJobListingsPage


class GlassdoorOrchestrationEngine:
  __driver: uc.Chrome
  __universal_config: UniversalConfig
  __glassdoor_login_page: GlassdoorLoginPage
  __glassdoor_job_listings_page: GlassdoorJobListingsPage

  def __init__(
    self,
    driver: uc.Chrome,
    selenium_helper: SeleniumHelper,
    universal_config: UniversalConfig,
    quick_settings: QuickSettings,
    glassdoor_config: GlassdoorConfig,
    indeed_apply_now_page: IndeedApplyNowPage
  ):
    self.__driver = driver
    self.__universal_config = universal_config
    self.__glassdoor_login_page = GlassdoorLoginPage(driver, selenium_helper, glassdoor_config)
    self.__glassdoor_job_listings_page = GlassdoorJobListingsPage(
      driver,
      selenium_helper,
      universal_config,
      quick_settings,
      indeed_apply_now_page
    )

  def apply(self):
    logging.debug("Applying on Glassdoor...")
    self.__glassdoor_login_page.login()
    search_terms = self.__universal_config.search.terms.match
    for search_term in search_terms:
      query_builder = GlassdoorQueryUrlBuilder(self.__universal_config)
      query_url = query_builder.build(search_term)
      self.__go_to_query_url(query_url)
      self.__glassdoor_job_listings_page.apply_to_all_matching_jobs()

  def __go_to_query_url(self, url: str) -> None:
    logging.debug("Going to query url: %s...", url)
    try:
      self.__driver.get(url)
    except TimeoutException:
      pass
