import re

RULE_LIST = [
    {
        "pattern": r"^/[a-f0-9\-]+/.*$",
        "group": ("ADMIN", "OWNER"),
        "read": True,
        "write": True,
    },
    {
        "pattern": r"^/[a-f0-9\-]+/.*/.*$",
        "group": "ADMIN",
        "read": True,
        "write": True,
    },
    {
        "pattern": r"^/[a-f0-9\-]+/transport/.*$",
        "group": "CLIENT",
        "read": True,
        "write": False,
    },
]

for rule in RULE_LIST:
    rule["compiled_pattern"] = re.compile(rule["pattern"])


def is_readable(path, user_group):
    path = "/" + path.strip("/") + "/"
    for rule in RULE_LIST:
        if user_group in rule["group"] and rule["compiled_pattern"].match(path):
            return rule["read"]
    return False


def is_writable(path, user_group):
    path = "/" + path.strip("/") + "/"
    for rule in RULE_LIST:
        if user_group in rule["group"] and rule["compiled_pattern"].match(path):
            return rule["write"]
    return False
