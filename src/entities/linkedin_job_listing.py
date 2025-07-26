import traceback
from bs4 import BeautifulSoup
from selenium.webdriver.remote.webelement import WebElement
from selenium.common.exceptions import NoSuchElementException
from entities.abc_job_listing import JobListing
from entities.linkedin_brief_job_listing import LinkedinBriefJobListing


class LinkedinJobListing(JobListing):

  def __init__(self, brief_job_listing: LinkedinBriefJobListing, full_job_details_div: WebElement):
    self.set_title(brief_job_listing.get_title())
    self.set_company(brief_job_listing.get_company())
    self.set_location(brief_job_listing.get_location())
    self.set_min_pay(brief_job_listing.get_min_pay())
    self.set_max_pay(brief_job_listing.get_max_pay())
    raw_description = full_job_details_div.get_attribute("innerHTML")
    if raw_description is None:
      raw_description = ""
    soup = BeautifulSoup(raw_description, "html.parser")
    self.set_description(soup.get_text(separator="\n", strip=True))
