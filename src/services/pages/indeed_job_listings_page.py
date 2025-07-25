import logging
import time
from typing import List
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement
from selenium.common.exceptions import (
  ElementClickInterceptedException,
  NoSuchElementException,
  StaleElementReferenceException
)
from entities.indeed_brief_job_listing import IndeedBriefJobListing
from entities.indeed_job_listing import IndeedJobListing
from models.configs.indeed_config import IndeedConfig
from models.configs.universal_config import UniversalConfig
from services.misc.selenium_helper import SeleniumHelper
from services.pages.indeed_apply_now_page import IndeedApplyNowPage


class IndeedJobListingsPage:
  __driver: uc.Chrome
  __universal_config: UniversalConfig
  __apply_now_page: IndeedApplyNowPage
  __jobs_applied_to_this_session: List[dict[str, str | None]]
  __current_page_number: int

  def __init__(
    self,
    driver: uc.Chrome,
    selenium_helper: SeleniumHelper,
    indeed_config: IndeedConfig,
    universal_config: UniversalConfig
  ):
    self.__driver = driver
    self.__universal_config = universal_config
    self.__apply_now_page = IndeedApplyNowPage(driver, selenium_helper, indeed_config, universal_config)
    self.__jobs_applied_to_this_session = []
    self.__current_page_number = 1

  def is_present(self) -> bool:
    try:
      self.__get_job_listings_ul()
      return True
    except NoSuchElementException:
      return False

  def apply_to_all_matching_jobs(self) -> None:
    jobs_attempted = -1
    while True:
      jobs_attempted += 1
      job_listing_li_number = (jobs_attempted % 18) + 2
      job_listing_is_on_next_page = jobs_attempted > 2 and job_listing_li_number == 2
      if job_listing_is_on_next_page:
        if self.__is_a_next_page():
          self.__go_to_next_page()
        else:
          logging.info("End of job listings.")
          return
      try:
        job_listing_li = self.__get_job_listing_li(job_listing_li_number)
      except NoSuchElementException:
        # if not "some_url" in current_url:   # TODO: Figure out what this "job view" url is about -- do driver.back()
        logging.info("End of job listings.")
        return
      try:
        brief_job_listing = IndeedBriefJobListing(job_listing_li)
      except NoSuchElementException:
        logging.debug("Skipping a fake job listing / advertisement...")
        continue
      brief_job_listing.print()
      if brief_job_listing.should_be_ignored(self.__universal_config):
        continue
      if brief_job_listing.to_dict() in self.__jobs_applied_to_this_session:
        logging.info("Ignoring job listing because: we've already applied this session.\n")
        continue
      job_listing_anchor = self.__get_job_listing_anchor(job_listing_li)
      while True:
        try:
          job_listing_anchor.click()
          break
        except ElementClickInterceptedException:
          logging.debug("Failed to click job anchor. Trying again...")
          self.__remove_did_you_apply_popup()
          time.sleep(0.1)
      job_description_html = self.__get_job_description_html()
      job_listing = IndeedJobListing(brief_job_listing, job_description_html)
      if job_listing.should_be_ignored(self.__universal_config):
        continue
      while (
        not self.__is_easy_apply_button()
        and not self.__is_apply_on_company_site_button()
        and not self.__is_apply_now_button()
      ):
        logging.debug("Waiting for apply button...")
        time.sleep(0.5)
      assert not (self.__is_easy_apply_button() and self.__is_apply_on_company_site_button())
      self.__apply_to_visible_job()
      self.__jobs_applied_to_this_session.append(brief_job_listing.to_dict())
      if len(self.__jobs_applied_to_this_session) % self.__universal_config.bot_behavior.pause_every_x_jobs == 0:
        print("\nPausing to allow user to handle existing tabs before overload.")
        input("\tPress enter to proceed...")

  def __apply_to_visible_job(self) -> None:
    if self.__is_apply_now_button():
      starting_tab_count = len(self.__driver.window_handles)
      while len(self.__driver.window_handles) == starting_tab_count:
        logging.debug("Attempting to click the apply now button...")
        while True:
          try:
            apply_now_button = self.__get_apply_now_button()
            apply_now_button.click()
            break
          except StaleElementReferenceException:
            logging.debug("Apply button reference is stale. Trying again...")
            time.sleep(0.5)
        time.sleep(0.5)
      self.__driver.switch_to.window(self.__driver.window_handles[-1])
      self.__apply_now_page.apply()
      self.__driver.switch_to.window(self.__driver.window_handles[0])
    elif self.__is_apply_on_company_site_button():
      apply_on_company_site_button = self.__get_apply_on_company_site_button()
      while True:
        try:
          apply_on_company_site_button.click()
          break
        except ElementClickInterceptedException:
          logging.debug("Failed to click apply on company site button. Trying again...")
          self.__remove_did_you_apply_popup()
          time.sleep(0.1)
      # Ignore page and allow user to come back later
      self.__driver.switch_to.window(self.__driver.window_handles[0])

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

  def __get_job_listing_li(self, index: int) -> WebElement:
    job_listings_ul = self.__get_job_listings_ul()
    job_listing_li = job_listings_ul.find_element(By.XPATH, f"./li[{index}]")
    return job_listing_li

  def __get_job_listings_ul(self) -> WebElement:
    job_listings_ul_xpath = "/html/body/main/div/div[2]/div/div[5]/div/div[1]/div[4]/div/ul"
    job_listings_ul = self.__driver.find_element(By.XPATH, job_listings_ul_xpath)
    return job_listings_ul

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

  def __get_page_buttons_ul(self) -> WebElement:
    page_buttons_ul_xpath = "/html/body/main/div/div[2]/div/div[5]/div/div[1]/nav/ul"
    page_buttons_ul = self.__driver.find_element(By.XPATH, page_buttons_ul_xpath)
    return page_buttons_ul

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
        logging.debug("Failed to get job description div... Trying again...")
        time.sleep(0.5)
    job_description_html = job_description_div.get_attribute("innerHTML")
    if job_description_html:
      return job_description_html
    raise AttributeError("Job description div has no innerHTML attribute.")

  def __is_easy_apply_button(self) -> bool:
    easy_apply_button_id = "indeedApplyButton"
    try:
      self.__driver.find_element(By.ID, easy_apply_button_id)
      return True
    except NoSuchElementException:
      return False

  def __is_apply_now_button(self) -> bool:
    apply_now_button_selector = '[aria-label="Apply now opens in a new tab"]'
    try:
      self.__driver.find_element(By.CSS_SELECTOR, apply_now_button_selector)
      return True
    except NoSuchElementException:
      return False

  def __is_apply_on_company_site_button(self) -> bool:
    apply_on_company_site_button_selector = '[aria-label="Apply on company site (opens in a new tab)"]'
    try:
      self.__driver.find_element(By.CSS_SELECTOR, apply_on_company_site_button_selector)
      return True
    except NoSuchElementException:
      return False

  def __get_apply_now_button(self) -> WebElement:
    apply_now_button_selector = '[aria-label="Apply now opens in a new tab"]'
    apply_now_button = self.__driver.find_element(By.CSS_SELECTOR, apply_now_button_selector)
    return apply_now_button

  def __get_apply_on_company_site_button(self) -> WebElement:
    apply_on_company_site_button_selector = '[aria-label="Apply on company site (opens in a new tab)"]'
    apply_on_company_site_button = self.__driver.find_element(By.CSS_SELECTOR, apply_on_company_site_button_selector)
    return apply_on_company_site_button

  def __remove_did_you_apply_popup(self, timeout=3) -> None:
    potential_exit_button_xpaths = [
      "/html/body/main/div/div[2]/div/div[5]/div/div[2]/div/div/div[2]/div[2]/div[1]/div/div[3]/div/div[3]/div/div[2]/div/div[1]/div[2]/button",   # pylint: disable=line-too-long
      "/html/body/main/div/div[2]/div/div[5]/div/div[2]/div/div/div[2]/div[2]/div[1]/div/div[4]/div/div[3]/div/div[2]/div/div[1]/div[2]/button"   # pylint: disable=line-too-long
    ]
    start_time = time.time()
    while time.time() - start_time < timeout:
      for xpath in potential_exit_button_xpaths:
        try:
          exit_button = self.__driver.find_element(By.XPATH, xpath)
          exit_button.click()
          return
        except NoSuchElementException:
          pass
