class ImproperlyConfigured(Exception):
    """Bottery is somehow improperly configured"""
    pass


class ValidationError(Exception):
    pass


class BotteryDeprecationWarning(Warning):
    pass


class PlatformError(Exception):
    def __init__(self, platform, message):
        super().__init__()
        self.platform = platform
        self.message = message

    def __str__(self):
        return '[{}] {}'.format(self.platform, self.message)
