import logging
import os
from typing import cast

from aiohttp import web
from telethon.tl.custom import Message
from telethon.tl.types import InputPeerChannel, InputPeerChat, InputPeerUser

from .config import web_api_key, show_index, link_prefix, admin_id, max_file_size
from .string_encoder import StringCoder
from .telegram_bot import client, transfer
from .util import get_file_name, get_requester_ip

log = logging.getLogger(__name__)
routes = web.RouteTableDef()


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


@routes.get(r'/favicon.ico')
async def favicon(req: web.Request) -> web.Response:
    fav_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'static', 'favicon.ico')
    return web.FileResponse(fav_path
                            , headers={'Content-Type': 'image/x-icon'}
                            )


@routes.head(r'/{id:\S+}/{name}')
async def handle_head_request(req: web.Request) -> web.Response:
    return await handle_request(req, head=True)


@routes.get(r'/{id:\S+}/{name}')
async def handle_get_request(req: web.Request) -> web.Response:
    return await handle_request(req, head=False)


@routes.get(r'/{id:\S+}')
async def get_id(req: web.Request) -> web.Response:
    return web.Response(status=404, text='<h3>404 Not Found</h3>', content_type='text/html')


@routes.get(r'/hb')
async def heart_beat(req: web.Request) -> web.Response:
    return web.Response(status=204)


@routes.delete(r'/{id:\S+}')
async def delete_image(req: web.Request) -> web.Response:
    file_id = str(req.match_info['id'])
    check_key = req.headers.get('WEB_API_KEY')
    if check_key is None or check_key != web_api_key:
        j = {'code': 401, 'msg': 'not allowed'}
        return web.json_response(j, status=401)
    peer, msg_id = extract_peer(file_id)
    if not peer or not msg_id:
        j = {'code': 404, 'msg': 'not found'}
        return web.json_response(j, status=404)
    await client.delete_messages(peer, [msg_id])
    j = {'code': 0, 'msg': 'deleted', 'file_id': file_id}
    return web.json_response(j, status=200)


@routes.post(r'/upload')
async def upload_image(req: web.Request) -> web.Response:
    check_key = req.headers.get('WEB_API_KEY')
    if check_key is None or check_key != web_api_key:
        j = {'code': 401, 'msg': 'not allowed'}
        return web.json_response(j, status=401)

    data = await req.post()
    if 'file' not in data.keys():
        j = {'code': 400, 'msg': 'no file found'}
        return web.json_response(j, status=400)

    file_size_est = req.headers.get("Content-Length")
    log.debug(f'Content-Length: {file_size_est}')
    if file_size_est > max_file_size:
        j = {'code': 400, 'msg': 'file too large'}
        return web.json_response(j, status=400)

    input_file = data['file'].file

    entity = InputPeerUser(user_id=int(admin_id), access_hash=0)
    msg = await client.send_file(entity, file=input_file.read(), force_document=True)
    file_id = StringCoder.encode(f"{admin_id}|{msg.id}|0|0")
    fn = get_file_name(msg)

    await client.edit_message(entity, msg, f'{link_prefix}/{file_id}/{fn}', file=msg.media)

    ret = {'code': 0, 'msg': 'OK', 'file_id': file_id, 'url': f'{link_prefix}/{file_id}/{fn}'}
    return web.json_response(ret)


async def handle_request(req: web.Request, head: bool = False) -> web.Response:
    file_name = req.match_info['name']
    file_id = str(req.match_info['id'])
    dl = 'dl' in req.query.keys()

    peer, msg_id = extract_peer(file_id)
    if not peer or not msg_id:
        ret = 'peer or msg_id None,file_id=%s,msg_id=%s\r\n' % (file_id, msg_id)
        log.debug(ret)
        return web.Response(status=404, text='<h3>404 Not Found</h3>', content_type='text/html')

    message = cast(Message, await client.get_messages(entity=peer, ids=int(msg_id)))
    if not message or not message.file or get_file_name(message) != file_name:
        ret = 'msg not found file_id=%s\r\n' % file_id
        log.debug(ret)
        return web.Response(status=404, text='<h3>404 Not Found</h3>', content_type='text/html')

    size = message.file.size
    offset = req.http_range.start or 0
    limit = req.http_range.stop or size
    ip = get_requester_ip(req)
    if not head:
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
