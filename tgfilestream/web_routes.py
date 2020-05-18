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
import logging
from collections import defaultdict
from typing import Dict, cast

from aiohttp import web
from telethon.tl.custom import Message
from telethon.tl.types import InputPeerChannel, InputPeerChat, InputPeerUser

from .config import request_limit, web_api_key, show_index
from .string_encoder import StringCoder
from .telegram import client, transfer
from .util import get_file_name, get_requester_ip

log = logging.getLogger(__name__)
routes = web.RouteTableDef()
ongoing_requests: Dict[str, int] = defaultdict(lambda: 0)


def extract_peer(encrypt_str: str):
    try:
        chat_id, msg_id, is_group, is_channel = StringCoder.decode(encrypt_str).split('|')
        if bool(int(is_channel)) and bool(int(is_group)):
            peer = InputPeerChat(chat_id=int(chat_id))
        else:
            if bool(int(is_group)):
                peer = InputPeerChat(chat_id=int(chat_id))
            elif bool(int(is_channel)):
                peer = InputPeerChannel(channel_id=int(chat_id), access_hash=0)
            else:
                peer = InputPeerUser(user_id=int(chat_id), access_hash=0)
        return peer, msg_id
    except Exception as ep:
        log.debug(ep)
        return None, None


@routes.get(r'')
async def index(req: web.Request) -> web.Response:
    if show_index:
        self_me = await client.get_me()
        index_html = f'<a target="_blank" href="https://t.me/{self_me.username}">{self_me.first_name}</a><br/>'
        return web.Response(status=200, text=index_html, content_type='text/html')
    else:
        return web.Response(status=403, text='<h3>403 Forbidden</h3>', content_type='text/html')


@routes.head(r'/{id:\S+}/{name}')
async def handle_head_request(req: web.Request) -> web.Response:
    return await handle_request(req, head=True)


@routes.get(r'/{id:\S+}/{name}')
async def handle_get_request(req: web.Request) -> web.Response:
    return await handle_request(req, head=False)


@routes.delete(r'/{id:\S+}')
async def delete_image(req: web.Request) -> web.Response:
    file_id = str(req.match_info['id'])
    check_key = req.headers.get('WEB_AP_KEY')
    if check_key is None or check_key != web_api_key:
        return web.Response(status=401, text='Not Allowed\r\n')
    peer, msg_id = extract_peer(file_id)
    if not peer or not msg_id:
        return web.Response(status=404, text='not found\r\n')
    await client.delete_messages(peer, [msg_id])
    return web.Response(status=200, text=f'msg {file_id} deleted\r\n')


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

    peer, msg_id = extract_peer(file_id)
    if not peer or not msg_id:
        ret = 'peer or msg_id None,file_id=%s,msg_id=%s\r\n' % (file_id, msg_id)
        return web.Response(status=404, text=ret)

    message = cast(Message, await client.get_messages(entity=peer, ids=int(msg_id)))
    if not message or not message.file or get_file_name(message) != file_name:
        ret = 'msg not found file_id=%s\r\n' % file_id
        return web.Response(status=404, text=ret)

    size = message.file.size
    offset = req.http_range.start or 0
    limit = req.http_range.stop or size

    if not head:
        ip = get_requester_ip(req)
        if not allow_request(ip):
            return web.Response(status=429)
        log.debug(f'Serving file in {message.id} (chat {message.chat_id}) to {ip}')
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
