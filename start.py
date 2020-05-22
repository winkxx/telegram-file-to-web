import asyncio
import logging
import sys

import requests
from aiohttp import web
from apscheduler.schedulers.background import BackgroundScheduler
from telethon import functions

from app.util import sizeof_fmt
from app.config import host, port, link_prefix, allowed_user, bot_token,\
    debug, show_index, keep_awake, keep_awake_url, max_file_size
from app.telegram_bot import client, transfer
from app.web import routes

logging.basicConfig(level=logging.DEBUG if debug else logging.INFO)

log = logging.getLogger('telegram-file-to-web')
logging.getLogger('telethon').setLevel(50)
logging.getLogger('apscheduler').setLevel(50)
logging.getLogger('urllib3').setLevel(50)

global_app = web.Application(client_max_size=max_file_size+64*1024)
global_app.add_routes(routes)

runner = web.AppRunner(global_app)
loop = asyncio.get_event_loop()

scheduler = BackgroundScheduler()

log.info('Initialization complete')
log.debug(f'Listening at http://{host}:{port}')
log.info(f'Public URL prefix is {link_prefix}')
log.info(f'allowed user ids {allowed_user}')
log.info(f'Debug={debug},show_index={show_index}')
log.info(f'max file size is {sizeof_fmt(max_file_size)}')
log.debug(f'BotToken={bot_token}')


async def start() -> None:
    await client.start(bot_token=bot_token)
    config = await client(functions.help.GetConfigRequest())
    for option in config.dc_options:
        if option.ip_address == client.session.server_address:
            client.session.set_dc(option.id, option.ip_address, option.port)
            client.session.save()
            log.debug(f"Fixed DC ID in session from {client.session.dc_id} to {option.id}")
            break
    transfer.post_init()
    await runner.setup()
    await web.TCPSite(runner, host, port).start()


async def stop() -> None:
    if keep_awake:
        scheduler.shutdown()
    await runner.cleanup()
    await client.disconnect()


def keep_wake():
    resp = requests.get(keep_awake_url)
    log.debug(f'keep_wake,get {str(keep_awake_url)},result={resp.status_code},{resp.content}')


try:
    if keep_awake:
        scheduler.add_job(keep_wake, 'interval', seconds=120)
        scheduler.start()
    loop.run_until_complete(start())
    loop.run_forever()
except Exception as ep:
    print(str(ep))
    if keep_awake:
        scheduler.shutdown()
    sys.exit(2)
