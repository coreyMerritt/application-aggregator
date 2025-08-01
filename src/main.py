#!/usr/bin/env python3

import logging
import time
import traceback
import yaml
from box import Box
import undetected_chromedriver as uc
from models.configs.glassdoor_config import GlassdoorConfig
from models.configs.indeed_config import IndeedConfig
from models.configs.linkedin_config import LinkedinConfig
from models.configs.system_config import SystemConfig
from models.configs.quick_settings import QuickSettings
from models.configs.universal_config import UniversalConfig
from services.misc.database_manager import DatabaseManager
from services.misc.proxy_manager import ProxyManager
from services.misc.selenium_helper import SeleniumHelper
from services.orchestration.glassdoor_orchestration_engine import GlassdoorOrchestrationEngine
from services.orchestration.indeed_orchestration_engine import IndeedOrchestrationEngine
from services.orchestration.linkedin_orchestration_engine import LinkedinOrchestrationEngine
from services.pages.indeed_apply_now_page.indeed_apply_now_page import IndeedApplyNowPage

class Start:
  __quick_settings: QuickSettings
  __system_config: SystemConfig
  __universal_config: UniversalConfig
  __linkedin_config: LinkedinConfig
  __glassdoor_config: GlassdoorConfig
  __indeed_config: IndeedConfig
  __driver: uc.Chrome
  __proxy_manager: ProxyManager
  __selenium_helper: SeleniumHelper
  __database_manager: DatabaseManager

  def __init__(self):
    self.__configure_logger()
    with open("config.yml", "r", encoding='utf-8') as config_file:
      config = Box(yaml.safe_load(config_file))
    self.__quick_settings = QuickSettings(
      bot_behavior=config.quick_settings.bot_behavior
    )
    self.__system_config = SystemConfig(
      browser=config.system.browser,
      database=config.system.database,
      proxies=config.system.proxies
    )
    self.__universal_config = UniversalConfig(
      about_me=config.universal.about_me,
      bot_behavior=config.universal.bot_behavior,
      search=config.universal.search
    )
    self.__linkedin_config = LinkedinConfig(
      easy_apply_only=config.linkedin.easy_apply_only,
      email=config.linkedin.email,
      password=config.linkedin.password
    )
    self.__glassdoor_config = GlassdoorConfig(
      email=config.glassdoor.email,
      password=config.glassdoor.password
    )
    self.__indeed_config = IndeedConfig(
      apply_now_only=config.indeed.apply_now_only,
      email=config.indeed.email
    )
    self.__database_manager = DatabaseManager(self.__system_config.database)
    self.__proxy_manager = ProxyManager(self.__system_config.proxies, self.__database_manager)
    self.__selenium_helper = SeleniumHelper(
      self.__system_config,
      self.__quick_settings.bot_behavior.default_page_load_timeout,
      self.__proxy_manager
    )
    self.__driver = self.__selenium_helper.get_driver()

  def execute(self):
    try:
      for platform in self.__quick_settings.bot_behavior.platform_order:
        if platform == "linkedin":
          self.__apply_on_linkedin()
        elif platform == "glassdoor":
          self.__apply_on_glassdoor()
        elif platform == "indeed":
          self.__apply_on_indeed()

      input("\n\tPress enter to exit...")
      self.__remove_all_tabs_except_first()
    except Exception:
      traceback.print_exc()
      input("\tPress enter to exit...")
    finally:
      self.__driver.quit()

  def __configure_logger(self):
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

  def __apply_on_indeed(self) -> None:
    indeed_orchestration_engine = IndeedOrchestrationEngine(
      self.__driver,
      self.__selenium_helper,
      self.__universal_config,
      self.__quick_settings,
      self.__indeed_config
    )
    indeed_orchestration_engine.apply()
    if self.__quick_settings.bot_behavior.pause_after_each_platform:
      input("\nFinished with Indeed. Press enter to proceed...")
    if self.__quick_settings.bot_behavior.remove_tabs_after_each_platform:
      self.__remove_all_tabs_except_first()

  def __apply_on_glassdoor(self) -> None:
    glassdoor_orchestration_engine = GlassdoorOrchestrationEngine(
      self.__driver,
      self.__selenium_helper,
      self.__universal_config,
      self.__quick_settings,
      self.__glassdoor_config,
      IndeedApplyNowPage(self.__driver, self.__selenium_helper, self.__universal_config)
    )
    glassdoor_orchestration_engine.apply()
    if self.__quick_settings.bot_behavior.pause_after_each_platform:
      input("\nFinished with Glassdoor. Press enter to proceed...")
    if self.__quick_settings.bot_behavior.remove_tabs_after_each_platform:
      self.__remove_all_tabs_except_first()

  def __apply_on_linkedin(self) -> None:
    linkedin_orchestration_engine = LinkedinOrchestrationEngine(
      self.__driver,
      self.__selenium_helper,
      self.__database_manager,
      self.__universal_config,
      self.__quick_settings,
      self.__linkedin_config,
      self.__proxy_manager
    )
    linkedin_orchestration_engine.apply()
    if self.__quick_settings.bot_behavior.pause_after_each_platform:
      input("\nFinished with Linkedin. Press enter to proceed...")
    if self.__quick_settings.bot_behavior.remove_tabs_after_each_platform:
      self.__remove_all_tabs_except_first()

  def __remove_all_tabs_except_first(self):
    while len(self.__driver.window_handles) > 1:
      self.__driver.switch_to.window(self.__driver.window_handles[-1])
      self.__driver.close()
    self.__driver.switch_to.window(self.__driver.window_handles[0])


Start().execute()
