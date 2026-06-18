class ProviderError(Exception):
    pass


class ProviderUnavailableError(ProviderError):
    pass


class ProviderParseError(ProviderError):
    pass

