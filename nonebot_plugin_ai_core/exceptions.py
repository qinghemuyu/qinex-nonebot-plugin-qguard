class AICoreError(RuntimeError):
    pass


class AIClientError(AICoreError):
    pass


class AIRateLimitExceeded(AICoreError):
    pass


class AIResponseParseError(AICoreError):
    pass
