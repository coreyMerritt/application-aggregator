import logging
import os
import time
from typing import Tuple
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement
from selenium.common.exceptions import ElementNotInteractableException, NoSuchElementException, TimeoutException
from services.misc.selenium_helper import SeleniumHelper


# This is not -- and will not -- be officially supported. However, its convenient for now
class MailDotComOrchestrationEngine:
  __driver: uc.Chrome
  __selenium_helper: SeleniumHelper

  def __init__(self, driver: uc.Chrome, selenium_helper: SeleniumHelper):
    self.__driver = driver
    self.__selenium_helper = selenium_helper

  def get_indeed_one_time_code(self) -> str:
    mail_dot_com_url = "https://mail.com"
    logging.debug("Handling %s...", mail_dot_com_url)
    self.__driver.switch_to.new_window('tab')
    self.__driver.set_page_load_timeout(3)
    try:
      self.__driver.get(mail_dot_com_url)
    except TimeoutException:
      pass
    self.__selenium_helper.set_driver_timeout_to_default()
    self.__login()
    self.__select_top_email()
    one_time_code = self.__get_indeed_one_time_code_from_email()
    self.__driver.switch_to.default_content()
    self.__delete_indeed_one_time_code_email()
    return one_time_code

  def __login(self) -> None:
    email_page_url = "navigator-lxa.mail.com"
    start_login_button_id = "login-button"
    email_textbox_id = "login-email"
    password_textbox_id = "login-password"
    login_button_xpath = "/html/body/div[1]/div/div[1]/div/div/div/div[2]/form/button"
    email, password = self.__get_auth_data()
    self.__driver.set_page_load_timeout(10)
    while email_page_url not in self.__driver.current_url:
      timeout = 10
      start_time = time.time()
      while True:
        try:
          if time.time() - start_time > timeout:
            raise TimeoutException("Timed out waiting for login button to load.")
          start_login_button = self.__driver.find_element(By.ID, start_login_button_id)
          break
        except NoSuchElementException:
          logging.debug("Waiting for start login button to load...")
          time.sleep(0.1)
      start_login_button.click()
      email_input = self.__driver.find_element(By.ID, email_textbox_id)
      while True:
        try:
          self.__selenium_helper.write_to_input(email, email_input)
          break
        except ElementNotInteractableException:
          logging.debug("Waiting for email input to load...")
          time.sleep(0.1)
      password_input = self.__driver.find_element(By.ID, password_textbox_id)
      self.__selenium_helper.write_to_input(password, password_input)
      try:
        login_button = self.__driver.find_element(By.XPATH, login_button_xpath)
        login_button.click()
      except TimeoutError:
        input("Why did this happen?")
      # TODO: Do we need this sleep? If so this can't be the right way to handle this...
      time.sleep(1)
    self.__selenium_helper.set_driver_timeout_to_default()

  def __get_auth_data(self) -> Tuple[str, str]:
    # Using env vars for personal use because this isn't officially supported
    email = os.getenv("MAIL_DOT_COM_EMAIL")
    password = os.getenv("MAIL_DOT_COM_PASS")
    if email is None:
      raise RuntimeError("MAIL_DOT_COM_EMAIL is not defined.")
    if password is None:
      raise RuntimeError("MAIL_DOT_COM_PASS is not defined.")
    return (email, password)

  def __select_top_email(self) -> None:
    self.__switch_to_main_content_iframe()
    top_email_tr = self.__get_top_indeed_one_time_email_tr()
    top_email_tr.click()

  def __get_indeed_one_time_code_from_email(self) -> str:
    one_time_code_strong_xpath = "/html/body/table[2]/tbody/tr/td/table/tbody/tr/td/table/tbody/tr/td/table/tbody/tr[3]/td/table/tbody/tr/td/p/strong"    # pylint: disable=line-too-long
    self.__switch_to_email_info_iframe()
    one_time_code_strong = self.__driver.find_element(By.XPATH, one_time_code_strong_xpath)
    one_time_code_text = one_time_code_strong.text
    assert one_time_code_text
    return one_time_code_text

  def __delete_indeed_one_time_code_email(self) -> None:
    delete_email_button_xpath = "/html/body/div[3]/div[3]/div[3]/div[1]/div[1]/div/form/div[1]/div[1]/ul[2]/li[1]/button"   # pylint: disable=line-too-long
    self.__switch_to_main_content_iframe()
    top_email_description_text = self.__get_top_email_description_text()
    assert top_email_description_text == "Indeed one-time passcode"
    delete_email_button = self.__driver.find_element(By.XPATH, delete_email_button_xpath)
    delete_email_button.click()

  def __get_top_email_description_text(self) -> str:
    self.__switch_to_main_content_iframe()
    relative_top_email_description_span_xpath = "./td[2]/div[2]/span"
    top_email_tr = self.__get_top_indeed_one_time_email_tr()
    email_description_span = top_email_tr.find_element(By.XPATH, relative_top_email_description_span_xpath)
    description = email_description_span.text
    assert description
    assert description == "Indeed one-time passcode"
    return description

  def __get_top_indeed_one_time_email_tr(self, timeout=10) -> WebElement:
    start_time = time.time()
    while time.time() - start_time < timeout:
      try:
        top_email_tr_xpath = "/html/body/div[3]/div[3]/div[3]/div[1]/div[1]/div/form/div[2]/div/div/table/tbody/tr[1]"
        top_email_tr = self.__driver.find_element(By.XPATH, top_email_tr_xpath)
        top_email_tr_class = top_email_tr.get_attribute("class")
        assert top_email_tr_class
        if top_email_tr_class != "js-component":
          return top_email_tr
        top_email_tr_xpath = "/html/body/div[3]/div[3]/div[3]/div[1]/div[1]/div/form/div[2]/div/div/table/tbody/tr[2]"
        top_email_tr = self.__driver.find_element(By.XPATH, top_email_tr_xpath)
        top_email_tr_class = top_email_tr.get_attribute("class")
        assert top_email_tr_class
        assert top_email_tr_class != "js-component"
        return top_email_tr
      except AssertionError:
        logging.debug("Waiting for top email tr to load...")
        time.sleep(0.1)
      except NoSuchElementException:
        logging.debug("Waiting for top email tr to load...")
        time.sleep(0.1)
    raise TimeoutError("Timed out waiting for email tr to load.")

  def __switch_to_main_content_iframe(self) -> None:
    main_iframe_xpath = "/html/body/main/nav-app-stack/iframe[3]"
    self.__driver.switch_to.default_content()
    while True:
      try:
        main_iframe = self.__driver.find_element(By.XPATH, main_iframe_xpath)
        break
      except NoSuchElementException:
        logging.debug("Waiting for main iframe to load...")
        time.sleep(0.5)
    self.__driver.switch_to.frame(main_iframe)

  def __switch_to_email_info_iframe(self) -> None:
    email_info_iframe_xpath = "/html/body/div[3]/div[3]/div[3]/div[1]/div[1]/div/div[1]/div[1]/div[2]/iframe"
    self.__switch_to_main_content_iframe()
    while True:
      try:
        email_info_iframe = self.__driver.find_element(By.XPATH, email_info_iframe_xpath)
        break
      except NoSuchElementException:
        logging.debug("Waiting for email info iframe to load...")
        time.sleep(0.5)
    self.__driver.switch_to.frame(email_info_iframe)
