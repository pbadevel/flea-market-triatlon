from datetime import UTC, datetime
from urllib.parse import parse_qsl

from src.logging import get_logger

from .types import InitData, InitDataUser

log = get_logger()


class InitDataParser:
    def __init__(self, init_data_string: str) -> None:
        self.init_data_string = init_data_string

    def parse(self) -> InitData:
        try:
            init_data_dict = dict(parse_qsl(self.init_data_string))
        except Exception as exc:
            log.warning("Error while parsing qsl", error=exc)
            raise

        try:
            can_send_after = init_data_dict.get("can_send_after")
            return InitData(
                query_id=init_data_dict.get("query_id"),
                user=InitDataUser.from_url_encoded(init_data_dict, "user"),
                receiver=InitDataUser.from_url_encoded(init_data_dict, "receiver"),
                chat_type=init_data_dict.get("chat_type"),
                chat_instance=init_data_dict.get("chat_instance"),
                start_param=init_data_dict.get("start_param"),
                can_send_after=int(can_send_after) if can_send_after else None,
                auth_date=datetime.fromtimestamp(
                    int(init_data_dict["auth_date"]), tz=UTC
                ),
                hash=init_data_dict["hash"],
                signature=init_data_dict["signature"],
            )
        except Exception as exc:
            log.error("Error while validating init data", error=exc)
            raise
