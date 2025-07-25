import logging
import time
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.common.exceptions import ElementClickInterceptedException, NoSuchElementException
from models.configs.universal_config import UniversalConfig
from models.enums.element_type import ElementType
from services.misc.selenium_helper import SeleniumHelper


class IndeedRelevantExperienceStepper:
  __driver: uc.Chrome
  __selenium_helper: SeleniumHelper
  __universal_config: UniversalConfig

  def __init__(
    self,
    driver: uc.Chrome,
    selenium_helper: SeleniumHelper,
    universal_config: UniversalConfig
  ):
    self.__driver = driver
    self.__selenium_helper = selenium_helper
    self.__universal_config = universal_config

  def is_present(self) -> bool:
    RELEVANT_EXPERIENCE_URL = "smartapply.indeed.com/beta/indeedapply/form/resume-module/relevant-experience"
    return RELEVANT_EXPERIENCE_URL in self.__driver.current_url

  def resolve(self) -> None:
    self.__handle_company_name_input()
    self.__handle_job_title_input()
    while self.is_present():
      # This pages really likes to act up, so self.__click_continue_button() needs to be in this loop sadly
      self.__click_continue_button()
      logging.debug("Waiting for relevant experience page to resolve...")
      time.sleep(5)

  def __handle_company_name_input(self, timeout=1) -> None:
    if len(self.__universal_config.about_me.work_experience) > 0:
      relevant_experience_company = self.__universal_config.about_me.work_experience[0].company
    else:
      relevant_experience_company = "N/A"
    company_name_input_name = "companyName"
    start_time = time.time()
    while time.time() - start_time < timeout:
      try:
        company_input = self.__driver.find_element(By.NAME, company_name_input_name)
        self.__selenium_helper.write_to_input(relevant_experience_company, company_input)
        return
      except NoSuchElementException:
        pass
    raise NoSuchElementException("Failed to find company input.")

  def __handle_job_title_input(self) -> None:
    if len(self.__universal_config.about_me.work_experience) > 0:
      relevant_experience_job_title = self.__universal_config.about_me.work_experience[0].title
    else:
      relevant_experience_job_title = "N/A"
    job_title_input_name = "jobTitle"
    try:
      job_title_input = self.__driver.find_element(By.NAME, job_title_input_name)
      self.__selenium_helper.write_to_input(relevant_experience_job_title, job_title_input)
      return
    except NoSuchElementException:
      pass
    raise NoSuchElementException("Failed to find job title input.")

  def __click_continue_button(self, timeout=10) -> None:
    start_time = time.time()
    # I really don't like using this loop for this but the continue button element is very shoddy
    while time.time() - start_time < timeout:
      try:
        continue_span = self.__selenium_helper.get_element_by_exact_text(
          "Continue",
          ElementType.SPAN
        )
        continue_button = continue_span.find_element(By.XPATH, "..")
        continue_button.click()
        break
      except NoSuchElementException:
        logging.debug("Failed to click continue button. Trying again...")
        time.sleep(0.5)
      except ElementClickInterceptedException:
        logging.debug("Failed to click continue button. Clicking body then trying again...")
        self.__driver.find_element(By.TAG_NAME, "body").click()
        time.sleep(0.5)
