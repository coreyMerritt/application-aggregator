import logging
import os
import time
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from models.enums.element_type import ElementType
from services.orchestration.mail_dot_com_orchestration_engine import MailDotComOrchestrationEngine
from services.misc.selenium_helper import SeleniumHelper


class IndeedOneTimeCodePage:
  __driver: uc.Chrome
  __selenium_helper: SeleniumHelper
  __mail_dot_com_orchestration_engine: MailDotComOrchestrationEngine

  def __init__(self, driver: uc.Chrome, selenium_helper: SeleniumHelper):
    self.__driver = driver
    self.__selenium_helper = selenium_helper
    self.__mail_dot_com_orchestration_engine = MailDotComOrchestrationEngine(driver, selenium_helper)

  def is_present(self) -> bool:
    return self.__selenium_helper.exact_text_is_present("Sign in with a code", ElementType.H1)

  def can_resolve_with_mail_dot_com(self) -> bool:
    email = os.getenv("MAIL_DOT_COM_EMAIL")
    password = os.getenv("MAIL_DOT_COM_PASS")
    if email and password:
      return True
    return False

  def resolve_with_mail_dot_com(self) -> None:
    assert self.can_resolve_with_mail_dot_com()
    email = os.getenv("MAIL_DOT_COM_EMAIL")
    password = os.getenv("MAIL_DOT_COM_PASS")
    if email and password:
      code = self.__mail_dot_com_orchestration_engine.get_indeed_one_time_code()
      self.__driver.switch_to.window(self.__driver.window_handles[0])
      self.__enter_one_time_code(code)
      self.__driver.switch_to.window(self.__driver.window_handles[-1])
      self.__driver.close()
      self.__driver.switch_to.window(self.__driver.window_handles[0])

  def wait_for_captcha_resolution(self) -> None:
    captcha_url = "secure.indeed.com"
    while captcha_url in self.__driver.current_url:
      logging.debug("Waiting for captcha resolution...")
      time.sleep(0.5)

  def __enter_one_time_code(self, code: str) -> None:
    logging.debug('Waiting for one-time code resolution...')
    one_time_code_input_id = "passcode-input"
    one_time_code_input = self.__driver.find_element(By.ID, one_time_code_input_id)
    self.__selenium_helper.write_to_input(code, one_time_code_input)
