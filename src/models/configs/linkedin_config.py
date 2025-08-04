from dataclasses import dataclass


@dataclass
class LinkedinConfig:
  easy_apply_only: bool = True
  email: str = ""
  password: str = ""
