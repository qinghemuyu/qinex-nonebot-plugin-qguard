from nonebot_plugin_log_doctor.config import Config, load_config
from nonebot_plugin_log_doctor.utils.log_cleaner import compact_duplicate_lines, strip_ansi
from nonebot_plugin_log_doctor.utils.text_limit import last_lines, limit_text
from nonebot_plugin_log_doctor.utils.traceback_parser import extract_traceback


class PreprocessService:
    def __init__(self, config: Config | None = None) -> None:
        self.config = config or load_config()

    def preprocess(self, text: str) -> str:
        cleaned = strip_ansi(text.replace("\r\n", "\n").replace("\r", "\n")).strip()
        cleaned = compact_duplicate_lines(cleaned)
        traceback = extract_traceback(cleaned)
        if traceback:
            cleaned = traceback
        cleaned = last_lines(cleaned, 80)
        return limit_text(cleaned, self.config.log_doctor_max_input_chars)
