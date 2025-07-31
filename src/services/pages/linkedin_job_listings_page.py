import logging
import math
import time
from typing import List, Tuple
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement
from selenium.common.exceptions import (
  ElementClickInterceptedException,
  ElementNotInteractableException,
  NoSuchElementException,
  StaleElementReferenceException
)
from entities.linkedin_brief_job_listing import LinkedinBriefJobListing
from entities.linkedin_job_listing import LinkedinJobListing
from models.configs.quick_settings import QuickSettings
from models.enums.element_type import ElementType
from models.configs.linkedin_config import LinkedinConfig
from models.configs.universal_config import UniversalConfig
from services.misc.database_manager import DatabaseManager
from services.pages.linkedin_apply_now_page.linkedin_apply_now_page import LinkedinApplyNowPage
from services.misc.selenium_helper import SeleniumHelper


class LinkedinJobListingsPage:
  __driver: uc.Chrome
  __selenium_helper: SeleniumHelper
  __universal_config: UniversalConfig
  __quick_settings: QuickSettings
  __database_manager: DatabaseManager
  __linkedin_apply_now_page: LinkedinApplyNowPage
  __jobs_applied_to_this_session: List[dict[str, str]]

  def __init__(
    self,
    driver: uc.Chrome,
    selenium_helper: SeleniumHelper,
    database_manager: DatabaseManager,
    universal_config: UniversalConfig,
    quick_settings: QuickSettings,
    linkedin_config: LinkedinConfig
  ):
    self.__driver = driver
    self.__selenium_helper = selenium_helper
    self.__database_manager = database_manager
    self.__universal_config = universal_config
    self.__quick_settings = quick_settings
    self.__linkedin_apply_now_page = LinkedinApplyNowPage(
      driver,
      selenium_helper,
      universal_config,
      linkedin_config
    )
    self.__jobs_applied_to_this_session = []

  def apply_to_all_matching_jobs(self) -> None:
    total_jobs_tried = 0
    job_listing_li_index = 0
    while True:
      total_jobs_tried, job_listing_li_index = self.__handle_incrementors(total_jobs_tried, job_listing_li_index)
      # try:
      self.__handle_page_context(total_jobs_tried)
      # except NoSuchElementException:
      #   logging.info("\tUnable to find next page button, assuming we've handled all job listings.")
      #   return
      if self.__is_no_matching_jobs_page():
        logging.info("No matching jobs... Ending query.")
        return
      job_listing_li = self.__get_job_listing_li(job_listing_li_index)
      if job_listing_li is None:
        logging.info("No job listings left -- Finished")
        return
      brief_job_listing = self.__build_new_brief_job_listing(job_listing_li)
      brief_job_listing.print()
      if not brief_job_listing.passes_filter_check(self.__universal_config, self.__quick_settings):
        logging.info("Ignoring brief job listing because it doesn't pass the filter check. Skipping...")
        continue
      if brief_job_listing.to_minimal_dict() in self.__jobs_applied_to_this_session:
        logging.info("Ignoring brief job listing because we've already applied this session. Skipping...")
        continue
      self.__select_job(job_listing_li)
      job_listing = self.__build_new_job_listing(brief_job_listing)
      if not job_listing.passes_filter_check(self.__universal_config, self.__quick_settings):
        logging.info("Ignoring job listing because it doesn't pass the filter check. Skipping...")
        continue
      if not self.__is_apply_button():
        logging.info("This job listing has no apply button. Skipping...")
        continue
      self.__apply_to_selected_job()
      self.__driver.switch_to.window(self.__driver.window_handles[0])
      self.__jobs_applied_to_this_session.append(brief_job_listing.to_minimal_dict())
      self.__database_manager.create_new_job_application_entry(
        self.__universal_config,
        brief_job_listing,
        self.__driver.current_url,
        "Linkedin"
      )
      self.__handle_potential_overload()

  def __handle_incrementors(self, total_jobs_tried: int, job_listing_li_index: int) -> Tuple[int, int]:
    total_jobs_tried += 1
    if total_jobs_tried >= 4:
      self.__selenium_helper.scroll_down(self.__get_job_listings_ul())
    job_listing_li_index = total_jobs_tried % 26
    if job_listing_li_index == 0:
      total_jobs_tried += 1
      job_listing_li_index = 1
    return (total_jobs_tried, job_listing_li_index)

  def __select_job(self, job_listing_li: WebElement, timeout=60) -> None:
    full_job_details_div = self.__get_full_job_details_div()
    assert full_job_details_div
    previous_job_details_html = full_job_details_div.get_attribute("innerHTML")
    assert previous_job_details_html
    self.__selenium_helper.scroll_into_view(job_listing_li)
    self.__click_job_listing_li(job_listing_li)
    start_time = time.time()
    while time.time() - start_time < timeout:
      try:
        full_job_details_div = self.__get_full_job_details_div()
        assert full_job_details_div
        if full_job_details_div.get_attribute("innerHTML") != previous_job_details_html:
          return
        logging.debug("Waiting for full job listing to load...")
        time.sleep(0.5)
      except TimeoutError:
        self.__selenium_helper.scroll_into_view(job_listing_li)
        self.__click_job_listing_li(job_listing_li)
      except NoSuchElementException:
        self.__handle_potential_problems()
    raise TimeoutError("Timed out waiting for full job listing to load.")

  def __click_job_listing_li(self, job_listing_li: WebElement) -> None:
    while True:
      try:
        job_listing_li.click()
        break
      except ElementClickInterceptedException:
        self.__handle_potential_problems()
        logging.debug("Attempting to click job listing li...")
        time.sleep(0.1)

  def __handle_page_context(self, total_jobs_tried: int) -> None:
    if total_jobs_tried > 26 and total_jobs_tried % 26 == 1:
      logging.info("Attempting to go to page: %s...", math.ceil(total_jobs_tried / 26))
      next_page_span = self.__get_next_page_span()
      while True:
        try:
          next_page_span.click()
          return
        except ElementNotInteractableException:
          logging.debug("Failed to click next page span... Scrolling down and trying again...")
          self.__selenium_helper.scroll_down(self.__get_job_listings_ul())
          time.sleep(0.1)

  def __apply_to_selected_job(self) -> None:
    logging.info("Applying to job...")
    self.__wait_for_apply_button()
    apply_button = self.__get_apply_button()
    apply_button_text = apply_button.text
    assert apply_button_text
    apply_button_text = apply_button_text.lower().strip()
    application_is_on_linkedin = apply_button_text.lower() == "easy apply"
    if application_is_on_linkedin:
      self.__apply_in_new_tab()
      return
    elif not application_is_on_linkedin:
      starting_tab_count = len(self.__driver.window_handles)
      self.__click_apply_button()
      try:
        self.__wait_for_new_tab_to_open(starting_tab_count)
        return
      except TimeoutError:
        # Weird bug where occasionally the Linkedin apply button does nothing
        logging.warning("Apply button is dead... skipping...")

  def __wait_for_new_tab_to_open(self, starting_tab_count: int, timeout=10) -> None:
    start_time = time.time()
    while time.time() - start_time < timeout:
      if len(self.__driver.window_handles) > starting_tab_count:
        return
      self.__handle_potential_problems()
      logging.debug("Waiting for new tab to open...")
      time.sleep(0.1)
    raise TimeoutError("Timed out waiting for a new tab to open...")

  def __click_apply_button(self) -> None:
    self.__wait_for_apply_button()
    apply_button = self.__get_apply_button()
    apply_button.click()

  def __get_all_content_div_xpath(self) -> str:
    for i in range(5, 7):
      potential_all_content_div = f"/html/body/div[{i}]"
      potential_header_button_xpath = f"{potential_all_content_div}/header/div/nav"
      try:
        timeout = 1
        start_time = time.time()
        while time.time() - start_time < timeout:
          try:
            some_validation_button = self.__driver.find_element(By.XPATH, potential_header_button_xpath)
            break
          except NoSuchElementException:
            logging.debug("Waiting for some validation button to load...")
            time.sleep(0.1)
        try:
          if some_validation_button:
            return potential_all_content_div
        except UnboundLocalError:
          pass
      except NoSuchElementException:
        pass
    raise RuntimeError("Failed to determine the all content div.")

  def __apply_in_new_tab(self) -> None:
    logging.debug("Applying in new tab...")
    url = self.__driver.current_url
    self.__selenium_helper.open_new_tab()
    self.__driver.get(url)
    self.__click_apply_button()
    self.__linkedin_apply_now_page.apply()

  def __build_new_brief_job_listing(self, job_listing_li: WebElement) -> LinkedinBriefJobListing:
    self.__selenium_helper.scroll_into_view(job_listing_li)
    while True:
      try:
        brief_job_listing = LinkedinBriefJobListing(job_listing_li)
        break
      except NoSuchElementException:
        self.__selenium_helper.scroll_down(self.__get_job_listings_ul())
    return brief_job_listing

  def __build_new_job_listing(self, brief_job_listing: LinkedinBriefJobListing, timeout=3) -> LinkedinJobListing:
    start_time = time.time()
    while time.time() - start_time < timeout:
      try:
        full_job_details_div = self.__get_full_job_details_div()
        assert full_job_details_div
        job_listing = LinkedinJobListing(brief_job_listing, full_job_details_div)
        return job_listing
      except StaleElementReferenceException:
        pass
    raise NoSuchElementException("Failed to find full job details div.")

  def __get_full_job_details_div(self) -> WebElement | None:
    full_job_details_div_selector = ".jobs-details__main-content.jobs-details__main-content--single-pane.full-width"
    main_content_div = self.__get_main_content_div()
    if main_content_div is None:
      return None
    while True:
      try:
        full_job_details_div = main_content_div.find_element(By.CSS_SELECTOR, full_job_details_div_selector)
        break
      except NoSuchElementException:
        self.__handle_potential_problems()
        logging.debug("Waiting for full job details div to load...")
        time.sleep(0.1)
    return full_job_details_div

  def __get_job_listing_li(self, index: int) -> WebElement | None:
    relative_job_listing_li_xpath = f"./li[{index}]"
    job_listings_ul = self.__get_job_listings_ul()
    if job_listings_ul is None:
      return None
    try:
      job_listing_li = job_listings_ul.find_element(By.XPATH, relative_job_listing_li_xpath)
    except NoSuchElementException:
      return None
    return job_listing_li

  def __get_job_listings_ul(self) -> WebElement | None:
    logging.debug("Getting job listings ul...")
    relative_job_listings_ul_xpath = "./div[3]/div[3]/div/div[2]/main/div/div[2]/div[1]/ul"
    main_content_div = self.__get_main_content_div()
    if main_content_div is None:
      return None
    while True:
      try:
        job_listings_ul = main_content_div.find_element(By.XPATH, relative_job_listings_ul_xpath)
        break
      except NoSuchElementException:
        self.__handle_potential_problems()
        logging.debug("Waiting for job listing ul to load...")
        time.sleep(0.1)
    return job_listings_ul

  def __get_main_content_div(self, timeout=10) -> WebElement | None:
    start_time = time.time()
    while time.time() - start_time < timeout:
      for i in range(5, 7):
        potential_main_div_xpath = f"/html/body/div[{i}]"
        potential_job_listings_ul_xpath = f"{potential_main_div_xpath}/div[3]/div[3]/div/div[2]/main/div/div[2]/div[1]/ul"   # pylint: disable=line-too-long
        try:
          self.__driver.find_element(By.XPATH, potential_job_listings_ul_xpath)
          main_content_div = self.__driver.find_element(By.XPATH, potential_main_div_xpath)
          if main_content_div:
            return main_content_div
        except NoSuchElementException:
          self.__handle_potential_problems()
          logging.debug("Waiting for main content div...")
          time.sleep(0.1)

  def __get_next_page_span(self) -> WebElement:
    logging.debug("Getting next page button...")
    main_content_div = self.__get_main_content_div()
    return self.__selenium_helper.get_element_by_aria_label(
      "View next page",
      ElementType.BUTTON,
      base_element=main_content_div
    )

  def __wait_for_apply_button(self) -> None:
    while not self.__is_apply_button():
      self.__handle_potential_problems()
      logging.debug("Waiting for apply button...")
      time.sleep(0.1)

  def __is_apply_button(self) -> bool:
    all_content_div_xpath = self.__get_all_content_div_xpath()
    potential_apply_button_xpaths = [
      f"{all_content_div_xpath}/div[3]/div[3]/div/div[2]/main/div/div[2]/div[2]/div/div[3]/div[1]/div/div[1]/div/div[1]/div/div[6]/div/div/button/span",   # pylint: disable=line-too-long
      f"{all_content_div_xpath}/div[3]/div[3]/div/div[2]/main/div/div[2]/div[2]/div/div[3]/div[1]/div/div[1]/div/div[1]/div/div[6]/div/div/div/button/span"   # pylint: disable=line-too-long
    ]
    for xpath in potential_apply_button_xpaths:
      try:
        self.__driver.find_element(By.XPATH, xpath)
        return True
      except NoSuchElementException:
        pass
    return False

  def __get_apply_button(self) -> WebElement:
    all_content_div_xpath = self.__get_all_content_div_xpath()
    potential_apply_button_xpaths = [
      f"{all_content_div_xpath}/div[3]/div[3]/div/div[2]/main/div/div[2]/div[2]/div/div[3]/div[1]/div/div[1]/div/div[1]/div/div[6]/div/div/button/span",   # pylint: disable=line-too-long
      f"{all_content_div_xpath}/div[3]/div[3]/div/div[2]/main/div/div[2]/div[2]/div/div[3]/div[1]/div/div[1]/div/div[1]/div/div[6]/div/div/div/button/span"   # pylint: disable=line-too-long
    ]
    for xpath in potential_apply_button_xpaths:
      try:
        apply_button = self.__driver.find_element(By.XPATH, xpath)
        return apply_button
      except NoSuchElementException:
        pass
    raise NoSuchElementException("Failed to find apply button.")

  def __is_no_matching_jobs_page(self) -> bool:
    return self.__selenium_helper.exact_text_is_present(
      "No matching jobs found",
      ElementType.H2
    )

  def __handle_potential_problems(self) -> None:
    if self.__is_job_safety_reminder_popup():
      self.__remove_job_search_safety_reminder_popup()
    elif self.__something_went_wrong():
      self.__driver.refresh()
    elif self.__is_rate_limited_page():
      self.__handle_rate_limited_page()

  def __something_went_wrong(self) -> bool:
    return self.__selenium_helper.exact_text_is_present(
      "Something went wrong",
      ElementType.H2
    )

  def __is_job_safety_reminder_popup(self) -> bool:
    return self.__selenium_helper.exact_text_is_present(
      "Job search safety reminder",
      ElementType.H2
    )

  def __remove_job_search_safety_reminder_popup(self) -> None:
    assert self.__is_job_safety_reminder_popup()
    continue_applying_button_id = "jobs-apply-button-id"
    continue_applying_button = self.__driver.find_element(By.ID, continue_applying_button_id)
    continue_applying_button.click()

  def __is_rate_limited_page(self) -> bool:
    error_code_div_class = "error-code"
    try:
      self.__driver.find_element(By.CLASS_NAME, error_code_div_class)   # Confirm we're on HTTP error page
      return True
    except NoSuchElementException:
      return False

  def __handle_rate_limited_page(self) -> None:
    pass # TODO

  def __handle_potential_overload(self) -> None:
    jobs_open = len(self.__driver.window_handles) - 1
    pause_every_x_jobs = self.__quick_settings.bot_behavior.pause_every_x_jobs
    if (
      jobs_open % pause_every_x_jobs == 0
      and jobs_open >= pause_every_x_jobs
    ):
      print("\nPausing to allow user to handle existing tabs before overload.")
      input("\tPress enter to proceed...")
