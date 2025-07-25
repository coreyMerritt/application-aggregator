import traceback
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement
from selenium.common.exceptions import NoSuchElementException
from entities.abc_brief_job_listing import BriefJobListing


class IndeedBriefJobListing(BriefJobListing):

  def __init__(self, job_listing_li: WebElement):
    try:
      relative_title_span_xpath = "./div/div/div/div/div/div/table/tbody/tr/td/div[1]/h2/a/span"
      relative_title_span = job_listing_li.find_element(By.XPATH, relative_title_span_xpath)
      self.set_title(relative_title_span.text.strip())
      relative_company_span_xpath = "./div/div/div/div/div/div/table/tbody/tr/td/div[2]/div/div[1]/span"
      relative_company_span = job_listing_li.find_element(By.XPATH, relative_company_span_xpath)
      self.set_company(relative_company_span.text.strip())
      relative_location_div_xpath = "./div/div/div/div/div/div/table/tbody/tr/td/div[2]/div/div[2]"
      relative_location_div = job_listing_li.find_element(By.XPATH, relative_location_div_xpath)
      self.set_location(relative_location_div.text.strip())
      # relative_pay_h2_xpath = "./div/div/div/div/div/div/table/tbody/tr/td/div[3]/div/h2"
      # try:
      #   relative_pay_h2 = job_listing_li.find_element(By.XPATH, relative_pay_h2_xpath)
      # except NoSuchElementException:
      #   self.set_pay(None)
      #   return
      # pay = relative_pay_h2.text
      # if pay:
      #   self.set_pay(pay.strip())
      # else:
      #   self.set_pay(None)
      self.set_min_pay(None)
      self.set_max_pay(None)
    except NoSuchElementException:
      traceback.print_exc()
      input("\n\tFailed to build Brief Job Listing.")
