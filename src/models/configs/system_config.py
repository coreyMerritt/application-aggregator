from dataclasses import dataclass, field


@dataclass
class DatabaseConfig:
  engine: str = ""
  username: str = ""
  password: str = ""
  host: str = ""
  port: int = 3306
  name: str = ""

@dataclass
class BrowserConfig:
  path: str = ""

@dataclass
class SystemConfig:
  browser: BrowserConfig = field(default_factory=BrowserConfig)
  database: DatabaseConfig = field(default_factory=DatabaseConfig)
