from dataclasses import dataclass, field


@dataclass
class BotBehavior:
  ignore_jobs_that_demand_cover_letters: bool = False
  pause_after_each_platform: bool = False
  remove_tabs_after_each_platform: bool = True
  default_page_load_timeout: int = 30
  pause_every_x_jobs: int = 50
  apply_order: list = field(default_factory=list)

@dataclass
class QuickSettings:
  bot_behavior: BotBehavior = field(default_factory=BotBehavior)
