import logging
import time
from typing import List
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement
from selenium.common.exceptions import NoSuchElementException, StaleElementReferenceException
from entities.glassdoor_brief_job_listing import GlassdoorBriefJobListing
from entities.glassdoor_job_listing import GlassdoorJobListing
from models.configs.quick_settings import QuickSettings
from models.enums.element_type import ElementType
from models.configs.universal_config import UniversalConfig
from services.pages.indeed_apply_now_page.indeed_apply_now_page import IndeedApplyNowPage
from services.misc.selenium_helper import SeleniumHelper


class GlassdoorJobListingsPage:
  __driver: uc.Chrome
  __selenium_helper: SeleniumHelper
  __universal_config: UniversalConfig
  __quick_settings: QuickSettings
  __indeed_apply_now_page: IndeedApplyNowPage
  __jobs_applied_to_this_session: List[dict[str, str | float | None]]

  def __init__(
    self,
    driver: uc.Chrome,
    selenium_helper: SeleniumHelper,
    universal_config: UniversalConfig,
    quick_settings: QuickSettings,
    indeed_apply_now_page: IndeedApplyNowPage
  ):
    self.__driver = driver
    self.__selenium_helper = selenium_helper
    self.__universal_config = universal_config
    self.__quick_settings = quick_settings
    self.__indeed_apply_now_page = indeed_apply_now_page
    self.__jobs_applied_to_this_session = []

  def apply_to_all_matching_jobs(self) -> None:
    i = 0
    while True:
      i += 1
      logging.debug("Looping through job listings: %s...", i)
      try:
        job_listings_ul = self.__get_job_listings_ul()
      except NoSuchElementException:
        query_results_header_xpath = "/html/body/div[4]/div[4]/div[2]/div[1]/div[1]/span/div/h1"
        query_results_header = self.__driver.find_element(By.XPATH, query_results_header_xpath)
        query_results_header_text = query_results_header.text
        if query_results_header_text:
          assert query_results_header_text[0] == "0"
          logging.info("Query returned 0 results. Continuing to next query...")
          return
      try:
        job_listing_li = job_listings_ul.find_element(By.XPATH, f"./li[{i}]")
      except NoSuchElementException:
        try:
          show_more_jobs_button = self.__get_show_more_jobs_button()
        except NoSuchElementException:
          logging.info("Finished with this query. Continuing to next query...")
          return
        show_more_jobs_button.click()
        job_listings_ul = self.__get_job_listings_ul()
        while True:
          try:
            job_listing_li = job_listings_ul.find_element(By.XPATH, f"./li[{i}]")
            break
          except NoSuchElementException:
            self.__driver.execute_script("window.scrollBy(0, 50);")
      if not self.__is_job_listing(job_listing_li):
        continue
      brief_job_listing = GlassdoorBriefJobListing(job_listing_li)
      brief_job_listing.print()
      if brief_job_listing.should_be_ignored(self.__universal_config):
        continue
      if brief_job_listing.to_dict() in self.__jobs_applied_to_this_session:
        logging.info("Ignoring job listing because: we've already applied this session.\n")
        continue
      self.__remove_create_job_dialog()
      job_listing_li.click()
      job_listing = self.__build_job_listing(brief_job_listing)
      if job_listing.should_be_ignored(self.__universal_config):
        continue
      self.__apply_to_selected_job()
      self.__jobs_applied_to_this_session.append(brief_job_listing.to_dict())
      if len(self.__jobs_applied_to_this_session) % self.__quick_settings.bot_behavior.pause_every_x_jobs == 0:
        print("\nPausing to allow user to handle existing tabs before overload.")
        input("\tPress enter to proceed...")

  def __build_job_listing(self, brief_job_listing: GlassdoorBriefJobListing) -> GlassdoorJobListing:
    job_info_div = self.__get_job_info_div()
    try:
      job_listing = GlassdoorJobListing(brief_job_listing, job_info_div)
      return job_listing
    except StaleElementReferenceException:
      if not self.__job_info_div_is_present():
        if self.__page_didnt_load_is_present():
          self.__reload_job_description()
      job_info_div = self.__get_job_info_div()
      job_listing = GlassdoorJobListing(brief_job_listing, job_info_div)
      return job_listing

  def __job_info_div_is_present(self) -> bool:
    job_info_div_xpath = "/html/body/div[4]/div[4]/div[2]/div[2]/div/div[1]"
    try:
      self.__driver.find_element(By.XPATH, job_info_div_xpath)
      return True
    except NoSuchElementException:
      return False

  def __page_didnt_load_is_present(self) -> bool:
    return self.__selenium_helper.exact_text_is_present("Zzzzzzzz...", ElementType.H1)

  def __reload_job_description(self) -> None:
    try_again_span = self.__selenium_helper.get_element_by_exact_text("Try again", ElementType.SPAN)
    parent_span = try_again_span.find_element(By.XPATH, "..")
    try_again_button = parent_span.find_element(By.XPATH, "..")
    try_again_button.click()
    self.__wait_for_job_info_div()

  def __get_job_listings_ul(self) -> WebElement:
    job_listings_ul = self.__selenium_helper.get_element_by_aria_label("Jobs List", ElementType.UL)
    return job_listings_ul

  def __get_show_more_jobs_button(self) -> WebElement:
    try:
      show_more_jobs_span = self.__selenium_helper.get_element_by_exact_text("Show more jobs", ElementType.SPAN)
    except ValueError as e:
      raise NoSuchElementException("Show more jobs button is not present.") from e
    show_more_jobs_button = show_more_jobs_span.find_element(By.XPATH, "../..")
    return show_more_jobs_button

  def __apply_to_selected_job(self) -> None:
    logging.debug("Applying to selected job...")
    starting_window_count = len(self.__driver.window_handles)
    self.__remove_create_job_dialog()
    apply_button = self.__get_apply_button()
    if not apply_button:
      return    # Assumes this is a greyed out "Applied" job
    apply_button_text = apply_button.text
    if apply_button_text.lower().strip() == "applied":
      return
    if apply_button.is_enabled():
      apply_button.click()
    while len(self.__driver.window_handles) == starting_window_count:
      logging.debug("Waiting for new tab to open...")
      time.sleep(0.1)
    self.__driver.switch_to.window(self.__driver.window_handles[-1])
    self.__handle_potential_human_verification_wait()
    self.__handle_potential_too_many_requests()
    self.__handle_application(apply_button_text)
    self.__driver.switch_to.window(self.__driver.window_handles[0])

  def __get_apply_button(self) -> WebElement | None:
    easy_apply_button_selector = '[data-test="easyApply"]'
    apply_on_employer_site_button_selector = '[data-test="applyButton"]'
    job_info_div = self.__get_job_info_div()
    try:
      apply_button = job_info_div.find_element(By.CSS_SELECTOR, easy_apply_button_selector)
    except NoSuchElementException:
      try:
        apply_button = job_info_div.find_element(By.CSS_SELECTOR, apply_on_employer_site_button_selector)
      except NoSuchElementException:
        self.__selenium_helper.get_element_by_exact_text("Applied", ElementType.BUTTON)
        return None
    return apply_button

  def __wait_for_job_info_div(self, timeout=10) -> None:
    job_info_div_xpath = "/html/body/div[4]/div[4]/div[2]/div[2]/div/div[1]"
    start_time = time.time()
    while time.time() - start_time < timeout:
      try:
        self.__driver.find_element(By.XPATH, job_info_div_xpath)
        break
      except NoSuchElementException:
        logging.debug("Waiting for job info div to load...")
        time.sleep(0.1)

  def __get_job_info_div(self) -> WebElement:
    self.__wait_for_job_info_div()
    job_info_div_xpath = "/html/body/div[4]/div[4]/div[2]/div[2]/div/div[1]"
    job_info_div = self.__driver.find_element(By.XPATH, job_info_div_xpath)
    return job_info_div

  def __handle_application(self, apply_button_text: str) -> None:
    if apply_button_text.lower().strip() == "easy apply":
      self.__easy_apply()
      return
    elif apply_button_text.lower().strip() == "apply on employer site":
      return
    elif apply_button_text.lower().strip() == "applied":
      return
    raise RuntimeError(f"Apply button text did not match any expected conditions: {apply_button_text}")

  def __easy_apply(self) -> None:
    logging.debug("Executing easy apply...")
    self.__indeed_apply_now_page.apply()

  def __remove_create_job_dialog(self) -> None:
    create_job_alert_dialog_xpath = "/html/body/div[8]/div/dialog"
    relative_cancel_dialog_button_xpath = "./div[2]/div[1]/div[1]/button[1]"
    try:
      create_job_alert_dialog = self.__driver.find_element(By.XPATH, create_job_alert_dialog_xpath)
      cancel_button = create_job_alert_dialog.find_element(By.XPATH, relative_cancel_dialog_button_xpath)
      logging.debug("Removing create job dialog...")
      cancel_button.click()
    except NoSuchElementException:
      pass

  def __handle_potential_human_verification_wait(self) -> None:
    while self.__selenium_helper.exact_text_is_present(
      "Additional Verification Required",
      ElementType.H1
    ):
      logging.debug("Waiting for user to handle captcha...")
      time.sleep(0.5)

  def __handle_potential_too_many_requests(self) -> None:
    while self.__selenium_helper.exact_text_is_present(
      "Too Many Requests",
      ElementType.H1
    ):
      # TODO: Implement proxy swap
      input("Heck, rate limited...")

  def __is_job_listing(self, element: WebElement) -> bool:
    attr = element.get_attribute("data-test")
    result = attr is not None and "jobListing" in attr
    logging.debug("Checked if is job listing -- %s", result)
    return result
