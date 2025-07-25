import logging
import time
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException
from models.enums.element_type import ElementType
from models.configs.indeed_config import IndeedConfig
from models.configs.universal_config import UniversalConfig
from services.misc.selenium_helper import SeleniumHelper


class IndeedApplyNowPage:
  __driver: uc.Chrome
  __selenium_helper: SeleniumHelper
  __indeed_config: IndeedConfig
  __universal_config: UniversalConfig

  def __init__(
    self,
    driver: uc.Chrome,
    selenium_helper: SeleniumHelper,
    indeed_config: IndeedConfig,
    universal_config: UniversalConfig
  ):
    self.__driver = driver
    self.__selenium_helper = selenium_helper
    self.__indeed_config = indeed_config
    self.__universal_config = universal_config

  def is_present(self) -> bool:
    return "smartapply.indeed.com" in self.__driver.current_url

  def apply(self) -> None:
    while self.is_present():
      # Relevant Experience Page
      if "smartapply.indeed.com/beta/indeedapply/form/resume-module/relevant-experience" in self.__driver.current_url:
        self.__handle_company_name_input()
        self.__handle_job_title_input()
        self.__click_continue_button()
        while "smartapply.indeed.com/beta/indeedapply/form/resume-module/relevant-experience" in self.__driver.current_url:   # pylint: disable=line-too-long
          logging.debug("Waiting for relevant experience page to resolve...")
          time.sleep(0.5)
      # Resume Page
      elif "smartapply.indeed.com/beta/indeedapply/form/resume" in self.__driver.current_url:
        if not self.__resume_preview_is_visible():
          self.__select_first_resume()
        self.__click_continue_button()
        while "smartapply.indeed.com/beta/indeedapply/form/resume" in self.__driver.current_url:
          if "relevant-experience" in self.__driver.current_url:
            break
          logging.debug("Waiting for resume page to resolve...")
          time.sleep(0.5)
      # Location Details Page
      elif "smartapply.indeed.com/beta/indeedapply/form/profile-location" in self.__driver.current_url:
        self.__handle_street_address_input()
        self.__handle_city_state_input()
        self.__handle_postal_code_input()
        self.__click_continue_button()
        while "smartapply.indeed.com/beta/indeedapply/form/profile-location" in self.__driver.current_url:
          logging.debug("Waiting for profile location page to resolve...")
          time.sleep(0.5)
      # Contact Information Page
      elif "smartapply.indeed.com/beta/indeedapply/form/contact-info" in self.__driver.current_url:
        self.__handle_phone_number_input()
        try:    # Sometimes this input isnt in the form -- seemingly when accessed from glassdoor specifically
          self.__handle_city_state_input()
        except NoSuchElementException:
          pass
        self.__handle_last_name_input()
        self.__handle_first_name_input()
        self.__click_continue_button()
        while "smartapply.indeed.com/beta/indeedapply/form/contact-info" in self.__driver.current_url:
          logging.debug("Waiting for contact info page to resolve...")
          time.sleep(0.5)
      # Finished with "apply now"
      elif (
        "smartapply.indeed.com/beta/indeedapply/form/questions-module/questions/1" in self.__driver.current_url
        or "smartapply.indeed.com/beta/indeedapply/form/review" in self.__driver.current_url
        or "smartapply.indeed.com/beta/indeedapply/form/demographic-questions/1" in self.__driver.current_url
      ):
        self.__driver.switch_to.window(self.__driver.window_handles[0])
        return
      elif "smartapply.indeed.com/beta/indeedapply/postresumeapply" in self.__driver.current_url:
        confirm_time = 7
        start_time = time.time()
        is_genuine_already_applied_page = True
        while time.time() - start_time < confirm_time:
          if not "smartapply.indeed.com/beta/indeedapply/postresumeapply" in self.__driver.current_url:
            is_genuine_already_applied_page = False
            break
        if is_genuine_already_applied_page:
          input("Confirm")
          self.__driver.close()
          self.__driver.switch_to.window(self.__driver.window_handles[0])
          return
      elif "smartapply.indeed.com/beta/indeedapply/form/applied":
        self.__driver.close()
        self.__driver.switch_to.window(self.__driver.window_handles[0])
      else:
        logging.warning("Might have found an unhandled page... Trying again...")
        time.sleep(0.5)

  def __resume_preview_is_visible(self) -> bool:
    try:
      self.__selenium_helper.get_element_by_exact_text("Resume options", ElementType.SPAN)
      return True
    except NoSuchElementException:
      return False

  def __select_first_resume(self, timeout=1) -> None:
    resume_preview_id = ":r0:-file-resume-expandable-region"
    start_time = time.time()
    while time.time() - start_time < timeout:
      try:
        resume_preview = self.__driver.find_element(By.ID, resume_preview_id)
        if not resume_preview.is_displayed():
          first_resume_span_xpath = "/html/body/div[2]/div/div[1]/div/div/div[2]/div[2]/div/div/main/div[2]/div/fieldset/div/label/span/span[2]/span[1]"    # pylint: disable=line-too-long
          first_resume_span = self.__driver.find_element(By.XPATH, first_resume_span_xpath)
          first_resume_span.click()
          return
      except NoSuchElementException:
        logging.debug("Waiting for first resume span to load...")
        time.sleep(0.1)
    raise TimeoutError("Timed out waiting for first resume span.")

  def __handle_company_name_input(self, timeout=1) -> None:
    relevant_experience_company = self.__indeed_config.relevant_experience_company
    potential_company_name_input_names = [
      "???",
      "companyName"
    ]
    start_time = time.time()
    while time.time() - start_time < timeout:
      for name in potential_company_name_input_names:
        try:
          company_input = self.__driver.find_element(By.NAME, name)
          self.__selenium_helper.write_to_input(relevant_experience_company, company_input)
          return
        except NoSuchElementException:
          pass
    raise NoSuchElementException("Failed to find company input.")

  def __handle_job_title_input(self) -> None:
    relevant_experience_job_title = self.__indeed_config.relevant_experience_job_title
    potential_job_title_input_names = [
      "???",
      "jobTitle"
    ]
    for name in potential_job_title_input_names:
      try:
        job_title_input = self.__driver.find_element(By.NAME, name)
        self.__selenium_helper.write_to_input(relevant_experience_job_title, job_title_input)
        return
      except NoSuchElementException:
        pass
    raise NoSuchElementException("Failed to find job title input.")

  def __handle_phone_number_input(self) -> None:
    phone_number = self.__universal_config.about_me.contact.phone_number
    potential_phone_number_input_names = [
      "phone",
      "phoneNumber"
    ]
    for name in potential_phone_number_input_names:
      try:
        phone_number_input = self.__driver.find_element(By.NAME, name)
        self.__selenium_helper.write_to_input(phone_number, phone_number_input)
        return
      except NoSuchElementException:
        pass
    raise NoSuchElementException("Failed to find phone number input.")

  def __handle_last_name_input(self) -> None:
    last_name = self.__universal_config.about_me.name.last
    potential_last_name_input_names = [
      "names-last-name",
      "lastName"
    ]
    for name in potential_last_name_input_names:
      try:
        last_name_input = self.__driver.find_element(By.NAME, name)
        self.__selenium_helper.write_to_input(last_name, last_name_input)
        return
      except NoSuchElementException:
        pass
    raise NoSuchElementException("Failed to find last name input.")

  def __handle_first_name_input(self) -> None:
    first_name = self.__universal_config.about_me.name.first
    potential_first_name_input_names = [
      "names-first-name",
      "firstName"
    ]
    for name in potential_first_name_input_names:
      try:
        first_name_input = self.__driver.find_element(By.NAME, name)
        self.__selenium_helper.write_to_input(first_name, first_name_input)
        return
      except NoSuchElementException:
        pass
    raise NoSuchElementException("Failed to find first name input.")

  def __handle_street_address_input(self) -> None:
    street_address_input_name = "location-address"
    street_address = self.__universal_config.about_me.location.street_address
    street_address_input = self.__driver.find_element(By.NAME, street_address_input_name)
    self.__selenium_helper.write_to_input(street_address, street_address_input)

  def __handle_city_state_input(self) -> None:
    city_state = f"{self.__universal_config.about_me.location.city}, {self.__universal_config.about_me.location.state_code}"
    potential_city_state_input_names = [
      "location-locality",
      "location.city"
    ]
    for name in potential_city_state_input_names:
      try:
        city_state_input = self.__driver.find_element(By.NAME, name)
        self.__selenium_helper.write_to_input(city_state, city_state_input)
        return
      except NoSuchElementException:
        pass
    raise NoSuchElementException("Failed to find city-state input.")

  def __handle_postal_code_input(self) -> None:
    postal_code_input_name = "location-postal-code"
    postal_code = self.__universal_config.about_me.location.postal_code
    postal_code_input = self.__driver.find_element(By.NAME, postal_code_input_name)
    self.__selenium_helper.write_to_input(postal_code, postal_code_input)

  def __click_continue_button(self, timeout=5) -> None:
    body = self.__driver.find_element(By.TAG_NAME, "body")
    body.click()
    time.sleep(0.1)
    start_time = time.time()
    while time.time() - start_time < timeout:
      try:
        continue_button = self.__selenium_helper.get_element_by_exact_text("Continue", ElementType.BUTTON)
        continue_button.click()
        return
      except NoSuchElementException:
        body = self.__driver.find_element(By.TAG_NAME, "body")
        body.click()
        logging.debug("Waiting for continue button to be clickable...")
        time.sleep(0.1)
    raise NoSuchElementException("Failed to find continue button.")
