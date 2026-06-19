from nonebot_plugin_support_bot.services.schemas import SupportIntent


def trim_reply(text: str, limit: int) -> str:
    cleaned = text.strip()
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[: max(0, limit - 12)].rstrip() + "\n..."


def format_followup(intent: SupportIntent) -> str:
    fields = (intent.missing_fields or ["你用的是哪个功能", "卡在哪一步"])[:2]
    template = _diagnostic_template(intent.issue_type, fields)
    if template:
        return template
    prefix = "喵，这个信息还不够，我先不乱猜。"
    if len(fields) == 1:
        return f"{prefix}先告诉我{fields[0]}，我再给你下一步。"
    return f"{prefix}简单说下：{fields[0]}；还有{fields[1]}。"


def _diagnostic_template(issue_type: str, fields: list[str]) -> str:
    if issue_type == "mapping_not_working":
        return (
            "喵，我先按“映射输出没生效”排查，不急着判硬件坏。\n"
            f"回我两个点就行：{_field(fields, 0, '你用的是 S3、免硬件 ADB 还是 P4')}；"
            f"{_field(fields, 1, '是全部没反应，还是只有部分按键/鼠标/压枪没反应')}。"
        )
    if issue_type == "performance_problem":
        return (
            "喵，我先按“卡顿/不跟手”排查，别先乱改一堆设置。\n"
            f"回我两个点：{_field(fields, 0, '卡的是滑屏、投屏画面，还是按键响应')}；"
            f"{_field(fields, 1, '你用的是 S3、免硬件 ADB 还是 P4')}。"
        )
    if issue_type == "launch_failed":
        return (
            "喵，我先按“启动/配置面板打不开”排查。\n"
            f"先说下：{_field(fields, 0, '是打不开、空白、闪退，还是有报错提示')}；"
            f"{_field(fields, 1, '打不开的是上位机、配置面板还是手机 APP')}。"
        )
    if issue_type == "screenhub_usage":
        return (
            "喵，我先按“投屏/手机 APP”排查。\n"
            f"告诉我：{_field(fields, 0, '是电脑投屏、手机 APP，还是控制模式')}；"
            f"{_field(fields, 1, '现象是画面卡、黑屏、点不准，还是连不上')}。"
        )
    if issue_type == "p4_usage":
        return (
            "喵，我先按 P4 单机版排查。\n"
            f"回我：{_field(fields, 0, 'P4 现在卡在哪个页面')}；"
            f"{_field(fields, 1, '手机上有没有出现触点')}。"
        )
    return ""


def _field(fields: list[str], index: int, fallback: str) -> str:
    if index < len(fields) and fields[index]:
        return fields[index]
    return fallback
