from dataclasses import dataclass


@dataclass
class LinkedinConfig:
  easy_apply_only: bool
  email: str
  password: str
