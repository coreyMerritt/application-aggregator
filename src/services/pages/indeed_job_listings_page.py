import logging
import time
from typing import List, Optional
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement
from selenium.common.exceptions import (
  NoSuchElementException
)
from entities.indeed_brief_job_listing import IndeedBriefJobListing
from entities.indeed_job_listing import IndeedJobListing
from models.configs.indeed_config import IndeedConfig
from models.configs.quick_settings import QuickSettings
from models.configs.universal_config import UniversalConfig
from models.enums.element_type import ElementType
from services.misc.selenium_helper import SeleniumHelper
from services.pages.indeed_apply_now_page.indeed_apply_now_page import IndeedApplyNowPage


class IndeedJobListingsPage:
  __driver: uc.Chrome
  __selenium_helper: SeleniumHelper
  __universal_config: UniversalConfig
  __quick_settings: QuickSettings
  __indeed_config: IndeedConfig
  __apply_now_page: IndeedApplyNowPage
  __jobs_applied_to_this_session: List[dict[str, str | float | None]]
  __current_page_number: int

  def __init__(
    self,
    driver: uc.Chrome,
    selenium_helper: SeleniumHelper,
    universal_config: UniversalConfig,
    quick_settings: QuickSettings,
    indeed_config: IndeedConfig
  ):
    self.__driver = driver
    self.__selenium_helper = selenium_helper
    self.__universal_config = universal_config
    self.__quick_settings = quick_settings
    self.__indeed_config = indeed_config
    self.__apply_now_page = IndeedApplyNowPage(driver, selenium_helper, universal_config)
    self.__jobs_applied_to_this_session = []
    self.__current_page_number = 1

  def is_present(self) -> bool:
    try:
      self.__get_job_listings_ul()
      return True
    except NoSuchElementException:
      return False

  def apply_to_all_matching_jobs(self) -> None:
    PROPER_JOB_INDEXES = [2, 3, 4, 5, 6, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18]
    INVISIBLE_AD_INDEXES = [1, 19]
    VISIBLE_AD_INDEXES = [7]
    LIS_PER_PAGE = len(PROPER_JOB_INDEXES) + len(INVISIBLE_AD_INDEXES) + len(VISIBLE_AD_INDEXES)
    i = 0
    while True:
      i += 1
      job_listing_li_number = (i % LIS_PER_PAGE) + 1
      JOB_IS_ON_NEXT_PAGE = i > 1 and job_listing_li_number == 1
      if JOB_IS_ON_NEXT_PAGE:
        if self.__is_a_next_page():
          self.__go_to_next_page()
        else:
          logging.info("End of job listings.")
          return
      elif job_listing_li_number in INVISIBLE_AD_INDEXES + VISIBLE_AD_INDEXES:
        continue  # Don't try to run against ads
      job_listing_li = self.__get_job_listing_li(job_listing_li_number)
      if job_listing_li is None:
        logging.info("End of job listings.")
        return
      brief_job_listing = self.__build_brief_job_listing(job_listing_li)
      if brief_job_listing is None:
        logging.debug("Skipping a fake job listing / advertisement...")
        continue
      BRIEF_JOB_SHOULD_BE_IGNORED = brief_job_listing.should_be_ignored(self.__universal_config)
      if BRIEF_JOB_SHOULD_BE_IGNORED:
        continue
      ALREADY_APPLIED_THIS_SESSION = brief_job_listing.to_dict() in self.__jobs_applied_to_this_session
      if ALREADY_APPLIED_THIS_SESSION:
        logging.info("Ignoring job listing because: we've already applied this session.\n")
        continue
      brief_job_listing.print()
      self.__open_job_in_new_tab(job_listing_li)
      try:
        self.__wait_for_new_job_tab_to_load()
      except RuntimeError:
        logging.debug("Some HTTP error... Skipping this job...")
        self.__driver.close()
        self.__driver.switch_to.window(self.__driver.window_handles[0])
        continue
      job_listing = self.__build_job_listing(brief_job_listing)
      if job_listing.should_be_ignored(self.__universal_config):
        self.__driver.close()
        self.__driver.switch_to.window(self.__driver.window_handles[0])
        continue
      while not self.__is_apply_now_span() and not self.__is_apply_on_company_site_span():
        logging.debug("Waiting for apply button...")
        time.sleep(0.5)
      self.__apply_to_job(brief_job_listing)
      self.__driver.switch_to.window(self.__driver.window_handles[0])
      self.__handle_potential_overload()

  def __build_brief_job_listing(self, job_listing_li: WebElement) -> Optional[IndeedBriefJobListing]:
    try:
      brief_job_listing = IndeedBriefJobListing(job_listing_li)
      return brief_job_listing
    except NoSuchElementException:
      return None

  def __get_job_listing_link(self, job_listing_li: WebElement) -> str:
    job_listing_anchor = self.__get_job_listing_anchor(job_listing_li)
    job_listing_link = job_listing_anchor.get_attribute("href")
    assert job_listing_link
    assert isinstance(job_listing_link, str)
    return job_listing_link

  def __open_job_in_new_tab(self, job_listing_li: WebElement) -> None:
    job_listing_link = self.__get_job_listing_link(job_listing_li)
    self.__selenium_helper.open_new_tab()
    self.__driver.get(job_listing_link)

  def __wait_for_new_job_tab_to_load(self, timeout=10) -> None:
    start_time = time.time()
    while time.time() - start_time < timeout:
      if self.__selenium_helper.exact_text_is_present(
        "Profile insights",
        ElementType.H2
      ):
        return
      elif self.__selenium_helper.exact_text_is_present(
        "We can’t find this page",
        ElementType.H1
      ):
        raise RuntimeError("Failed to arrive at new job tab... \"We can't find this page\".")
      logging.debug("Waiting for page to load...")
      time.sleep(0.5)

  def __build_job_listing(self, brief_job_listing: IndeedBriefJobListing) -> IndeedJobListing:
    job_description_html = self.__get_job_description_html()
    job_listing = IndeedJobListing(brief_job_listing, job_description_html)
    return job_listing

  def __apply_to_job(self, brief_job_listing: IndeedBriefJobListing) -> None:
    if self.__is_apply_now_span():
      self.__click_apply_now_button()
      self.__apply_now_page.apply()
      self.__jobs_applied_to_this_session.append(brief_job_listing.to_dict())
      return
    elif self.__is_apply_on_company_site_span():
      if not self.__indeed_config.apply_now_only:
        self.__go_to_company_site()
        self.__jobs_applied_to_this_session.append(brief_job_listing.to_dict())
      else:
        self.__driver.close()
      return
    elif self.__is_applied_span():
      return
    raise RuntimeError("Tried to apply to a job, but expected conditions were not met regarding the apply button.")
  # def __apply_to_visible_job(self) -> None:
  #   if self.__is_apply_now_button():
  #     starting_tab_count = len(self.__driver.window_handles)
  #     while len(self.__driver.window_handles) == starting_tab_count:
  #       logging.debug("Attempting to click the apply now button...")
  #       while True:
  #         try:
  #           apply_now_button = self.__get_apply_now_button()
  #           apply_now_button.click()
  #           break
  #         except StaleElementReferenceException:
  #           logging.debug("Apply button reference is stale. Trying again...")
  #           time.sleep(0.5)
  #       time.sleep(0.5)
  #     self.__driver.switch_to.window(self.__driver.window_handles[-1])
  #     self.__apply_now_page.apply()
  #     self.__driver.switch_to.window(self.__driver.window_handles[0])
  #   elif self.__is_apply_on_company_site_span():
  #     apply_on_company_site_button = self.__get_apply_on_company_site_button()
  #     while True:
  #       try:
  #         apply_on_company_site_button.click()
  #         break
  #       except ElementClickInterceptedException:
  #         logging.debug("Failed to click apply on company site button. Trying again...")
  #         self.__remove_did_you_apply_popup()
  #         time.sleep(0.1)
  #     # Ignore page and allow user to come back later
  #     self.__driver.switch_to.window(self.__driver.window_handles[0])

  def __handle_potential_overload(self) -> None:
    if len(self.__jobs_applied_to_this_session) > 0:
      if len(self.__jobs_applied_to_this_session) % self.__quick_settings.bot_behavior.pause_every_x_jobs == 0:
        print("\nPausing to allow user to handle existing tabs before overload.")
        input("\tPress enter to proceed...")

  def __is_a_next_page(self) -> bool:
    visible_page_numbers = self.__get_visible_page_numbers()
    current_page_number = self.__get_current_page_number()
    if current_page_number + 1 in visible_page_numbers:
      return True
    return False

  def __go_to_next_page(self) -> None:
    logging.info("Going to page %s...", self.__current_page_number + 1)
    next_page_anchor = self.__get_next_page_anchor()
    next_page_anchor.click()
    self.__current_page_number += 1

  def __get_job_listing_li(self, index: int) -> Optional[WebElement]:
    try:
      job_listings_ul = self.__get_job_listings_ul()
      job_listing_li = job_listings_ul.find_element(By.XPATH, f"./li[{index}]")
      return job_listing_li
    except NoSuchElementException:
      return None

  def __get_job_listings_ul(self) -> WebElement:
    potential_job_listings_ul_xpaths = [
      "/html/body/main/div/div[2]/div/div[5]/div/div[1]/div[4]/div/ul",
      "/html/body/main/div/div/div[2]/div/div[5]/div/div[1]/div[4]/div/div/ul"
    ]
    for xpath in potential_job_listings_ul_xpaths:
      try:
        job_listings_ul = self.__driver.find_element(By.XPATH, xpath)
        return job_listings_ul
      except NoSuchElementException:
        pass
    raise NoSuchElementException("Failed to find job listings ul.")

  def __get_next_page_anchor(self) -> WebElement:
    page_buttons_ul = self.__get_page_buttons_ul()
    current_page_number = self.__get_current_page_number()
    for i in range(1, 7):
      potential_relative_next_page_anchor_xpath = f"./li[{i}]/a[1]"
      potential_next_page_anchor = page_buttons_ul.find_element(By.XPATH, potential_relative_next_page_anchor_xpath)
      potential_next_page_anchor_text = potential_next_page_anchor.text
      if potential_next_page_anchor_text:
        if potential_next_page_anchor_text == str(current_page_number + 1):
          return potential_next_page_anchor
    raise NoSuchElementException("Failed to find next page anchor.")

  def __get_visible_page_numbers(self) -> List[int]:
    page_buttons_ul = self.__get_page_buttons_ul()
    visible_page_numbers = []
    for i in range(1, 6):
      relative_anchor_xpath = f"./li[{i}]/a[1]"
      try:
        page_anchor = page_buttons_ul.find_element(By.XPATH, relative_anchor_xpath)
      except NoSuchElementException:
        continue
      page_anchor_text = page_anchor.text
      if page_anchor_text:
        visible_page_numbers.append(int(page_anchor_text))
    return visible_page_numbers

  def __get_current_page_number(self) -> int:
    return self.__current_page_number

  def __get_page_buttons_ul(self, timeout=5) -> WebElement:
    page_buttons_ul_xpath = "/html/body/main/div/div[2]/div/div[5]/div/div[1]/nav/ul"
    start_time = time.time()
    while time.time() - start_time < timeout:
      try:
        page_buttons_ul = self.__driver.find_element(By.XPATH, page_buttons_ul_xpath)
        return page_buttons_ul
      except NoSuchElementException:
        logging.debug("Failed to find page buttons ul. Trying again...")
        time.sleep(0.1)
    raise NoSuchElementException("Failed to find page buttons ul.")

  def __get_job_listing_anchor(self, job_listing_li: WebElement) -> WebElement:
    relative_job_listing_anchor_xpath = "./div/div/div/div/div/div/table/tbody/tr/td/div[1]/h2/a"
    job_listing_anchor = job_listing_li.find_element(By.XPATH, relative_job_listing_anchor_xpath)
    return job_listing_anchor

  def __get_job_description_html(self, timeout=30) -> str:
    job_description_id = "jobDescriptionText"
    start_time = time.time()
    while time.time() - start_time < timeout:
      try:
        job_description_div = self.__driver.find_element(By.ID, job_description_id)
        break
      except NoSuchElementException:
        logging.debug("Failed to get job description div. Trying again...")
        time.sleep(0.5)
    job_description_html = job_description_div.get_attribute("innerHTML")
    if job_description_html:
      return job_description_html
    raise AttributeError("Job description div has no innerHTML attribute.")

  def __is_applied_span(self) -> bool:
    return self.__selenium_helper.exact_text_is_present(
      "Applied",
      ElementType.SPAN
    )

  def __is_apply_now_span(self) -> bool:
    return self.__selenium_helper.exact_text_is_present(
      "Apply now",
      ElementType.SPAN
    )

  def __get_apply_now_button(self) -> WebElement:
    assert self.__is_apply_now_span()
    apply_now_span = self.__selenium_helper.get_element_by_exact_text(
      "Apply now",
      ElementType.SPAN
    )
    apply_now_button = apply_now_span.find_element(By.XPATH, "../..")
    return apply_now_button

  def __click_apply_now_button(self) -> None:
    self.__get_apply_now_button().click()

  def __is_apply_on_company_site_span(self) -> bool:
    return self.__selenium_helper.exact_text_is_present(
      "Apply on company site",
      ElementType.SPAN
    )

  def __get_apply_on_company_site_button(self) -> WebElement:
    assert self.__is_apply_on_company_site_span()
    apply_now_span = self.__selenium_helper.get_element_by_exact_text(
      "Apply on company site",
      ElementType.SPAN
    )
    apply_now_button = apply_now_span.find_element(By.XPATH, "..")
    return apply_now_button

  def __go_to_company_site(self) -> None:
    apply_on_company_site_button = self.__get_apply_on_company_site_button()
    company_site_link = apply_on_company_site_button.get_attribute("href")
    assert company_site_link
    self.__driver.get(company_site_link)
