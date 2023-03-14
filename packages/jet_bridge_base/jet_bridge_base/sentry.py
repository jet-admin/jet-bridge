from jet_bridge_base.exceptions.api import APIException
from jet_bridge_base.logger import logger


class SentryController(object):
    sentry_sdk = None

    def enable(self, dsn, release, tornado=False):
        try:
            import sentry_sdk

            integrations = []

            if tornado:
                try:
                    from sentry_sdk.integrations.tornado import TornadoIntegration
                    integrations.append(TornadoIntegration())
                except ImportError:
                    pass

            sentry_sdk.init(
                dsn=dsn,
                integrations=integrations,
                release=release,
                before_send=lambda event, hint: self.before_send(event, hint)
            )

            self.sentry_sdk = sentry_sdk
        except ImportError:
            self.sentry_sdk = None

    def before_send(self, event, hint):
        if 'exc_info' in hint:
            exc_type, exc_value, tb = hint['exc_info']
            if isinstance(exc_value, (APIException, KeyboardInterrupt)):
                return None
        if event.get('logger') == 'jet_bridge':
            return None
        return event

    def set_user(self, user):
        if not self.sentry_sdk:
            return

        self.sentry_sdk.set_user(user)

    def set_context(self, name, value):
        if not self.sentry_sdk:
            return

        self.sentry_sdk.set_context(name, value)

    def capture_exception(self, exc):
        logger.exception(exc)

        if not self.sentry_sdk:
            return

        self.sentry_sdk.capture_exception(exc)

    def capture_message(self, message):
        logger.error(message)

        if not self.sentry_sdk:
            return

        self.sentry_sdk.capture_message(message)


sentry_controller = SentryController()
