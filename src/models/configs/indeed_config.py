from dataclasses import dataclass


@dataclass
class IndeedConfig:
  apply_now_only: bool = True
  email: str = ""
