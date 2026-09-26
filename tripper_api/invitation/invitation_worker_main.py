import asyncio

import httpx

from tripper_api.core.config import Settings
from tripper_api.core.database import Database
from tripper_api.invitation.invitation_provider import MailgunEmailProvider
from tripper_api.invitation.invitation_worker import InvitationOutboxWorker


async def run() -> None:
    settings = Settings()
    if (
        settings.mailgun_api_key is None
        or settings.mailgun_domain is None
        or settings.invitation_from_email is None
    ):
        raise RuntimeError("Mailgun invitation delivery settings are required")
    database = Database(settings)
    await database.start()
    async with httpx.AsyncClient(timeout=10) as client:
        provider = MailgunEmailProvider(
            client,
            api_key=settings.mailgun_api_key.get_secret_value(),
            domain=settings.mailgun_domain,
            from_email=settings.invitation_from_email,
        )
        worker = InvitationOutboxWorker(
            database,
            provider.send,
            settings.invitation_key_bytes(),
            settings.invitation_base_url,
        )
        try:
            while True:
                delivered = await worker.deliver_next()
                if not delivered:
                    await asyncio.sleep(5)
        finally:
            await database.stop()


if __name__ == "__main__":
    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        pass
