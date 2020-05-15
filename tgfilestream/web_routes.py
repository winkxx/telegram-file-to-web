# tgfilestream - A Telegram bot that can stream Telegram files to users over HTTP.
# Copyright (C) 2019 Tulir Asokan
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
from typing import Dict, cast
from collections import defaultdict
import logging

from telethon.tl.custom import Message
from aiohttp import web

from telethon.tl.types import TypeInputPeer, InputPeerChannel, InputPeerChat, InputPeerUser

from .util import get_file_name, get_requester_ip
from .string_encoder import StringCoder
from .config import request_limit
from .telegram import client, transfer

log = logging.getLogger(__name__)
routes = web.RouteTableDef()
ongoing_requests: Dict[str, int] = defaultdict(lambda: 0)


@routes.head(r'/{id:\S+}/{name}')
async def handle_head_request(req: web.Request) -> web.Response:
    return await handle_request(req, head=True)


@routes.get(r'/{id:\S+}/{name}')
async def handle_get_request(req: web.Request) -> web.Response:
    return await handle_request(req, head=False)


def allow_request(ip: str) -> None:
    return ongoing_requests[ip] < request_limit


def increment_counter(ip: str) -> None:
    ongoing_requests[ip] += 1


def decrement_counter(ip: str) -> None:
    ongoing_requests[ip] -= 1


async def handle_request(req: web.Request, head: bool = False) -> web.Response:
    file_name = req.match_info['name']
    file_id = str(req.match_info['id'])
    dl = 'dl' in req.query.keys()

    chat_id, msg_id, is_group, is_channel = StringCoder.decode(file_id)
    if is_channel:
        peer = InputPeerChannel(channel_id=chat_id, access_hash=0)
    elif is_group:
        peer = InputPeerChat(chat_id=chat_id)
    else:
        peer = InputPeerUser(user_id=chat_id, access_hash=0)

    if not peer or not msg_id:
        ret = ' peer or msg_id None,file_id=%s,msg_id=%s' % (file_id, msg_id)
        return web.Response(status=404, text=ret)

    message = cast(Message, await client.get_messages(entity=peer, ids=msg_id))
    if not message or not message.file or get_file_name(message) != file_name:
        ret = 'msg not found file_id=%s' % file_id
        return web.Response(status=404, text=ret)

    size = message.file.size
    offset = req.http_range.start or 0
    limit = req.http_range.stop or size

    if not head:
        ip = get_requester_ip(req)
        if not allow_request(ip):
            return web.Response(status=429)
        log.info(f'Serving file in {message.id} (chat {message.chat_id}) to {ip}')
        body = transfer.download(message.media, file_size=size, offset=offset, limit=limit)
    else:
        body = None

    h = {
        'Content-Type': message.file.mime_type,
        'Content-Range': f'bytes {offset}-{size}/{size}',
        'Content-Length': str(limit - offset),
        'Access-Control-Allow-Origin': '*',
        'content-security-policy': 'script-src "self" "unsafe-inline" "unsafe-eval"',
        # 'Content-Disposition': f'attachment; filename='{file_name}'',
        'Accept-Ranges': 'bytes',
    }
    if dl:
        h['Content-Disposition'] = f'attachment; filename="{file_name}"'

    return web.Response(status=206 if offset else 200,
                        body=body,
                        headers=h)
