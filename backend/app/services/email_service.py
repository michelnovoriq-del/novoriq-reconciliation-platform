from app.config import get_settings


def send_email_verification(*, to_email: str, token: str) -> None:
    settings = get_settings()
    _ = (to_email, token, settings.frontend_url)
    # Production deployments should replace this no-op adapter with a real mailer.


def send_plan_activation_email(*, to_email: str, plan_name: str) -> None:
    _ = (to_email, plan_name)


def send_plan_downgrade_email(*, to_email: str) -> None:
    _ = to_email
