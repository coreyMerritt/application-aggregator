from abc import ABC
import logging
import re
from typing import List
from models.configs.quick_settings import QuickSettings
from models.configs.universal_config import SearchSalary, UniversalConfig


class BriefJobListing(ABC):
  __title: str
  __company: str
  __location: str
  __min_pay: float | None = None
  __max_pay: float | None = None

  def get_title(self) -> str:
    return self.__title

  def get_company(self) -> str:
    return self.__company

  def get_location(self) -> str:
    return self.__location

  def get_min_pay(self) -> float | None:
    return self.__min_pay

  def get_max_pay(self) -> float | None:
    return self.__max_pay

  def set_title(self, title: str) -> None:
    self.__title = title

  def set_company(self, company: str) -> None:
    self.__company = company

  def set_location(self, location: str) -> None:
    self.__location = location

  def set_min_pay(self, pay: float | None) -> None:
    self.__min_pay = pay

  def set_max_pay(self, pay: float | None) -> None:
    self.__max_pay = pay

  def passes_filter_check(self, universal_config: UniversalConfig, quick_settings: QuickSettings) -> bool:
    if quick_settings.bot_behavior.platinum_star_only:
      if not self._is_gold_star_listing(universal_config):
        logging.info("Ignoring Brief Job Listing because it is not a gold star.\n")
        return False
      else:
        if self._passes_ignore_filters(universal_config):
          logging.info("Brief Job Listing passes filter check.")
          return True
        else:
          logging.info("Ignoring Brief Job Listing because ignore term was found.\n")
          return False
    elif quick_settings.bot_behavior.gold_star_only:
      if self._is_gold_star_listing(universal_config):
        logging.info("Brief Job Listing passes because its a gold star.")
        return True
      else:
        logging.info("Ignoring Brief Job Listing because it is not a gold star.\n")
        return False
    else:
      if self._is_gold_star_listing(universal_config):
        logging.info("Brief Job Listing passes because its a gold star.")
        return True
      else:
        if self._passes_ignore_filters(universal_config):
          logging.info("Brief Job Listing passes because it matches no terms in ignore.")
          return True
        else:
          logging.info("Ignoring Brief Job Listing because ignore term was found.\n")
          return False

  def print(self) -> None:
    logging.info(
      "\nTitle:\t\t%s\nCompany:\t%s\nLocation:\t%s\nMin Pay:\t%s\nMax Pay:\t%s\n",
      self.__title,
      self.__company,
      self.__location,
      self.__min_pay,
      self.__max_pay
    )

  def to_dict(self) -> dict[str, str | float | None]:
    return {
      "title": self.__title,
      "company": self.__company,
      "location": self.__location,
      "min_pay": self.__min_pay,
      "max_pay": self.__max_pay
    }

  def to_minimal_dict(self) -> dict[str, str]:
    return {
      "title": self.__title,
      "company": self.__company
    }

  def _is_gold_star_listing(self, universal_config: UniversalConfig) -> bool:
    title = self.__title.lower().strip()
    for gold_star_title in universal_config.bot_behavior.gold_star.titles:
      if self._phrase_is_in_phrase(gold_star_title, title):
        return True
    company = self.__company.lower().strip()
    for gold_star_company in universal_config.bot_behavior.gold_star.companies:
      if self._phrase_is_in_phrase(gold_star_company, company):
        return True
    location = self.__location.lower().strip()
    for gold_star_location in universal_config.bot_behavior.gold_star.locations:
      if self._phrase_is_in_phrase(gold_star_location, location):
        return True
    return False

  def _passes_ignore_filters(self, universal_config: UniversalConfig) -> bool:
    return (
      self._title_is_passable(universal_config)
      and self._company_is_passable(universal_config)
      and self._location_is_passable(universal_config)
      and self._pay_is_passable(universal_config.search.salary)
    )

  def _title_is_passable(self, universal_config: UniversalConfig) -> bool:
    title = self.__title.lower().strip()
    for title_to_ignore in universal_config.bot_behavior.ignore.titles:
      if self._phrase_is_in_phrase(title_to_ignore, title):
        logging.info("Found ignore term in title: %s", title_to_ignore)
        return False
    return True

  def _company_is_passable(self, univseral_config: UniversalConfig) -> bool:
    company = self.__company.lower().strip()
    for company_to_ignore in univseral_config.bot_behavior.ignore.companies:
      if self._phrase_is_in_phrase(company_to_ignore, company):
        logging.info("Found ignore term in company: %s", company_to_ignore)
        return False
    return True

  def _location_is_passable(self, universal_config: UniversalConfig) -> bool:
    location = self.__location.lower().strip()
    for location_to_ignore in universal_config.bot_behavior.ignore.locations:
      if self._phrase_is_in_phrase(location_to_ignore, location):
        logging.info("Found ignore term in location: %s", location_to_ignore)
        return False
    return True

  def _pay_is_passable(self, expected_salary: SearchSalary) -> bool:
    if self.__max_pay and expected_salary.min > self.__max_pay:
      logging.info(
        "Job pays: %s   less than our minimum: %s.",
        expected_salary.min - self.__max_pay,
        expected_salary.min
      )
      return False
    elif self.__min_pay and expected_salary.max < self.__min_pay:
      logging.info(
        "Job pays: %s   more than our maximum: %s.",
        expected_salary.max - self.__min_pay,
        expected_salary.max
      )
      return False
    return True

  def _phrase_is_in_phrase(self, phrase_one: str | List, phrase_two: str) -> bool:
    if isinstance(phrase_one, str):
      phrase_one = phrase_one.lower().strip()
      phrase_two = phrase_two.lower().strip()
      return self._matches_pattern(phrase_one, phrase_two)
    elif isinstance(phrase_one, List):
      for item in phrase_one:
        if not self._phrase_is_in_phrase(item, phrase_two):
          return False
      return True

  def _matches_pattern(self, phrase_to_ignore: str, phrase: str) -> bool:
    pattern = rf"(?<!\w)\(?{re.escape(phrase_to_ignore)}\)?(?!\w)"
    return (
      re.search(pattern, phrase) is not None
      or phrase_to_ignore == phrase
    )
