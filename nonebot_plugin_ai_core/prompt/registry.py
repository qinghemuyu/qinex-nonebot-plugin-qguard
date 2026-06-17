class PromptRegistry:
    def __init__(self) -> None:
        self._templates: dict[str, str] = {}

    def register(self, name: str, template: str) -> None:
        self._templates[name] = template

    def get(self, name: str) -> str:
        return self._templates[name]

    def names(self) -> list[str]:
        return sorted(self._templates)
