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
# along with this program.  If not, see <https://www.gnu.org/licenses/>.'
import logging
from typing import cast
import asyncio
from telethon import TelegramClient, events
from telethon.tl.custom import Message
from telethon.tl.types import InputPeerChannel, InputPeerChat, InputPeerUser

from .config import link_prefix, api_id, api_hash, allowed_user, max_file_size, admin_id, session
from .paralleltransfer import ParallelTransferrer
from .string_encoder import StringCoder
from .util import get_file_name, get_media_meta

log = logging.getLogger(__name__)

client = TelegramClient(session, api_id, api_hash)
transfer = ParallelTransferrer(client)


def new_message_filter(message_text):
    return not str(message_text).startswith('/start')


@client.on(events.NewMessage(pattern='/start'))
async def handle_start(evt: events.NewMessage.Event) -> None:
    c = await evt.reply('send me an image to host it on web')
    # log.debug(c)
    await asyncio.sleep(5)
    await client.delete_messages(evt.input_chat, [c.id])
    await evt.delete()
    raise events.StopPropagation


@client.on(events.NewMessage(pattern=new_message_filter))
async def handle_message(evt: events.NewMessage.Event) -> None:
    if '*' in allowed_user and not evt.is_private:
        return
    if not (str(evt.from_id) in allowed_user and str(evt.chat_id) in allowed_user) and '*' not in allowed_user:
        log.info(f'user {evt.from_id} or {evt.chat_id} not allowed to use this bot')
        if evt.is_private:
            await evt.delete()
        return
    if str(evt.message.message).startswith('/del') and evt.reply_to_msg_id is not None:
        if bool(int(evt.is_channel)) and bool(int(evt.is_group)):
            peer = InputPeerChat(chat_id=int(evt.chat_id))
        else:
            if bool(int(evt.is_group)):
                peer = InputPeerChat(chat_id=int(evt.chat_id))
            elif bool(int(evt.is_channel)):
                peer = InputPeerChannel(channel_id=int(evt.chat_id), access_hash=0)
            else:
                peer = InputPeerUser(user_id=int(evt.chat_id), access_hash=0)
        c = cast(Message, await client.get_messages(entity=peer, ids=evt.reply_to_msg_id))
        me = await client.get_me()
        reply_msg = cast(Message, await c.get_reply_message())
        log.debug(f'msg_from={c.from_id},evt_from={evt.from_id},c is reply={c.is_reply}'
                  f',reply_msg_from={reply_msg.from_id if reply_msg is not None else 0}')
        if c.from_id == evt.from_id or (c.from_id == me.id and c.is_reply):
            if (reply_msg is not None and reply_msg.from_id == evt.from_id) or reply_msg is None:
                await client.delete_messages(evt.input_chat, [evt.reply_to_msg_id])
        await evt.delete()
    else:
        if not evt.file:
            log.info('not evt.file')
            await evt.delete()
            return
        try:
            ret = get_media_meta(evt.media)
            if ret[0] and ret[1] and ret[2] <= max_file_size:
                middle_x = StringCoder.encode(
                    f"{evt.chat_id}|{evt.id}|{1 if evt.is_group else 0}|{1 if evt.is_channel else 0}")
                log.debug(f"{evt.chat_id}|{evt.id}|{1 if evt.is_group else 0}|{1 if evt.is_channel else 0}")
                # url = public_url / str(pack_id(evt)) / get_file_name(evt)
                url = link_prefix / middle_x / get_file_name(evt)
                await evt.reply(f'[{url}]({url})')
                log.debug(f'Link to {evt.id} in {evt.chat_id}: {url}')
            else:
                if admin_id == evt.from_id and ret[0]:
                    log.debug('admin usage')
                    middle_x = StringCoder.encode(
                        f"{evt.chat_id}|{evt.id}|{1 if evt.is_group else 0}|{1 if evt.is_channel else 0}")
                    log.debug(f"{evt.chat_id}|{evt.id}|{1 if evt.is_group else 0}|{1 if evt.is_channel else 0}")
                    # url = public_url / str(pack_id(evt)) / get_file_name(evt)
                    url = link_prefix / middle_x / get_file_name(evt)
                    await evt.reply(f'[{url}]({url})')
                    log.debug(f'Link to {evt.id} in {evt.chat_id}: {url}')
                else:
                    log.info('non-admin can not serve other than image')
                    await evt.delete()
        except Exception as exp:
            await evt.reply(str(exp))
            pass
