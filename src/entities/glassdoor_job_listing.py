import logging
import time
from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement
from selenium.common.exceptions import NoSuchElementException
from entities.abc_job_listing import JobListing
from entities.glassdoor_brief_job_listing import GlassdoorBriefJobListing
from services.misc.yoe_parser import YoeParser


class GlassdoorJobListing(JobListing):

  def __init__(
    self,
    brief_job_listing: GlassdoorBriefJobListing,
    job_info_div: WebElement | None = None,
    url: str | None = None
  ):
    self.set_title(brief_job_listing.get_title())
    self.set_company(brief_job_listing.get_company())
    self.set_location(brief_job_listing.get_location())
    self.set_min_pay(brief_job_listing.get_min_pay())
    self.set_max_pay(brief_job_listing.get_max_pay())
    self.set_ignore_category(brief_job_listing.get_ignore_category())
    self.set_ignore_term(brief_job_listing.get_ignore_term())
    description_div_selector = ".JobDetails_jobDescription__uW_fK.JobDetails_blurDescription__vN7nh"
    timeout = 3
    timed_out = True
    start_time = time.time()
    if job_info_div:
      while time.time() - start_time < timeout:
        try:
          description_div = job_info_div.find_element(By.CSS_SELECTOR, description_div_selector)
          timed_out = False
          break
        except NoSuchElementException:
          logging.debug("Waiting for job description div to load...")
          time.sleep(0.1)
      if timed_out:
        raise TimeoutError("Timed out waiting for job description div to load.")
      raw_description = description_div.get_attribute("innerHTML")
      if raw_description is None:
        raw_description = ""
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
