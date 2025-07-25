import logging
import time
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement
from selenium.common.exceptions import NoSuchElementException
from models.configs.indeed_config import IndeedConfig
from models.enums.element_type import ElementType
from services.misc.selenium_helper import SeleniumHelper


class IndeedLoginPage:
  __driver: uc.Chrome
  __selenium_helper: SeleniumHelper
  __indeed_config: IndeedConfig

  def __init__(self, driver: uc.Chrome, selenium_helper: SeleniumHelper, indeed_config: IndeedConfig):
    self.__driver = driver
    self.__selenium_helper = selenium_helper
    self.__indeed_config = indeed_config

  def login(self) -> None:
    base_url = "https://www.indeed.com"
    logging.debug("Logging into %s...", base_url)
    self.__driver.get(base_url)
    sign_in_anchor = self.__get_sign_in_anchor()
    sign_in_anchor.click()
    self.__wait_for_login_page_url()
    email_textbox_name = "__email"
    email_address = self.__indeed_config.email
    while True:
      try:
        email_textbox = self.__driver.find_element(By.NAME, email_textbox_name)
        break
      except NoSuchElementException:
        logging.debug("Failed to find email textbox, trying again...")
        time.sleep(0.5)
    self.__selenium_helper.write_to_input(email_address, email_textbox)
    continue_button_xpath = "/html/body/div/div[2]/main/div/div/div[2]/div/form/button"
    continue_button = self.__driver.find_element(By.XPATH, continue_button_xpath)
    continue_button.click()

  def __get_sign_in_anchor(self) -> WebElement:
    sign_in_anchor = self.__selenium_helper.get_element_by_exact_text("Sign in", ElementType.ANCHOR)
    return sign_in_anchor

  def __wait_for_login_page_url(self, timeout=10) -> None:
    login_page_url = "onboarding.indeed.com"
    start_time = time.time()
    while time.time() - start_time < timeout:
      if login_page_url in self.__driver.current_url:
        return
      logging.debug("Waiting for login page url to appear...")
      time.sleep(0.5)
