from dataclasses import dataclass, field


@dataclass
class BotBehavior:
  pause_after_each_platform: bool = False
  remove_tabs_after_each_platform: bool = True
  default_page_load_timeout: int = 30
  pause_every_x_jobs: int = 50
  platform_order: list = field(default_factory=list)

@dataclass
class QuickSettings:
  bot_behavior: BotBehavior = field(default_factory=BotBehavior)
