import asyncio

from procrastinate.contrib.django import app


def _run_worker_once_sync() -> None:
    with app.replace_connector(app.connector.get_worker_connector()):  # type: ignore
        app.run_worker(wait=False, install_signal_handlers=False, listen_notify=False)


async def _run_worker_once_async() -> None:
    with app.replace_connector(app.connector.get_worker_connector()):  # type: ignore
        async with app.open_async():
            await app.run_worker_async(
                wait=False, install_signal_handlers=False, listen_notify=False
            )


def run_worker_once() -> None:
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop is None:
        _run_worker_once_sync()
    else:
        loop.run_until_complete(_run_worker_once_async())
