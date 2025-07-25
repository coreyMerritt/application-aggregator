import traceback
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement
from selenium.common.exceptions import NoSuchElementException
from entities.abc_brief_job_listing import BriefJobListing


class GlassdoorBriefJobListing(BriefJobListing):

  def __init__(self, job_listing_li: WebElement):
    try:
      job_title_anchor_class = "JobCard_jobTitle__GLyJ1"
      job_title_anchor = job_listing_li.find_element(By.CLASS_NAME, job_title_anchor_class)
      self.set_title(job_title_anchor.text.strip())
      company_span_class = "EmployerProfile_compactEmployerName__9MGcV"
      company_span = job_listing_li.find_element(By.CLASS_NAME, company_span_class)
      self.set_company(company_span.text.strip())
      location_div_class = "JobCard_location__Ds1fM"
      location_div = job_listing_li.find_element(By.CLASS_NAME, location_div_class)
      self.set_location(location_div.text.strip())
      # pay_div_class = 'JobCard_salaryEstimate__QpbTW'
      self.set_min_pay(None)
      self.set_max_pay(None)
    except NoSuchElementException:
      traceback.print_exc()
      input("\n\tFailed to build Brief Job Listing.")
