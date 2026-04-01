from enum import StrEnum


class Scope(StrEnum):
    web_default = "web_default"  # Web default scope. For users logged in on the web.
    web_admin = "web_admin"
