import re
from dataclasses import dataclass

from Pricelist.settings import ADMIN_GROUPS, CLIENT_GROUPS


@dataclass
class Rule:
    """file permissions"""

    pattern: re.Pattern
    group: tuple
    read: bool
    write: bool


RULE_LIST = [
    Rule(re.compile(r".*"), ADMIN_GROUPS + CLIENT_GROUPS, True, True),
    Rule(re.compile(r"^/[a-f0-9\-]+/.*$"), ("ADMIN", "OWNER"), True, True),
]


def is_readable(path, user_group):
    for rule in RULE_LIST:
        if user_group in rule.group and rule.pattern.match(
            path
        ):  # it has match() member xD
            return rule.read
    return False


def is_writable(path, user_group):
    for rule in RULE_LIST:
        if user_group in rule.group and rule.pattern.match(path):
            return rule.write
    return False
