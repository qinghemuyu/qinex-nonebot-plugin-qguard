from dataclasses import dataclass

from nonebot_plugin_log_doctor.services.schemas import DiagnosisResult


@dataclass(frozen=True, slots=True)
class BuiltinRule:
    name: str
    category: str
    patterns: tuple[str, ...]
    title: str
    root_cause: str
    fix_steps: tuple[str, ...]
    severity: str = "medium"
    confidence: float = 0.95
    evidence_keywords: tuple[str, ...] = ()
    priority: int = 100

    def to_result(self, evidence: list[str]) -> DiagnosisResult:
        return DiagnosisResult(
            title=self.title,
            category=self.category,
            severity=self.severity,
            confidence=self.confidence,
            root_cause=self.root_cause,
            evidence=evidence,
            fix_steps=list(self.fix_steps),
            related_keywords=[self.name, *self.evidence_keywords],
            need_more_info=False,
        )


BUILTIN_RULES: tuple[BuiltinRule, ...] = (
    BuiltinRule(
        name="sqlite_unable_to_open_database_file",
        category="database_path_or_permission",
        patterns=("sqlite3.operationalerror: unable to open database file", "unable to open database file"),
        title="SQLite 数据库文件无法打开",
        root_cause="通常是数据库目录不存在、数据库路径配置错误，或运行用户没有写权限。",
        fix_steps=(
            "检查 .env 中数据库 URL 是否正确。",
            "如果使用相对路径，确认当前工作目录是否符合预期。",
            "创建数据库所在目录，例如 mkdir -p ./data。",
            "检查运行用户对数据库目录是否有读写权限。",
            "生产环境建议改成绝对路径，减少工作目录差异。",
        ),
        evidence_keywords=("sqlite", "sqlalchemy", "aiosqlite"),
        priority=10,
    ),
    BuiltinRule(
        name="module_not_found",
        category="missing_dependency",
        patterns=("modulenotfounderror: no module named", "importerror: cannot import name"),
        title="Python 依赖或模块缺失",
        root_cause="当前 Python 环境中缺少依赖，或者包名、模块名、虚拟环境不一致。",
        fix_steps=(
            "确认正在使用 NoneBot 项目的虚拟环境。",
            "根据报错里的模块名安装依赖，例如 python -m pip install 包名。",
            "如果是本地插件模块，检查插件目录是否在 NoneBot 的 plugin_dirs 内。",
            "重启 NoneBot 后再次观察导入日志。",
        ),
        evidence_keywords=("ModuleNotFoundError", "ImportError"),
        priority=20,
    ),
    BuiltinRule(
        name="permission_error",
        category="filesystem_permission",
        patterns=("permissionerror:", "permission denied", "errno 13"),
        title="文件或目录权限不足",
        root_cause="运行机器人进程的用户没有目标文件或目录的读写权限。",
        fix_steps=(
            "确认机器人实际运行用户，例如 whoami 或 systemctl status。",
            "检查目标路径权限：ls -ld 路径。",
            "把数据目录授权给运行用户，避免长期用 root 混跑。",
            "如果在 Docker 内运行，检查 volume 挂载权限。",
        ),
        evidence_keywords=("PermissionError", "permission denied"),
        priority=30,
    ),
    BuiltinRule(
        name="file_not_found",
        category="missing_file_or_path",
        patterns=("filenotfounderror:", "no such file or directory", "errno 2"),
        title="文件或路径不存在",
        root_cause="程序访问的文件路径不存在，或者相对路径的当前工作目录与预期不一致。",
        fix_steps=(
            "确认报错中的完整路径是否存在。",
            "使用 pwd 查看当前工作目录。",
            "必要时创建目录或复制缺失文件。",
            "配置文件里尽量使用绝对路径。",
        ),
        evidence_keywords=("FileNotFoundError", "No such file"),
        priority=40,
    ),
    BuiltinRule(
        name="config_parse_error",
        category="config_syntax",
        patterns=("jsondecodeerror", "yaml", "tomldecodeerror", "tomlkit.exceptions", "expected", "parse error"),
        title="配置文件格式解析失败",
        root_cause="JSON/YAML/TOML 配置里可能存在缩进、引号、逗号、布尔值或换行格式错误。",
        fix_steps=(
            "定位报错行号附近的配置内容。",
            "检查引号、逗号、冒号、缩进是否正确。",
            "TOML 中字符串要加引号，布尔值使用 true/false。",
            "修改后重启服务验证配置是否能正常加载。",
        ),
        severity="low",
        confidence=0.88,
        evidence_keywords=("JSON", "YAML", "TOML"),
        priority=50,
    ),
    BuiltinRule(
        name="onebot_websocket_failed",
        category="onebot_connection",
        patterns=("websocket error", "connection refused", "connectionclosed", "/onebot/v11/ws"),
        title="OneBot WebSocket 连接异常",
        root_cause="OneBot 实现端与 NoneBot 的 WebSocket 地址、端口、路径或 access token 可能不一致。",
        fix_steps=(
            "确认 NoneBot 正在监听正确 HOST/PORT。",
            "确认协议端连接地址类似 ws://127.0.0.1:8080/onebot/v11/ws。",
            "检查 access token 是否两边一致。",
            "如果跨机器连接，检查防火墙、安全组和反向代理。",
        ),
        evidence_keywords=("WebSocket", "OneBot"),
        priority=60,
    ),
    BuiltinRule(
        name="nonebot_plugin_import_failed",
        category="nonebot_plugin_loading",
        patterns=("failed to import", "failed to load plugin", "is not loaded as a plugin", "nonebot.plugin"),
        title="NoneBot 插件加载失败",
        root_cause="插件可能被提前 import、加载路径不正确、依赖缺失，或本地插件目录解析失败。",
        fix_steps=(
            "不要在正式启动前手动 import 要作为插件加载的模块。",
            "确认 plugin_dirs 指向项目内真实目录，不要软链接到项目外路径。",
            "检查完整 Traceback 顶部的第一个业务错误。",
            "确认插件依赖已经安装到当前虚拟环境。",
        ),
        evidence_keywords=("NoneBot", "plugin"),
        priority=70,
    ),
)
