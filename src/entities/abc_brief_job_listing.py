from abc import ABC
import logging
import re
from typing import List
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

  def should_be_ignored(self, universal_config: UniversalConfig) -> bool:
    return (
      self._title_should_be_ignored(universal_config.bot_behavior.ignore.titles)
      or self._company_should_be_ignored(universal_config.bot_behavior.ignore.companies)
      or self._location_should_be_ignored(universal_config.bot_behavior.ignore.locations)
      or self._pay_should_be_ignored(universal_config.search.salary)
    )

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

  def _title_should_be_ignored(self, titles_to_ignore: List[str] | List[List]) -> bool:
    title = self.__title.lower().strip()
    for title_to_ignore in titles_to_ignore:
      if self._phrase_is_in_phrase(title_to_ignore, title):
        logging.info("Ignoring job listing because: %s is in title.\n", title_to_ignore)
        return True
    return False

  def _company_should_be_ignored(self, companies_to_ignore: List[str] | List[List]) -> bool:
    company = self.__company.lower().strip()
    for company_to_ignore in companies_to_ignore:
      if self._phrase_is_in_phrase(company_to_ignore, company):
        logging.info("Ignoring job listing because: %s is in company.\n", company_to_ignore)
        return True
    return False

  def _location_should_be_ignored(self, locations_to_ignore: List[str] | List[List]) -> bool:
    location = self.__location.lower().strip()
    for location_to_ignore in locations_to_ignore:
      if self._phrase_is_in_phrase(location_to_ignore, location):
        logging.info("Ignoring job listing because: %s is in location.\n", location_to_ignore)
        return True
    return False

  def _pay_should_be_ignored(self, expected_salary: SearchSalary) -> bool:
    if self.__max_pay and expected_salary.min > self.__max_pay:
      logging.info(
        "Ignoring job listing because: Job pays %s less than our minimum \"%s\"\n",
        expected_salary.min - self.__max_pay,
        expected_salary.min
      )
      return True
    elif self.__min_pay and expected_salary.max < self.__min_pay:
      logging.info(
        "Ignoring job listing because: Job pays %s more than our maximum \"%s\"\n",
        expected_salary.max - self.__min_pay,
        expected_salary.max
      )
      return True
    return False

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
