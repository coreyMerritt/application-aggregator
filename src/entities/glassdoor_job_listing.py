import logging
import time
import traceback
from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement
from selenium.common.exceptions import NoSuchElementException
from entities.abc_job_listing import JobListing
from entities.glassdoor_brief_job_listing import GlassdoorBriefJobListing


class GlassdoorJobListing(JobListing):

  def __init__(self, brief_job_listing: GlassdoorBriefJobListing, job_info_div: WebElement):
    self.set_title(brief_job_listing.get_title())
    self.set_company(brief_job_listing.get_company())
    self.set_location(brief_job_listing.get_location())
    self.set_min_pay(brief_job_listing.get_min_pay())
    self.set_max_pay(brief_job_listing.get_max_pay())
    description_div_selector = ".JobDetails_jobDescription__uW_fK.JobDetails_blurDescription__vN7nh"
    while True:
      try:
        description_div = job_info_div.find_element(By.CSS_SELECTOR, description_div_selector)
        break
      except NoSuchElementException:
        logging.debug("Waiting for job description div to load...")
        time.sleep(0.1)
    raw_description = description_div.get_attribute("innerHTML")
    if raw_description is None:
      raw_description = ""
    soup = BeautifulSoup(raw_description, "html.parser")
    self.set_description(soup.get_text(separator="\n", strip=True))
