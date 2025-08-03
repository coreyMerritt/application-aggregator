import time
from bs4 import BeautifulSoup
from selenium.webdriver.remote.webelement import WebElement
from entities.abc_job_listing import JobListing
from entities.linkedin_brief_job_listing import LinkedinBriefJobListing


class LinkedinJobListing(JobListing):

  def __init__(self, brief_job_listing: LinkedinBriefJobListing, job_description_content_div: WebElement):
    self.set_title(brief_job_listing.get_title())
    self.set_company(brief_job_listing.get_company())
    self.set_location(brief_job_listing.get_location())
    self.set_min_pay(brief_job_listing.get_min_pay())
    self.set_max_pay(brief_job_listing.get_max_pay())
    self.__wait_for_populated_description(job_description_content_div)
    raw_description = job_description_content_div.get_attribute("outerHTML") or ""
    soup = BeautifulSoup(raw_description, "html.parser")
    self.set_description(soup.get_text(separator="\n", strip=True))

  def __wait_for_populated_description(self, element: WebElement, timeout=5.0) -> None:
    start = time.time()
    while time.time() - start < timeout:
      text = element.text.strip()
      IS_LOADED = len(text.splitlines()) > 2 or len(text) > 100
      if IS_LOADED:
        return
      time.sleep(0.1)
