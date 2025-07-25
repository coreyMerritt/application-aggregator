import re
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement
from selenium.common.exceptions import NoSuchElementException
from entities.abc_brief_job_listing import BriefJobListing


class LinkedinBriefJobListing(BriefJobListing):

  def __init__(self, job_listing_li: WebElement):
    relative_job_title_span_xpath = "./div/a/div/div/div[2]/div[1]/div[1]/span[1]/strong"
    job_title_span = job_listing_li.find_element(By.XPATH, relative_job_title_span_xpath)
    self.set_title(job_title_span.text)
    relative_company_div_xpath = "./div/a/div/div/div[2]/div[1]/div[2]/div"
    company_div = job_listing_li.find_element(By.XPATH, relative_company_div_xpath)
    self.set_company(company_div.text)
    relative_location_div_xpath = "./div/a/div/div/div[2]/div[1]/div[3]/div"
    location_div = job_listing_li.find_element(By.XPATH, relative_location_div_xpath)
    self.set_location(location_div.text)
    try:
      relative_pay_div_xpath = "./div/a/div/div/div[2]/div[1]/div[4]/div[1]"
      pay_div = job_listing_li.find_element(By.XPATH, relative_pay_div_xpath)
      self.__handle_linkedin_pay(pay_div.text)
    except NoSuchElementException:
      self.set_min_pay(None)
      self.set_max_pay(None)

  def __handle_linkedin_pay(self, raw_pay_string: str) -> None:
    raw_pay_string = raw_pay_string.lower().strip()
    IS_GARBAGE = "/hr" not in raw_pay_string and "/yr" not in raw_pay_string
    if IS_GARBAGE:
      self.set_min_pay(None)
      self.set_max_pay(None)
      return
    IS_RANGE = "-" in raw_pay_string
    IS_ANNUAL = "/yr" in raw_pay_string
    IS_HOURLY = "/hr" in raw_pay_string
    HOURLY_TO_SALARY_CONST = 2080
    K_TO_TRUE_SALARY_CONST = 1000
    if IS_RANGE:
      values = re.findall(r"\$[0-9]+(?:\.[0-9]{1,2})?", raw_pay_string)
      if IS_HOURLY:
        hourly_values = [float(v.replace("$", "")) * HOURLY_TO_SALARY_CONST for v in values if v.strip()]
        if len(hourly_values) == 2:
          self.set_min_pay(hourly_values[0])
          self.set_max_pay(hourly_values[1])
      elif IS_ANNUAL:
        salary_values = [float(v.replace("$", "")) * K_TO_TRUE_SALARY_CONST for v in values if v.strip()]
        if len(salary_values) == 2:
          self.set_min_pay(salary_values[0])
          self.set_max_pay(salary_values[1])
    else:
      match = re.search(r"\$[0-9]+(?:\.[0-9]{1,2})?", raw_pay_string)
      if match:
        value = float(match.group().replace("$", ""))
        if IS_HOURLY:
          value *= HOURLY_TO_SALARY_CONST
        elif IS_ANNUAL:
          value *= K_TO_TRUE_SALARY_CONST
        if "up to" in raw_pay_string:
          self.set_min_pay(None)
        else:
          self.set_min_pay(value)
        self.set_max_pay(value)
