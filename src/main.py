#!/usr/bin/env python3

import argparse
import logging
import time
import traceback
import yaml
import undetected_chromedriver as uc
from dacite import from_dict
from models.configs.full_config import FullConfig
from models.enums.platform import Platform
from services.misc.database_manager import DatabaseManager
from services.misc.proxy_manager import ProxyManager
from services.misc.selenium_helper import SeleniumHelper
from services.orchestration.glassdoor_orchestration_engine import GlassdoorOrchestrationEngine
from services.orchestration.indeed_orchestration_engine import IndeedOrchestrationEngine
from services.orchestration.linkedin_orchestration_engine import LinkedinOrchestrationEngine
from services.pages.indeed_apply_now_page.indeed_apply_now_page import IndeedApplyNowPage


class Start:
  __config: FullConfig
  __driver: uc.Chrome
  __proxy_manager: ProxyManager
  __selenium_helper: SeleniumHelper
  __database_manager: DatabaseManager

  def __init__(self):
    self.__configure_logger()
    with open("config.yml", "r", encoding='utf-8') as config_file:
      raw_config = yaml.safe_load(config_file)
    self.__config = from_dict(data_class=FullConfig, data=raw_config)
    self.__database_manager = DatabaseManager(self.__config.system.database)
    self.__proxy_manager = ProxyManager(self.__config.system.proxies, self.__database_manager)
    self.__selenium_helper = SeleniumHelper(
      self.__config.system,
      self.__config.quick_settings.bot_behavior.default_page_load_timeout,
      self.__proxy_manager
    )
    self.__driver = self.__selenium_helper.get_driver()

  def execute(self):
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command")
    subparsers.required = True
    apply_parser = subparsers.add_parser("apply", help="Aggregates jobs; fills out some data; scrapes job info.")
    apply_parser.set_defaults(func=self.apply)
    output_parser = subparsers.add_parser("output", help="Outputs scrapped job info.")
    output_parser.add_argument("--ignore-terms", type=int, required=True)
    output_parser.set_defaults(func=self.__output)
    args = parser.parse_args()
    args.func(args)

  def apply(self, args: argparse.Namespace):    # pylint: disable=unused-argument
    try:
      for some_platform in self.__config.quick_settings.bot_behavior.platform_order:
        platform = str(some_platform).lower()
        if platform == Platform.LINKEDIN.value.lower():
          self.__apply_on_linkedin()
        elif platform == Platform.GLASSDOOR.value.lower():
          self.__apply_on_glassdoor()
        elif platform == Platform.INDEED.value.lower():
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
      self.__database_manager,
      self.__config.universal,
      self.__config.quick_settings,
      self.__config.indeed
    )
    indeed_orchestration_engine.apply()
    if self.__config.quick_settings.bot_behavior.pause_after_each_platform:
      input("\nFinished with Indeed. Press enter to proceed...")
    if self.__config.quick_settings.bot_behavior.remove_tabs_after_each_platform:
      self.__remove_all_tabs_except_first()

  def __apply_on_glassdoor(self) -> None:
    glassdoor_orchestration_engine = GlassdoorOrchestrationEngine(
      self.__driver,
      self.__selenium_helper,
      self.__database_manager,
      self.__config.universal,
      self.__config.quick_settings,
      self.__config.glassdoor,
      IndeedApplyNowPage(
        self.__driver,
        self.__selenium_helper,
        self.__config.universal,
        self.__config.quick_settings
      )
    )
    glassdoor_orchestration_engine.apply()
    if self.__config.quick_settings.bot_behavior.pause_after_each_platform:
      input("\nFinished with Glassdoor. Press enter to proceed...")
    if self.__config.quick_settings.bot_behavior.remove_tabs_after_each_platform:
      self.__remove_all_tabs_except_first()

  def __apply_on_linkedin(self) -> None:
    linkedin_orchestration_engine = LinkedinOrchestrationEngine(
      self.__driver,
      self.__selenium_helper,
      self.__database_manager,
      self.__config.universal,
      self.__config.quick_settings,
      self.__config.linkedin,
      self.__proxy_manager
    )
    linkedin_orchestration_engine.apply()
    if self.__config.quick_settings.bot_behavior.pause_after_each_platform:
      input("\nFinished with Linkedin. Press enter to proceed...")
    if self.__config.quick_settings.bot_behavior.remove_tabs_after_each_platform:
      self.__remove_all_tabs_except_first()

  def __remove_all_tabs_except_first(self) -> None:
    while len(self.__driver.window_handles) > 1:
      self.__driver.switch_to.window(self.__driver.window_handles[-1])
      self.__driver.close()
    self.__driver.switch_to.window(self.__driver.window_handles[0])

  def __output(self, args: argparse.Namespace) -> None:
    if args.ignore_terms:
      self.__print_highest_ignore_terms(args.ignore_terms)

  def __print_highest_ignore_terms(self, limit: int) -> None:
    print("\n" + "Brief Job Listing Ignore Terms".center(50))
    keywords = self.__database_manager.get_highest_brief_job_listing_ignore_keywords(limit)
    print(f"{"Category":>11}   {"Term":<20} {"Count"}")
    print("─" * 50)
    for category, term, count in keywords:
      print(f"{category:>11}   {term:<20} {count:07,d}")
    print("\n" + "Job Listing Ignore Terms".center(50))
    keywords = self.__database_manager.get_highest_job_listing_ignore_keywords(limit)
    print(f"{"Category":>11}   {"Term":<20} {"Count"}")
    print("─" * 50)
    for category, term, count in keywords:
      print(f"{category:>11}   {term:<20} {count:07,d}")
    print()

Start().execute()
