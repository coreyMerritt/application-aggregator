from dataclasses import dataclass


@dataclass
class IndeedConfig:
  apply_now_only: bool
  email: str
