from bs4 import BeautifulSoup
from entities.abc_job_listing import JobListing
from entities.indeed_brief_job_listing import IndeedBriefJobListing
from services.misc.yoe_parser import YoeParser


class IndeedJobListing(JobListing):

  def __init__(self, brief_job_listing: IndeedBriefJobListing, job_description_html: str):
    self.set_title(brief_job_listing.get_title())
    self.set_company(brief_job_listing.get_company())
    self.set_location(brief_job_listing.get_location())
    self.set_min_pay(brief_job_listing.get_min_pay())
    self.set_max_pay(brief_job_listing.get_max_pay())
    soup = BeautifulSoup(job_description_html, "html.parser")
    description = soup.get_text(separator="\n", strip=True)
    self.set_description(description)
    yoe_parser = YoeParser()
    min_yoe, max_yoe = yoe_parser.parse(description)
    self.set_min_yoe(min_yoe)
    self.set_max_yoe(max_yoe)
