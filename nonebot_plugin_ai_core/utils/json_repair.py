import json
import re
from typing import TypeVar

from pydantic import BaseModel, ValidationError

from nonebot_plugin_ai_core.exceptions import AIResponseParseError

T = TypeVar("T", bound=BaseModel)


def extract_json_object(text: str) -> dict:
    cleaned = _strip_code_fence(text.strip())
    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError:
        data = json.loads(_find_first_json_object(cleaned))
    if not isinstance(data, dict):
        raise AIResponseParseError("AI 返回的 JSON 不是对象。")
    return data


def parse_model_from_text(text: str, schema_model: type[T]) -> T:
    try:
        data = extract_json_object(text)
        return schema_model.model_validate(data)
    except (json.JSONDecodeError, ValidationError, AIResponseParseError) as exc:
        raise AIResponseParseError(str(exc)) from exc


def _strip_code_fence(text: str) -> str:
    match = re.fullmatch(r"```(?:json)?\s*(.*?)\s*```", text, flags=re.DOTALL | re.IGNORECASE)
    return match.group(1) if match else text


def _find_first_json_object(text: str) -> str:
    start = text.find("{")
    if start < 0:
        raise AIResponseParseError("AI 响应中没有 JSON 对象。")
    depth = 0
    in_string = False
    escaped = False
    for index in range(start, len(text)):
        char = text[index]
        if escaped:
            escaped = False
            continue
        if char == "\\":
            escaped = True
            continue
        if char == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return text[start : index + 1]
    raise AIResponseParseError("AI 响应中的 JSON 对象不完整。")
