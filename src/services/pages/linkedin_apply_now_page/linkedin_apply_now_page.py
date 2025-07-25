import logging
import time
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement
from selenium.common.exceptions import ElementClickInterceptedException, NoSuchElementException
from models.enums.element_type import ElementType
from models.configs.linkedin_config import LinkedinConfig
from models.configs.universal_config import UniversalConfig
from services.misc.selenium_helper import SeleniumHelper
from services.pages.linkedin_apply_now_page.steppers.linkedin_contact_info_stepper import LinkedinContactInfoStepper
from services.pages.linkedin_apply_now_page.steppers.linkedin_education_stepper import LinkedinEducationStepper
from services.pages.linkedin_apply_now_page.steppers.linkedin_home_address_stepper import LinkedinHomeAddressStepper
from services.pages.linkedin_apply_now_page.steppers.linkedin_resume_stepper import LinkedinResumeStepper
from services.pages.linkedin_apply_now_page.steppers.linkedin_voluntary_self_identification_stepper import LinkedinVoluntarySelfIdentificationStepper        # pylint: disable=line-too-long
from services.pages.linkedin_apply_now_page.steppers.linkedin_work_experience_stepper import LinkedinWorkExperienceStepper     # pylint: disable=line-too-long


class LinkedinApplyNowPage:
  __driver: uc.Chrome
  __selenium_helper: SeleniumHelper
  __contact_info_stepper: LinkedinContactInfoStepper
  __home_address_stepper: LinkedinHomeAddressStepper
  __resume_stepper: LinkedinResumeStepper
  __voluntary_self_indentification_stepper: LinkedinVoluntarySelfIdentificationStepper
  __work_experience_stepper: LinkedinWorkExperienceStepper
  __education_stepper: LinkedinEducationStepper

  def __init__(
    self,
    driver: uc.Chrome,
    selenium_helper: SeleniumHelper,
    linkedin_config: LinkedinConfig,
    universal_config: UniversalConfig
  ):
    self.__driver = driver
    self.__selenium_helper = selenium_helper
    self.__contact_info_stepper = LinkedinContactInfoStepper(
      selenium_helper,
      linkedin_config,
      universal_config
    )
    self.__home_address_stepper = LinkedinHomeAddressStepper(
      selenium_helper,
      universal_config
    )
    self.__resume_stepper = LinkedinResumeStepper(
      selenium_helper,
      universal_config
    )
    self.__voluntary_self_indentification_stepper = LinkedinVoluntarySelfIdentificationStepper(
      selenium_helper,
      universal_config
    )
    self.__work_experience_stepper = LinkedinWorkExperienceStepper(
      driver,
      selenium_helper,
      universal_config
    )
    self.__education_stepper = LinkedinEducationStepper(
      driver,
      selenium_helper,
      universal_config
    )

  def apply(self) -> None:
    logging.debug("Filling out application...")
    easy_apply_div_xpath = "/html/body/div[4]/div/div"
    easy_apply_div = self.__driver.find_element(By.XPATH, easy_apply_div_xpath)
    while self.__driver.find_element(By.XPATH, easy_apply_div_xpath):
      if self.__is_contact_info_page(easy_apply_div):
        self.__contact_info_stepper.resolve(easy_apply_div)
      elif self.__is_home_address_page(easy_apply_div):
        self.__home_address_stepper.resolve(easy_apply_div)
      elif self.__is_resume_page(easy_apply_div):
        self.__resume_stepper.resolve(easy_apply_div)
      elif self.__is_voluntary_self_identification_stepper(easy_apply_div):
        self.__voluntary_self_indentification_stepper.resolve(easy_apply_div)
      elif self.__is_work_experience_stepper(easy_apply_div):
        self.__work_experience_stepper.resolve(easy_apply_div)
      elif self.__is_education_stepper(easy_apply_div):
        self.__education_stepper.resolve(easy_apply_div)
      if self.__is_automation_roadblock(easy_apply_div):
        return
      elif self.__is_final_stepper(easy_apply_div):
        if self.__is_easy_apply_scrollable_div():
          self.__scroll_to_bottom()
        return
      else:
        self.__continue_stepper(easy_apply_div)
        time.sleep(0.1)
        if self.__some_field_was_left_blank(easy_apply_div):
          input("Some field was left blank -- lets fix that.")
          return

  def __is_automation_roadblock(self, easy_apply_div: WebElement) -> bool:
    return (
      self.__selenium_helper.exact_text_is_present("Additional", ElementType.H3, easy_apply_div)
      or self.__selenium_helper.exact_text_is_present("Additional Questions", ElementType.H3, easy_apply_div)
    )

  def __is_final_stepper(self, easy_apply_div: WebElement) -> bool:
    return (
      self.__selenium_helper.exact_text_is_present("Submit application", ElementType.BUTTON, easy_apply_div)
      or self.__selenium_helper.exact_text_is_present('Review your application', ElementType.H3, easy_apply_div)
    )

  def __continue_stepper(self, easy_apply_div: WebElement) -> None:
    while True:
      try:
        next_span = self.__selenium_helper.get_element_by_exact_text("Next", ElementType.SPAN, easy_apply_div)
        next_button = next_span.find_element(By.XPATH, "..")
        next_button.click()
        return
      except ElementClickInterceptedException:
        logging.debug("ElementClickInterceptedException. Trying again...")
        time.sleep(0.1)
      except NoSuchElementException:
        logging.debug("NoSuchElementException. Trying again...")
        time.sleep(0.1)
      try:
        review_span = self.__selenium_helper.get_element_by_exact_text("Review", ElementType.SPAN, easy_apply_div)
        review_button = review_span.find_element(By.XPATH, "..")
        review_button.click()
        return
      except ElementClickInterceptedException:
        logging.debug("ElementClickInterceptedException... trying again...")
        time.sleep(0.1)
      except NoSuchElementException:
        logging.debug("NoSuchElementException. Trying again...")
        time.sleep(0.1)

  def __some_field_was_left_blank(self, easy_apply_div: WebElement) -> bool:
    try:
      self.__selenium_helper.get_element_by_exact_text(
        "Please enter a valid answer",
        ElementType.SPAN,
        easy_apply_div
      )
      return True
    except NoSuchElementException:
      return False

  def __is_easy_apply_scrollable_div(self) -> bool:
    easy_apply_scrollable_div_xpath = "/html/body/div[4]/div/div/div[2]"
    try:
      self.__driver.find_element(By.XPATH, easy_apply_scrollable_div_xpath)
      return True
    except NoSuchElementException:
      return False

  def __get_easy_apply_scrollable_div(self) -> WebElement:
    assert self.__is_easy_apply_scrollable_div()
    easy_apply_scrollable_div_xpath = "/html/body/div[4]/div/div/div[2]"
    easy_apply_scrollable_div = self.__driver.find_element(By.XPATH, easy_apply_scrollable_div_xpath)
    return easy_apply_scrollable_div

  def __scroll_to_bottom(self) -> None:
    easy_apply_scrollable_div = self.__get_easy_apply_scrollable_div()
    self.__driver.execute_script(
      "arguments[0].scrollTop = arguments[0].scrollHeight;",
      easy_apply_scrollable_div
    )

  def __is_contact_info_page(self, easy_apply_div: WebElement) -> bool:
    return self.__selenium_helper.exact_text_is_present(
      "Contact info",
      ElementType.H3,
      easy_apply_div
    )

  def __is_home_address_page(self, easy_apply_div: WebElement) -> bool:
    return self.__selenium_helper.exact_text_is_present(
      "Home address",
      ElementType.H3,
      easy_apply_div
    )

  def __is_resume_page(self, easy_apply_div: WebElement) -> bool:
    return self.__selenium_helper.exact_text_is_present(
      "Resume",
      ElementType.H3,
      easy_apply_div
    )

  def __is_voluntary_self_identification_stepper(self, easy_apply_div: WebElement) -> bool:
    return self.__selenium_helper.exact_text_is_present(
      "Voluntary self identification",
      ElementType.H3,
      easy_apply_div
    )

  def __is_work_experience_stepper(self, easy_apply_div: WebElement) -> bool:
    return self.__selenium_helper.exact_text_is_present(
      "Work experience",
      ElementType.SPAN,
      easy_apply_div
    )

  def __is_education_stepper(self, easy_apply_div: WebElement) -> bool:
    return self.__selenium_helper.exact_text_is_present(
      "Education",
      ElementType.SPAN,
      easy_apply_div
    )
