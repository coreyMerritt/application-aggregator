import logging
import time
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException
from models.enums.element_type import ElementType
from models.configs.universal_config import UniversalConfig
from services.misc.selenium_helper import SeleniumHelper
from services.pages.indeed_apply_now_page.steppers.indeed_commute_check_stepper import IndeedCommuteCheckStepper
from services.pages.indeed_apply_now_page.steppers.indeed_contact_info_stepper import IndeedContactInfoStepper
from services.pages.indeed_apply_now_page.steppers.indeed_location_stepper import IndeedLocationStepper
from services.pages.indeed_apply_now_page.steppers.indeed_relevant_experience_stepper import (
  IndeedRelevantExperienceStepper
)
from services.pages.indeed_apply_now_page.steppers.indeed_resume_stepper import IndeedResumeStepper


class IndeedApplyNowPage:
  __driver: uc.Chrome
  __relevant_experience_stepper: IndeedRelevantExperienceStepper
  __resume_stepper: IndeedResumeStepper
  __location_stepper: IndeedLocationStepper
  __contact_info_stepper: IndeedContactInfoStepper
  __commute_check_stepper: IndeedCommuteCheckStepper

  def __init__(
    self,
    driver: uc.Chrome,
    selenium_helper: SeleniumHelper,
    universal_config: UniversalConfig
  ):
    self.__driver = driver
    self.__relevant_experience_stepper = IndeedRelevantExperienceStepper(
      driver,
      selenium_helper,
      universal_config
    )
    self.__resume_stepper = IndeedResumeStepper(
      driver,
      selenium_helper,
      universal_config
    )
    self.__location_stepper = IndeedLocationStepper(
      driver,
      selenium_helper,
      universal_config
    )
    self.__contact_info_stepper = IndeedContactInfoStepper(
      driver,
      selenium_helper,
      universal_config
    )
    self.__commute_check_stepper = IndeedCommuteCheckStepper(
      driver,
      selenium_helper
    )

  def is_present(self) -> bool:
    return "smartapply.indeed.com" in self.__driver.current_url

  def apply(self) -> None:
    RELEVANT_EXPERIENCE_URL = "smartapply.indeed.com/beta/indeedapply/form/resume-module/relevant-experience"
    RESUME_URL = "smartapply.indeed.com/beta/indeedapply/form/resume"
    LOCATION_URL = "smartapply.indeed.com/beta/indeedapply/form/profile-location"
    CONTACT_INFO_URL = "smartapply.indeed.com/beta/indeedapply/form/contact-info"
    POTENTIAL_ALREADY_APPLIED_URL = "smartapply.indeed.com/beta/indeedapply/postresumeapply"
    ALREADY_APPLIED_URL = "smartapply.indeed.com/beta/indeedapply/form/applied"
    COMMUTE_CHECK_URL = "smartapply.indeed.com/beta/indeedapply/form/commute-check"
    FINISHED_WITH_APPLY_NOW_URL = "smartapply.indeed.com/beta/indeedapply/form/review"
    VAGUE_QUESTIONS_URL = "smartapply.indeed.com/beta/indeedapply/form/questions-module/questions/1"
    DEMOGRAPHIC_QUESTIONS_URL = "smartapply.indeed.com/beta/indeedapply/form/demographic-questions/1"
    while self.is_present():
      URL = self.__driver.current_url
      if RELEVANT_EXPERIENCE_URL in URL:
        self.__relevant_experience_stepper.resolve(RELEVANT_EXPERIENCE_URL)
      elif RESUME_URL in URL:
        self.__resume_stepper.resolve(RESUME_URL)
      elif LOCATION_URL in URL:
        self.__location_stepper.resolve(LOCATION_URL)
      elif CONTACT_INFO_URL in URL:
        self.__contact_info_stepper.resolve(CONTACT_INFO_URL)
      elif COMMUTE_CHECK_URL in URL:
        self.__commute_check_stepper.resolve(COMMUTE_CHECK_URL)
      elif POTENTIAL_ALREADY_APPLIED_URL in URL:
        IS_GENUINE_ALREADY_APPLIED_PAGE = self.__is_already_applied_page(POTENTIAL_ALREADY_APPLIED_URL)
        if IS_GENUINE_ALREADY_APPLIED_PAGE:
          self.__driver.close()
          self.__driver.switch_to.window(self.__driver.window_handles[0])
          return
      elif ALREADY_APPLIED_URL in URL:
        self.__driver.close()
        self.__driver.switch_to.window(self.__driver.window_handles[0])
      elif VAGUE_QUESTIONS_URL in URL:
        self.__driver.switch_to.window(self.__driver.window_handles[0])
        return
      elif DEMOGRAPHIC_QUESTIONS_URL in URL:
        self.__driver.switch_to.window(self.__driver.window_handles[0])
        return
      elif FINISHED_WITH_APPLY_NOW_URL in URL:
        self.__scroll_to_bottom()
        self.__driver.switch_to.window(self.__driver.window_handles[0])
        return
      else:
        logging.warning("Might have found an unhandled page. Trying again...")
        time.sleep(0.5)

  def __is_already_applied_page(self, potential_already_applied_url: str) -> bool:
    confirm_time = 7
    start_time = time.time()
    IS_GENUINE_ALREADY_APPLIED_PAGE = True
    while time.time() - start_time < confirm_time:
      if not potential_already_applied_url in self.__driver.current_url:
        IS_GENUINE_ALREADY_APPLIED_PAGE = False
        break
    return IS_GENUINE_ALREADY_APPLIED_PAGE

  def __scroll_to_bottom(self) -> None:
    self.__driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
