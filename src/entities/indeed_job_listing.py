import traceback
from bs4 import BeautifulSoup
from selenium.common.exceptions import NoSuchElementException
from entities.abc_job_listing import JobListing
from entities.indeed_brief_job_listing import IndeedBriefJobListing


class IndeedJobListing(JobListing):

  def __init__(self, brief_job_listing: IndeedBriefJobListing, job_description_html: str):
    try:
      self.set_title(brief_job_listing.get_title())
      self.set_company(brief_job_listing.get_company())
      self.set_location(brief_job_listing.get_location())
      self.set_min_pay(brief_job_listing.get_min_pay())
      self.set_max_pay(brief_job_listing.get_max_pay())
      soup = BeautifulSoup(job_description_html, "html.parser")
      self.set_description(soup.get_text(separator="\n", strip=True))
    except NoSuchElementException:
      traceback.print_exc()
      input("\n\tFailed to build Job Listing.")
