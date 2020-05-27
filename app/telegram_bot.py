import logging
from typing import cast

from telethon import TelegramClient, events
from telethon.tl.custom import Message
from telethon.tl.types import InputPeerChannel, InputPeerChat, InputPeerUser

from .config import link_prefix, api_id, api_hash, allowed_user, max_file_size, admin_id, session
from .string_encoder import StringCoder
from .transfer_helper import ParallelTransferrer
from .util import get_file_name, get_media_meta

log = logging.getLogger('telegram-file-to-web')

client = TelegramClient(session, api_id, api_hash)

# import socks
# proxy = (socks.SOCKS5, '127.0.0.1', 7891)
# client = TelegramClient(session, api_id, api_hash, proxy=proxy)

transfer = ParallelTransferrer(client)


def new_message_filter(message_text):
    return not str(message_text).startswith('/start')


def get_url_by_event(evt: events.NewMessage.Event) -> object:
    ret = get_media_meta(evt.media)
    if ret[0] and ret[1] and (ret[2] <= max_file_size or max_file_size == -1):
        middle_x = StringCoder.encode(
            f"{evt.chat_id}|{evt.id}|{1 if evt.is_group else 0}|{1 if evt.is_channel else 0}")
        log.debug(f"{evt.chat_id}|{evt.id}|{1 if evt.is_group else 0}|{1 if evt.is_channel else 0}")
        # url = public_url / str(pack_id(evt)) / get_file_name(evt)
        url = link_prefix / middle_x / get_file_name(evt)
        log.debug(f'Link to {evt.id} in {evt.chat_id}: {url}')
        return f'[{url}]({url})'
    else:
        if admin_id == evt.from_id and ret[0]:
            log.debug('admin usage')
            middle_x = StringCoder.encode(
                f"{evt.chat_id}|{evt.id}|{1 if evt.is_group else 0}|{1 if evt.is_channel else 0}")
            log.debug(f"{evt.chat_id}|{evt.id}|{1 if evt.is_group else 0}|{1 if evt.is_channel else 0}")
            # url = public_url / str(pack_id(evt)) / get_file_name(evt)
            url = link_prefix / middle_x / get_file_name(evt)
            log.debug(f'Link to {evt.id} in {evt.chat_id}: {url}')
            return f'[{url}]({url})'
        else:
            log.info('non-admin can not serve other than image')
            return None
    pass


def get_url_by_message(message: Message, is_group: bool, is_channel: bool) -> object:
    ret = get_media_meta(message.media)
    if ret[0] and ret[1] and (ret[2] <= max_file_size or max_file_size == -1):
        middle_x = StringCoder.encode(
            f"{message.chat_id}|{message.id}|{1 if is_group else 0}|{1 if is_channel else 0}")
        log.debug(f"{message.chat_id}|{message.id}|{1 if is_group else 0}|{1 if is_channel else 0}")
        # url = public_url / str(pack_id(evt)) / get_file_name(evt)
        url = link_prefix / middle_x / get_file_name(message)
        log.debug(f'Link to {message.id} in {message.chat_id}: {url}')
        return f'[{url}]({url})'
    else:
        if admin_id == message.from_id and ret[0]:
            log.debug('admin usage')
            middle_x = StringCoder.encode(
                f"{message.chat_id}|{message.id}|{1 if is_group else 0}|{1 if is_channel else 0}")
            log.debug(f"{message.chat_id}|{message.id}|{1 if is_group else 0}|{1 if is_channel else 0}")
            # url = public_url / str(pack_id(evt)) / get_file_name(evt)
            url = link_prefix / middle_x / get_file_name(message)
            log.debug(f'Link to {message.id} in {message.chat_id}: {url}')
            return f'[{url}]({url})'
        else:
            log.info('non-admin can not serve other than image')
            return None


@client.on(events.NewMessage(pattern='/start'))
async def handle_start(evt: events.NewMessage.Event) -> None:
    c = await evt.reply('send me an image to host it on web')
    # log.debug(c)
    # await asyncio.sleep(5)
    # await client.delete_messages(evt.input_chat, [c.id])
    # await evt.delete()
    raise events.StopPropagation


@client.on(events.NewMessage(pattern='/del'))
async def handel_del(evt: events.NewMessage.Event) -> None:
    if evt.reply_to_msg_id is not None:
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

        log.debug(f'c.from_id={c.from_id},evt_from={evt.from_id},reply_chat_id={c.chat_id}'
                  f',reply_msg_from={reply_msg.from_id if reply_msg is not None else 0}')

        if c.from_id == evt.from_id or (c.from_id == me.id and c.chat_id == evt.from_id):
            if (reply_msg is not None and reply_msg.from_id == evt.from_id) or reply_msg is None:
                await client.delete_messages(evt.input_chat, [evt.reply_to_msg_id])
        await evt.delete()
    else:
        evt.reply('please reply the message you want to delete')
    raise events.StopPropagation


@client.on(events.NewMessage(pattern='/link'))
async def handel_link(evt: events.NewMessage.Event) -> None:
    if '*' in allowed_user and not evt.is_private:
        return
    if not (str(evt.from_id) in allowed_user and str(evt.chat_id) in allowed_user) and '*' not in allowed_user:
        log.info(f'user {evt.from_id} or {evt.chat_id} not allowed to use this bot')
        if evt.is_private:
            await evt.delete()
        return

    if evt.reply_to_msg_id is not None:
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
        if c.from_id == evt.message.from_id:
            ret = get_url_by_message(c,evt.is_group,evt.is_channel)
            if ret is not None:
                await c.reply(ret)
            await evt.delete()
        raise events.StopPropagation
    pass


@client.on(events.NewMessage(pattern=new_message_filter))
async def handle_message(evt: events.NewMessage.Event) -> None:
    if '*' in allowed_user and not evt.is_private:
        return
    if not (str(evt.from_id) in allowed_user and str(evt.chat_id) in allowed_user) and '*' not in allowed_user:
        log.info(f'user {evt.from_id} or {evt.chat_id} not allowed to use this bot')
        if evt.is_private:
            await evt.delete()
        return

    if not evt.file:
        log.info('not evt.file')
        await evt.delete()
        return
    try:
        ret = get_url_by_event(evt)
        if ret is None:
            await evt.delete()
        else:
            await evt.reply(ret)
    except Exception as exp:
        await evt.reply(str(exp))
        pass
