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

from telethon import TelegramClient, events

from .paralleltransfer import ParallelTransferrer
from .config import session_name, api_id, api_hash, public_url, allowed_user, max_file_size
from .util import pack_id, get_file_name

log = logging.getLogger(__name__)

client = TelegramClient(session_name, api_id, api_hash)
transfer = ParallelTransferrer(client)


def get_media_meta(media):
    try:
        if hasattr(media, 'photo'):
            log.debug('media.photo true')
            for a in media.photo.sizes:
                log.debug(a)
                if a.type == 'x':
                    return True, True, a.size
        if hasattr(media, 'document'):
            log.debug('media.document true')
            log.info(media.document.mime_type)
            return True, str(media.document.mime_type).split("/")[0] == "image", media.document.size
        return False, False, 0
    except Exception as ep:
        log.error(ep)
        return False, False, False, str(ep)


@client.on(events.NewMessage)
async def handle_message(evt: events.NewMessage.Event) -> None:
    if str(evt.from_id) not in allowed_user:
        log.info(f"user {evt.from_id} not allowed to use this bot")
        return
    try:
        ret = get_media_meta(evt.media)
        if not (ret[0] and ret[1] and ret[2] <= max_file_size):
            log.info(f"{ret}")
            return
    except Exception as exp:
        pass
    if not evt.is_private or not evt.file:
        return
    url = public_url / str(pack_id(evt)) / get_file_name(evt)
    await evt.reply(f"Link to download file: [{url}]({url})")
    log.info(f"Replied with link for {evt.id} to {evt.from_id} in {evt.chat_id}")
    log.debug(f"Link to {evt.id} in {evt.chat_id}: {url}")
