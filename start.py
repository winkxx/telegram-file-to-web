from aiohttp import web
from app.web import routes
import asyncio
import sys
import logging
# global_app.add_domain('admin.127.0.0.1.xip.io', admin_controller.web_app)

global_app = web.Application()
global_app.add_routes(routes)

runner = web.AppRunner(global_app)
loop = asyncio.get_event_loop()


async def start():
    await runner.setup()
    await web.TCPSite(runner,'127.0.0.1', 19888).start()


try:
    loop.run_until_complete(start())
    loop.run_forever()
except Exception:
    sys.exit(2)
