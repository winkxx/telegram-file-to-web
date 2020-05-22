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
from typing import Union

from aiohttp import web
from telethon import events
from telethon.tl.custom import Message

log = logging.getLogger('telegram-file-to-web')

def get_file_name(message: Union[Message, events.NewMessage.Event]) -> str:
    if message.file.name:
        return message.file.name
    ext = message.file.ext or ''
    return f'{message.date.strftime("%Y-%m-%d_%H_%M_%S")}{ext}'


def get_requester_ip(req: web.Request) -> str:
    peername = req.transport.get_extra_info('peername')
    if peername is not None:
        return peername[0]


def get_media_meta(media) -> (bool, bool, int, str):
    try:
        if hasattr(media, 'photo'):
            for a in media.photo.sizes:
                if a.type == 'm':
                    return True, True, int(a.size), ''
        if hasattr(media, 'document'):
            return True, str(media.document.mime_type).split("/")[0] == 'image', int(media.document.size), ''
        return False, False, 0, ''
    except Exception as ep:
        log.debug(str(ep))
        return False, False, 0, str(ep)


def sizeof_fmt(num, suffix='B'):
    for unit in ['', 'Ki', 'Mi', 'Gi', 'Ti', 'Pi', 'Ei', 'Zi']:
        if abs(num) < 1024.0:
            return "%3.1f%s%s" % (num, unit, suffix)
        num /= 1024.0
    return "%.1f%s%s" % (num, 'Yi', suffix)
