from django.conf import settings
import resend


resend.api_key = settings.RESEND_API_KEY


def send_email_task(
    subject: str,
    message: str,
    recipient_list: list[str],
) -> None:
    """
    :param subject: Subject of the email.
    :param message: Body of the email.
    :param recipient_list: A list of recipient email addresses.
    """

    if not settings.ENABLE_EMAILS:
        return None

    if settings.DEBUG:
        # override the recipient list on local development
        recipient_list = ["delivered@resend.dev"]

    params: resend.Emails.SendParams = {
        "from": settings.DEFAULT_FROM_EMAIL,
        "to": recipient_list,
        "subject": subject,
        "html": message,
    }

    resend.Emails.send(params)

    return None
