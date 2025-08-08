import time
from bs4 import BeautifulSoup
from selenium.webdriver.remote.webelement import WebElement
from entities.abc_job_listing import JobListing
from entities.linkedin_brief_job_listing import LinkedinBriefJobListing
from services.misc.yoe_parser import YoeParser
from services.misc.language_parser import LanguageParser


class LinkedinJobListing(JobListing):

  def __init__(
    self,
    language_parser: LanguageParser,
    brief_job_listing: LinkedinBriefJobListing,
    job_description_content_div: WebElement | None = None,
    url: str | None = None
  ):
    super().__init__(language_parser)
    self.set_title(brief_job_listing.get_title())
    self.set_company(brief_job_listing.get_company())
    self.set_location(brief_job_listing.get_location())
    self.set_min_pay(brief_job_listing.get_min_pay())
    self.set_max_pay(brief_job_listing.get_max_pay())
    self.set_ignore_category(brief_job_listing.get_ignore_category())
    self.set_ignore_term(brief_job_listing.get_ignore_term())
    if job_description_content_div:
      self.__wait_for_populated_description(job_description_content_div)
      raw_description = job_description_content_div.get_attribute("outerHTML") or ""
      soup = BeautifulSoup(raw_description, "html.parser")
      description = soup.get_text(separator="\n", strip=True)
      self.set_description(description)
      yoe_parser = YoeParser()
      min_yoe, max_yoe = yoe_parser.parse(description)
      self.set_min_yoe(min_yoe)
      self.set_max_yoe(max_yoe)
    else:
      self.set_description(None)
    if url:
      self.set_url(url)
    else:
      self.set_url(brief_job_listing.get_url())

  def __wait_for_populated_description(self, element: WebElement, timeout=5.0) -> None:
    start = time.time()
    while time.time() - start < timeout:
      text = element.text.strip()
      IS_LOADED = len(text.splitlines()) > 2 or len(text) > 100
      if IS_LOADED:
        return
      time.sleep(0.1)
