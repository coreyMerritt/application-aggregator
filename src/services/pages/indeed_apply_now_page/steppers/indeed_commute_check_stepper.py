import logging
import time
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from models.enums.element_type import ElementType
from services.misc.selenium_helper import SeleniumHelper


class IndeedCommuteCheckStepper:
  __driver: uc.Chrome
  __selenium_helper: SeleniumHelper

  def __init__(
    self,
    driver: uc.Chrome,
    selenium_helper: SeleniumHelper
  ):
    self.__driver = driver
    self.__selenium_helper = selenium_helper

  def is_present(self) -> bool:
    COMMUTE_CHECK_URL = "smartapply.indeed.com/beta/indeedapply/form/commute-check"
    return COMMUTE_CHECK_URL in self.__driver.current_url

  def resolve(self) -> None:
    self.__wait_for_continue_appying_span()
    continue_applying_span = self.__selenium_helper.get_element_by_exact_text(
      "Continue applying",
      ElementType.SPAN
    )
    continue_applying_button = continue_applying_span.find_element(By.XPATH, "..")
    continue_applying_button.click()
    while self.is_present():
      logging.debug("Waiting for contact info page to resolve...")
      time.sleep(0.5)

  def __wait_for_continue_appying_span(self, timeout=10) -> None:
    start_time = time.time()
    while time.time() - start_time < timeout:
      if self.__selenium_helper.exact_text_is_present(
        "Continue applying",
        ElementType.SPAN
      ):
        return
      logging.debug("Waiting for continue applying span...")
      time.sleep(0.5)
