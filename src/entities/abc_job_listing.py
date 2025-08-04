import logging
from entities.abc_brief_job_listing import BriefJobListing
from models.configs.quick_settings import QuickSettings
from models.configs.universal_config import UniversalConfig


class JobListing(BriefJobListing):
  __min_yoe: int | None = None
  __max_yoe: int | None = None
  __description: str

  def get_min_yoe(self) -> int | None:
    return self.__min_yoe

  def get_max_yoe(self) -> int | None:
    return self.__max_yoe

  def get_description(self) -> str:
    return self.__description

  def set_min_yoe(self, yoe: int | None) -> None:
    self.__min_yoe = yoe

  def set_max_yoe(self, yoe: int | None) -> None:
    self.__max_yoe = yoe

  def set_description(self, description: str) -> None:
    self.__description = description

  def passes_filter_check(self, universal_config: UniversalConfig, quick_settings: QuickSettings) -> bool:
    if quick_settings.bot_behavior.platinum_star_only:
      if not self._is_gold_star_listing(universal_config):
        logging.info("Ignoring Job Listing because it is not a gold star.\n")
        return False
      else:
        if self._passes_ignore_filters(universal_config):
          logging.info("Job Listing passes filter check.")
          return True
        else:
          logging.info("Ignoring Job Listing because ignore term was found.\n")
          return False
    elif quick_settings.bot_behavior.gold_star_only:
      if self._is_gold_star_listing(universal_config):
        logging.info("Job Listing passes because its a gold star.")
        return True
      else:
        logging.info("Ignoring Job Listing because it is not a gold star.\n")
        return False
    else:
      if self._is_gold_star_listing(universal_config):
        logging.info("Job Listing passes because its a gold star.")
        return True
      else:
        if self._passes_ignore_filters(universal_config):
          logging.info("Job Listing passes because it matches no terms in ignore.")
          return True
        else:
          logging.info("Ignoring Job Listing because ignore term was found.\n")
          return False

  def _is_gold_star_listing(self, universal_config: UniversalConfig) -> bool:
    title = self.get_title().lower().strip()
    for gold_star_title in universal_config.bot_behavior.gold_star.titles:
      if self._phrase_is_in_phrase(gold_star_title, title):
        return True
    company = self.get_company().lower().strip()
    for gold_star_company in universal_config.bot_behavior.gold_star.companies:
      if self._phrase_is_in_phrase(gold_star_company, company):
        return True
    location = self.get_location().lower().strip()
    for gold_star_location in universal_config.bot_behavior.gold_star.locations:
      if self._phrase_is_in_phrase(gold_star_location, location):
        return True
    description = self.get_description().lower().strip()
    for gold_star_description in universal_config.bot_behavior.gold_star.descriptions:
      if self._phrase_is_in_phrase(gold_star_description, description):
        return True
    return False

  def _passes_ignore_filters(self, universal_config: UniversalConfig) -> bool:
    return (
      self._title_is_passable(universal_config)
      and self._company_is_passable(universal_config)
      and self._location_is_passable(universal_config)
      and self._pay_is_passable(universal_config.search.salary)
      and self._yoe_is_passable(universal_config)
      and self._description_is_passable(universal_config)
    )

  def print(self) -> None:
    logging.info(
      "\nTitle:\t\t%s\nCompany:\t%s\nLocation:\t%s\nMin Pay:\t%s\nMax Pay:\t%s\nDescription:\n\n%s\n",
      self.get_title(),
      self.get_company(),
      self.get_location(),
      self.get_min_pay(),
      self.get_max_pay(),
      self.get_description()
    )

  def to_dict(self) -> dict[str, str | float | None]:
    return {
      "title": self.get_title(),
      "company": self.get_company(),
      "location": self.get_location(),
      "min_pay": self.get_min_pay(),
      "max_pay": self.get_max_pay(),
      "description": self.get_description()
    }

  def _yoe_is_passable(self, universal_config: UniversalConfig) -> bool:
    min_yoe_desired = universal_config.bot_behavior.years_of_experience.minimum
    max_yoe_desired = universal_config.bot_behavior.years_of_experience.maximum
    if self.__min_yoe and max_yoe_desired and max_yoe_desired < self.__min_yoe:
      logging.info("Job requires too many Years of Experience.")
      self.set_ignore_category("Min YoE")
      self.set_ignore_term(str(self.__min_yoe))
      return False
    if self.__max_yoe and min_yoe_desired and min_yoe_desired < self.__max_yoe:
      logging.info("Job asks for too few Years of Experience.")
      self.set_ignore_category("Max YoE")
      self.set_ignore_term(str(self.__max_yoe))
      return False
    return True

  def _description_is_passable(self, universal_config: UniversalConfig) -> bool:
    description = self.get_description().lower().strip()
    for description_to_ignore in universal_config.bot_behavior.ignore.descriptions:
      if self._phrase_is_in_phrase(description_to_ignore, description):
        logging.info("Found ignore term in description: %s.", description_to_ignore)
        description_to_ignore = str(description_to_ignore)
        self.set_ignore_category("Description")
        self.set_ignore_term(description_to_ignore)
        return False
    return True
