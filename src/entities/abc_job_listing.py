import logging
from typing import List
from entities.abc_brief_job_listing import BriefJobListing
from models.configs.universal_config import UniversalConfig


class JobListing(BriefJobListing):
  __description: str

  def get_description(self) -> str:
    return self.__description

  def set_description(self, description: str) -> None:
    self.__description = description

  def should_be_ignored(self, universal_config: UniversalConfig) -> bool:
    return (
      self._title_should_be_ignored(universal_config.bot_behavior.ignore.titles)
      or self._company_should_be_ignored(universal_config.bot_behavior.ignore.companies)
      or self._location_should_be_ignored(universal_config.bot_behavior.ignore.locations)
      or self._pay_should_be_ignored(universal_config.search.salary)
      or self.__description_should_be_ignored(universal_config.bot_behavior.ignore.descriptions)
    )

  def print(self) -> None:
    logging.info(
      "\nTitle:\t\t%s\nCompany:\t%s\nLocation:\t%s\nMin Pay:\t%s\nMax Pay:\t%s\nDescription:\n\n%s\n",
      self.get_title(),
      self.get_company(),
      self.get_location(),
      self.get_min_pay(),
      self.get_max_pay(),
      self.__description
    )

  def to_dict(self) -> dict[str, str | float | None]:
    return {
      "title": self.get_title(),
      "company": self.get_company(),
      "location": self.get_location(),
      "min_pay": self.get_min_pay(),
      "max_pay": self.get_max_pay(),
      "description": self.__description
    }

  def __description_should_be_ignored(self, descriptions_to_ignore: List[str] | List[List]) -> bool:
    description = self.__description.lower().strip()
    for description_to_ignore in descriptions_to_ignore:
      if self._phrase_is_in_phrase(description_to_ignore, description):
        logging.info("Ignoring job listing because: %s is in description.\n", description_to_ignore)
        return True
    return False
