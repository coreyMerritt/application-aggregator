import logging
import time
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.common.exceptions import ElementClickInterceptedException, NoSuchElementException
from models.configs.universal_config import UniversalConfig
from models.enums.element_type import ElementType
from services.misc.selenium_helper import SeleniumHelper


class IndeedLocationStepper:
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
    LOCATION_URL = "smartapply.indeed.com/beta/indeedapply/form/profile-location"
    return LOCATION_URL in self.__driver.current_url

  def resolve(self) -> None:
    self.__handle_street_address_input()
    self.__handle_city_state_input()
    self.__handle_postal_code_input()
    self.__click_continue_button()
    while self.is_present():
      logging.debug("Waiting for profile location page to resolve...")
      time.sleep(0.5)

  def __handle_street_address_input(self) -> None:
    street_address_input_name = "location-address"
    street_address = self.__universal_config.about_me.location.street_address
    street_address_input = self.__driver.find_element(By.NAME, street_address_input_name)
    self.__selenium_helper.write_to_input(street_address, street_address_input)

  def __handle_city_state_input(self) -> None:
    city = self.__universal_config.about_me.location.city
    state_code = self.__universal_config.about_me.location.state_code
    city_state = f"{city}, {state_code}"
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
    self.__selenium_helper.write_to_input(str(postal_code), postal_code_input)

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
