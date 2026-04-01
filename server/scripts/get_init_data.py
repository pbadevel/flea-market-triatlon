import json
from urllib.parse import urlencode

from src.kit.utils import utc_now
from src.logging import get_logger

log = get_logger()


def main():
    id = 5316965624
    first_name = "Brave"
    username = "bravecode"

    init_data = {
        "auth_date": int(utc_now().timestamp()),
        "hash": "some-hash",
        "signature": "some-signature",
        "user": json.dumps({"id": id, "first_name": first_name, "username": username}),
    }

    init_data_string = urlencode(init_data)

    log.debug(f"Init data string: {init_data_string}")


if __name__ == "__main__":
    main()
