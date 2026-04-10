from django.core.mail.backends.smtp import EmailBackend


class DevSmtpBackend(EmailBackend):
    """SMTP backend for development that gives a clear error when the local
    test SMTP server is not running."""

    def open(self):
        try:
            return super().open()
        except ConnectionRefusedError:
            raise ConnectionRefusedError(
                "Could not connect to the SMTP server. "
                "Start your local test SMTP server, e.g.:\n\n"
                "    python -m smtpd -n -c DebuggingServer localhost:25\n\n"
                "or with aiosmtpd (pip install aiosmtpd):\n\n"
                "    python -m aiosmtpd -n -l localhost:1025"
            ) from None
