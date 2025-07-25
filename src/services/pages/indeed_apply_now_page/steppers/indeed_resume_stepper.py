import logging
import time
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.common.exceptions import ElementClickInterceptedException, NoSuchElementException
from models.configs.universal_config import UniversalConfig
from models.enums.element_type import ElementType
from services.misc.selenium_helper import SeleniumHelper


class IndeedResumeStepper:
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

  def resolve(self, resume_url: str) -> None:
    if not self.__resume_preview_is_visible():
      self.__select_first_resume()
    self.__click_continue_button()
    while resume_url in self.__driver.current_url and "relevant-experience" not in self.__driver.current_url:
      logging.debug("Waiting for resume page to resolve...")
      time.sleep(0.5)

  def __resume_preview_is_visible(self) -> bool:
    return self.__selenium_helper.exact_text_is_present("Resume options", ElementType.SPAN)

  def __select_first_resume(self, timeout=5) -> None:
    start_time = time.time()
    while time.time() - start_time < timeout:
      try:
        first = self.__universal_config.about_me.name.first
        last = self.__universal_config.about_me.name.last
        expected_resume_name = f"{first}-{last}.pdf"
        resume_span = self.__selenium_helper.get_element_by_exact_text(
          expected_resume_name,
          ElementType.SPAN
        )
        resume_span.click()
        return
      except NoSuchElementException:
        logging.debug("Failed to click resume span. Trying again...")
        time.sleep(0.5)
    raise NoSuchElementException("Failed to click resume span.")

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
