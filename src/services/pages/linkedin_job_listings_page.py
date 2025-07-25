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
  __database_manager: DatabaseManager
  __linkedin_apply_now_page: LinkedinApplyNowPage
  __jobs_applied_to_this_session: List[dict[str, str | float | None]]

  def __init__(
    self,
    driver: uc.Chrome,
    selenium_helper: SeleniumHelper,
    database_manager: DatabaseManager,
    linkedin_config: LinkedinConfig,
    universal_config: UniversalConfig
  ):
    self.__driver = driver
    self.__selenium_helper = selenium_helper
    self.__database_manager = database_manager
    self.__universal_config = universal_config
    self.__linkedin_apply_now_page = LinkedinApplyNowPage(driver, selenium_helper, linkedin_config, universal_config)
    self.__jobs_applied_to_this_session = []

  def apply_to_all_matching_jobs(self) -> None:
    total_jobs_tried = 0
    job_listing_li_index = 0
    while True:
      try:
        total_jobs_tried, job_listing_li_index = self.__handle_incrementors(total_jobs_tried, job_listing_li_index)
      except NoSuchElementException:
        logging.info("\tUnable to find next page button, assuming we've handled all job listings.")
        return
      try:
        self.__handle_page_context(total_jobs_tried)
      except NoSuchElementException:
        logging.info("\tUnable to find next page button, assuming we've handled all job listings.")
        return
      try:
        job_listing_li = self.__get_job_listing_li(job_listing_li_index)
      except NoSuchElementException:
        logging.info("No job listings left -- Finished")
        return
      except TimeoutError as e:
        if not self.__selenium_helper.exact_text_is_present("No matching jobs found", ElementType.H2):
          raise e
        logging.info("No job listings left -- Finished")
        return
      brief_job_listing = self.__build_new_brief_job_listing(job_listing_li, int(total_jobs_tried % 26))
      brief_job_listing.print()
      if brief_job_listing.should_be_ignored(self.__universal_config):
        continue
      if brief_job_listing.to_dict() in self.__jobs_applied_to_this_session:
        logging.debug("Ignoring job listing because: we've already applied this session.\n")
        continue
      previous_job_details_html = self.__get_full_job_details_div().get_attribute("innerHTML")
      assert previous_job_details_html
      self.__click_job_listing_li(job_listing_li)
      self.__wait_for_full_job_details_div_to_change(previous_job_details_html, job_listing_li)
      job_listing = self.__build_new_job_listing(brief_job_listing)
      if job_listing.should_be_ignored(self.__universal_config):
        continue
      starting_tab_count = len(self.__driver.window_handles)
      try:
        self.__apply_to_selected_job()
        self.__database_manager.create_new_job_application_entry(
          self.__universal_config,
          brief_job_listing,
          self.__driver.current_url,
          "Linkedin"
        )
        self.__driver.switch_to.window(self.__driver.window_handles[0])
        self.__jobs_applied_to_this_session.append(brief_job_listing.to_dict())
      except RuntimeError:
        logging.warning("Assuming this job posting has no apply button, continuing...")
        if len(self.__driver.window_handles) > starting_tab_count:
          self.__driver.close()
          self.__driver.switch_to.window(self.__driver.window_handles[0])
          continue
      if (
        len(self.__jobs_applied_to_this_session) % self.__universal_config.bot_behavior.pause_every_x_jobs == 0
        and len(self.__jobs_applied_to_this_session) >= self.__universal_config.bot_behavior.pause_every_x_jobs
      ):
        print("\nPausing to allow user to handle existing tabs before overload.")
        input("\tPress enter to proceed...")

  def __click_job_listing_li(self, job_listing_li: WebElement) -> None:
    while True:
      try:
        job_listing_li.click()
        break
      except ElementClickInterceptedException:
        logging.debug("Click intercepted... Attempting to resolve...")
        if self.__job_search_safety_reminder_popup_is_present():
          self.__remove_job_search_safety_reminder_popup()
        time.sleep(0.1)

  def __handle_incrementors(self, total_jobs_tried: int, job_listing_li_index: int) -> Tuple[int, int]:
    total_jobs_tried += 1
    if total_jobs_tried >= 4:
      self.__scroll_jobs_ul()
    job_listing_li_index = total_jobs_tried % 26
    if job_listing_li_index == 0:
      total_jobs_tried += 1
      job_listing_li_index = 1
    return (total_jobs_tried, job_listing_li_index)

  def __wait_for_full_job_details_div_to_change(
    self,
    previous_job_details_html: str,
    job_listing_li: WebElement,
    timeout=60
  ) -> None:
    start_time = time.time()
    while time.time() - start_time < timeout:
      try:
        if self.__get_full_job_details_div().get_attribute("innerHTML") != previous_job_details_html:
          return
        logging.debug("Waiting for full job listing to load...")
        time.sleep(0.5)
      except TimeoutError:
        self.__scroll_jobs_ul()
        self.__click_job_listing_li(job_listing_li)
      except NoSuchElementException:
        if self.__selenium_helper.exact_text_is_present(
          "Something went wrong",
          ElementType.H2
        ):
          self.__driver.refresh()
    raise TimeoutError("Timed out waiting for full job listing to load.")

  def __handle_page_context(self, total_jobs_tried: int) -> None:
    if total_jobs_tried > 26 and total_jobs_tried % 26 == 1:
      logging.debug("Going to page %s...", math.ceil(total_jobs_tried / 26))
      next_page_span = self.__get_next_page_span()
      while True:
        try:
          next_page_span.click()
          return
        except ElementNotInteractableException:
          logging.debug("Failed to click next page span... Scrolling down and trying again...")
          self.__scroll_jobs_ul()
          time.sleep(0.1)

  def __apply_to_selected_job(self) -> None:
    logging.debug("Applying to job...")
    apply_button = self.__get_apply_button()
    apply_button_text = apply_button.text
    assert apply_button_text
    apply_button_text = apply_button_text.strip()
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
      logging.debug("Waiting for new tab to open...")
      if self.__job_search_safety_reminder_popup_is_present():
        self.__remove_job_search_safety_reminder_popup()
      time.sleep(0.1)
    raise TimeoutError("Timed out waiting for a new tab to open...")

  def __click_apply_button(self, timeout=10) -> None:
    start_time = time.time()
    while time.time() - start_time < timeout:
      try:
        apply_button = self.__get_apply_button()
        apply_button.click()
        return
      except StaleElementReferenceException:
        logging.debug("Stale element reference while trying to click apply. Trying again...")
        time.sleep(0.5)

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
    raise RuntimeError("Failed to determine the all content div xpath.")

  def __is_job_load_error(self) -> bool:
    return self.__selenium_helper.exact_text_is_present("Something went wrong", ElementType.H2)

  def __handle_job_load_error(self) -> None:
    assert self.__selenium_helper.exact_text_is_present("Something went wrong", ElementType.H2)
    refresh_page_span = self.__selenium_helper.get_element_by_exact_text("Refresh page", ElementType.SPAN)
    refresh_page_button = refresh_page_span.find_element(By.XPATH, "..")
    refresh_page_button.click()

  def __apply_in_new_tab(self) -> None:
    logging.debug("Applying in new tab...")
    url = self.__driver.current_url
    self.__driver.switch_to.new_window('tab')
    self.__driver.get(url)
    try:
      apply_button = self.__get_apply_button()
    except ValueError:
      logging.warning('No apply button found, assuming "No longer accepting applications", skipping...')
      return
    apply_button.click()
    self.__linkedin_apply_now_page.apply()

  def __scroll_jobs_ul(self, pixels=50) -> None:
    logging.debug("Scrolling jobs url...")
    job_listing_ul = self.__get_job_listing_ul()
    self.__driver.execute_script(f"arguments[0].scrollTop = arguments[0].scrollTop + {pixels};", job_listing_ul)

  def __build_new_brief_job_listing(self, job_listing_li: WebElement, debug: int) -> LinkedinBriefJobListing:
    while True:
      try:
        print(f"DEBUG: {debug}, if 1, should have gone to next page")
        brief_job_listing = LinkedinBriefJobListing(job_listing_li)
        break
      except NoSuchElementException:
        self.__scroll_jobs_ul()
    return brief_job_listing

  def __build_new_job_listing(self, brief_job_listing: LinkedinBriefJobListing, timeout=3) -> LinkedinJobListing:
    start_time = time.time()
    while time.time() - start_time < timeout:
      try:
        full_job_details_div = self.__get_full_job_details_div()
        job_listing = LinkedinJobListing(brief_job_listing, full_job_details_div)
        return job_listing
      except StaleElementReferenceException:
        pass
    raise NoSuchElementException("Failed to find full job details div.")

  def __get_full_job_details_div(self) -> WebElement:
    full_job_details_div_selector = ".jobs-details__main-content.jobs-details__main-content--single-pane.full-width"
    main_content_div = self.__get_main_content_div()
    while True:
      try:
        full_job_details_div = main_content_div.find_element(By.CSS_SELECTOR, full_job_details_div_selector)
        break
      except NoSuchElementException:
        logging.debug("Waiting for full job details div to load...")
        if self.__is_job_load_error():
          self.__handle_job_load_error()
        time.sleep(0.1)
    return full_job_details_div

  def __get_job_listing_li(self, index: int) -> WebElement:
    relative_job_listing_li_xpath = f"./li[{index}]"
    job_listing_ul = self.__get_job_listing_ul()
    job_listing_li = job_listing_ul.find_element(By.XPATH, relative_job_listing_li_xpath)
    return job_listing_li

  def __get_job_listing_ul(self) -> WebElement:
    logging.debug("Getting job listings ul xpath...")
    relative_job_listing_ul_xpath = "./div[3]/div[3]/div/div[2]/main/div/div[2]/div[1]/ul"
    main_content_div = self.__get_main_content_div()
    while True:
      try:
        job_listing_ul = main_content_div.find_element(By.XPATH, relative_job_listing_ul_xpath)
        break
      except NoSuchElementException:
        logging.debug("Waiting for job listing ul to load...")
        time.sleep(0.1)
    return job_listing_ul

  def __get_main_content_div(self, timeout=10) -> WebElement:
    self.__wait_for_main_content_div(timeout)
    for i in range(5, 7):
      potential_main_div_xpath = f"/html/body/div[{i}]"
      potential_job_listing_ul_xpath = f"{potential_main_div_xpath}/div[3]/div[3]/div/div[2]/main/div/div[2]/div[1]/ul"   # pylint: disable=line-too-long
      try:
        self.__driver.find_element(By.XPATH, potential_job_listing_ul_xpath)
        main_content_div = self.__driver.find_element(By.XPATH, potential_main_div_xpath)
      except NoSuchElementException:
        continue
      assert main_content_div
      return main_content_div
    raise NoSuchElementException("Failed to find main content div.")

  def __wait_for_main_content_div(self, timeout=10) -> None:
    start_time = time.time()
    while time.time() - start_time < timeout:
      for i in range(5, 7):
        potential_main_div_xpath = f"/html/body/div[{i}]"
        potential_job_listing_ul_xpath = f"{potential_main_div_xpath}/div[3]/div[3]/div/div[2]/main/div/div[2]/div[1]/ul"   # pylint: disable=line-too-long
        try:
          self.__driver.find_element(By.XPATH, potential_job_listing_ul_xpath)
          main_content_div = self.__driver.find_element(By.XPATH, potential_main_div_xpath)
          if main_content_div:
            return
        except NoSuchElementException:
          pass
    if self.__on_http_error_page():
      self.__driver.refresh()
      self.__driver.find_element(By.XPATH, potential_job_listing_ul_xpath)
      main_content_div = self.__driver.find_element(By.XPATH, potential_main_div_xpath)
      if main_content_div:
        return
    raise NoSuchElementException("Failed to find main content div.")

  def __on_http_error_page(self) -> bool:
    error_code_div_class = "error-code"
    try:
      self.__driver.find_element(By.CLASS_NAME, error_code_div_class)   # Confirm we're on HTTP error page
      return True
    except NoSuchElementException:
      return False

  def __handle_http_error_page(self) -> None:
    self.__driver.refresh()
    # time.sleep(5)   # TODO: We need a proper wait condition here

  def __get_next_page_span(self) -> WebElement:
    logging.debug("Getting next page button...")
    main_content_div = self.__get_main_content_div()
    return self.__selenium_helper.get_element_by_aria_label(
      "View next page",
      ElementType.BUTTON,
      base_element=main_content_div
    )

  def __get_apply_button(self, timeout=1) -> WebElement:
    all_content_div_xpath = self.__get_all_content_div_xpath()
    potential_apply_button_xpaths = [
      f"{all_content_div_xpath}/div[3]/div[3]/div/div[2]/main/div/div[2]/div[2]/div/div[3]/div[1]/div/div[1]/div/div[1]/div/div[6]/div/div/button/span",   # pylint: disable=line-too-long
      f"{all_content_div_xpath}/div[3]/div[3]/div/div[2]/main/div/div[2]/div[2]/div/div[3]/div[1]/div/div[1]/div/div[1]/div/div[6]/div/div/div/button/span"   # pylint: disable=line-too-long
    ]
    start_time = time.time()
    while time.time() - start_time < timeout:
      for xpath in potential_apply_button_xpaths:
        try:
          apply_button = self.__driver.find_element(By.XPATH, xpath)
          return apply_button
        except NoSuchElementException:
          pass
      if self.__is_job_load_error():
        self.__handle_job_load_error()
    raise RuntimeError("Failed to find apply button xpath.")


  def __job_search_safety_reminder_popup_is_present(self) -> bool:
    return self.__selenium_helper.exact_text_is_present("Job search safety reminder", ElementType.H2)

  def __remove_job_search_safety_reminder_popup(self) -> None:
    if self.__selenium_helper.exact_text_is_present("Job search safety reminder", ElementType.H2):
      continue_applying_button_id = "jobs-apply-button-id"
      continue_applying_button = self.__driver.find_element(By.ID, continue_applying_button_id)
      continue_applying_button.click()
