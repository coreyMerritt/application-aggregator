#!/usr/bin/env python3

import logging
import time
import traceback
import yaml
from box import Box
import undetected_chromedriver as uc
from models.configs.database_config import DatabaseConfig
from services.misc.database_manager import DatabaseManager
from services.misc.selenium_helper import SeleniumHelper
from services.orchestration.glassdoor_orchestration_engine import GlassdoorOrchestrationEngine
from services.orchestration.indeed_orchestration_engine import IndeedOrchestrationEngine
from services.orchestration.linkedin_orchestration_engine import LinkedinOrchestrationEngine
from services.pages.indeed_apply_now_page.indeed_apply_now_page import IndeedApplyNowPage


DEFAULT_PAGE_LOAD_TIMEOUT = 30
APPLY_ON_INDEED = False
APPLY_ON_GLASSDOOR = True
APPLY_ON_LINKEDIN = True
INPUT_AFTER_EACH_SERVICE = True
REMOVE_TABS_AFTER_EACH_SERVICE = False

def __main__():
  try:
    handle_logger()
    with open("config.yml", "r", encoding='utf-8') as config_file:
      config = Box(yaml.safe_load(config_file))
    options = uc.ChromeOptions()
    options.binary_location = config.browser.path
    driver = uc.Chrome(options=options)
    selenium_helper = SeleniumHelper(driver, DEFAULT_PAGE_LOAD_TIMEOUT)
    database_config = DatabaseConfig(
      engine=config.database.engine,
      username=config.database.username,
      password=config.database.password,
      host=config.database.host,
      port=config.database.port,
      name=config.database.name
    )
    database_manager = DatabaseManager(database_config)

    if APPLY_ON_INDEED:
      apply_on_indeed(driver, selenium_helper, config)
    if APPLY_ON_GLASSDOOR:
      apply_on_glassdoor(driver, selenium_helper, config)
    if APPLY_ON_LINKEDIN:
      apply_on_linkedin(driver, selenium_helper, database_manager, config)

    input("\n\tPress enter to exit...")
    remove_all_tabs_except_first(driver)
  except Exception as e:
    traceback.print_exc()
    logging.error("\n\nException of type %s was thrown...", type(e).__name__)
    input("\tPress enter to exit...")
  finally:
    driver.quit()

def apply_on_indeed(driver: uc.Chrome, selenium_helper: SeleniumHelper, config: Box) -> None:
  indeed_orchestration_engine = IndeedOrchestrationEngine(
    driver,
    selenium_helper,
    config.indeed,
    config.universal
  )
  indeed_orchestration_engine.apply()
  if INPUT_AFTER_EACH_SERVICE:
    input("\nFinished with Indeed. Press enter to proceed to Glassdoor...")
  if REMOVE_TABS_AFTER_EACH_SERVICE:
    remove_all_tabs_except_first(driver)

def apply_on_glassdoor(driver: uc.Chrome, selenium_helper: SeleniumHelper, config: Box) -> None:
  glassdoor_orchestration_engine = GlassdoorOrchestrationEngine(
    driver,
    selenium_helper,
    config.glassdoor,
    config.universal,
    IndeedApplyNowPage(driver, selenium_helper, config.universal)
  )
  glassdoor_orchestration_engine.apply()
  if INPUT_AFTER_EACH_SERVICE:
    input("\nFinished with Glassdoor. Press enter to proceed to Linkedin...")
  if REMOVE_TABS_AFTER_EACH_SERVICE:
    remove_all_tabs_except_first(driver)

def apply_on_linkedin(
  driver: uc.Chrome,
  selenium_helper: SeleniumHelper,
  database_manager: DatabaseManager,
  config: Box
) -> None:
  linkedin_orchestration_engine = LinkedinOrchestrationEngine(
    driver,
    selenium_helper,
    database_manager,
    config.linkedin,
    config.universal
  )
  linkedin_orchestration_engine.apply()
  if INPUT_AFTER_EACH_SERVICE:
    input("\nFinished with Linkedin.")
  if REMOVE_TABS_AFTER_EACH_SERVICE:
    remove_all_tabs_except_first(driver)

def handle_logger():
  def custom_time(record):
    t = time.localtime(record.created)
    return time.strftime("%Y-%m-%d %H:%M:%S", t) + f".{int(record.msecs):03d}"
  logging.basicConfig(
    format='[%(asctime)s] [%(levelname)s] %(message)s',
    datefmt='',
    level=logging.DEBUG
  )
  logging.Formatter.converter = time.localtime
  logging.Formatter.formatTime = lambda self, record, datefmt=None: custom_time(record)
  noisy_loggers = [
    "selenium", "urllib3", "httpx", "asyncio", "trio", "PIL.Image", 
    "undetected_chromedriver", "werkzeug", "hpack", "chardet.charsetprober", 
    "websockets", "chromedriver_autoinstaller"
  ]
  for name in noisy_loggers:
    logging.getLogger(name).setLevel(logging.WARNING)

def remove_all_tabs_except_first(driver: uc.Chrome):
  while len(driver.window_handles) > 1:
    driver.switch_to.window(driver.window_handles[-1])
    driver.close()
  driver.switch_to.window(driver.window_handles[0])


__main__()
