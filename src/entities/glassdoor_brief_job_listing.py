from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement
from entities.abc_brief_job_listing import BriefJobListing


class GlassdoorBriefJobListing(BriefJobListing):

  def __init__(self, job_listing_li: WebElement):
    super().__init__()
    job_title_anchor_class = "JobCard_jobTitle__GLyJ1"
    job_title_anchor = job_listing_li.find_element(By.CLASS_NAME, job_title_anchor_class)
    self.set_title(job_title_anchor.text.strip())
    company_span_class = "EmployerProfile_compactEmployerName__9MGcV"
    company_span = job_listing_li.find_element(By.CLASS_NAME, company_span_class)
    self.set_company(company_span.text.strip())
    location_div_class = "JobCard_location__Ds1fM"
    location_div = job_listing_li.find_element(By.CLASS_NAME, location_div_class)
    self.set_location(location_div.text.strip())
    self.set_min_pay(None)
    self.set_max_pay(None)
    job_anchor_class = "JobCard_trackingLink__HMyun"
    job_anchor = job_listing_li.find_element(By.CLASS_NAME, job_anchor_class)
    url = job_anchor.get_attribute("href")
    assert url
    self.set_url(url)
