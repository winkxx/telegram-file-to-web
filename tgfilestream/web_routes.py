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
import base64
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


@routes.get(r'/favicon.ico')
async def favicon(req: web.Request) -> web.Response:
    b_data = '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kP+GblL/yJ1s/8idbP/InWz/yJ1s/8idbP/InWz/yJ1s/8idbP+/l2n/l3pZ/2dYRv85NzX/VlZW/93d3f/X19f/NzU0/7+Waf/InWz/yJ1s/8idbP/InWz/wplq/6CBXf+ggV3/sY1j/8idbP/InWz/yJ1s/5h6Wf8lVGz/JFZw/5N3V//InWz/yJ1s/8idbP+yjWT/oIFd/6CBXf/BmGn/yJ1s/8idbP/InWz/yJ1s/8CYaf88OTb/09PT//Hx8f85OTn/t5Vs/8idbP/InWz/yJ1s/8idbP+/lmj/hm5S/4ZuUv+igV3/yJ1s/8idbP/InWz/yJ1s/5l8Wv+Xeln/x51s/8idbP/InWz/yJ1s/6SDXf+GblL/hm5S/72VaP/InWz/yJ1s/8idbP/InWz/vppu/zU1NP/r6+v/9/f3/25ubv9/b1n/0ax9/8ykdP/Jn27/yJ1s/7+WaP+GblL/hm5S/6KCXf/InWz/qYdg/3lkTf9aT0H/TEQ8/0tEPP9ZTkH/d2NM/6eFX//InWz/pINe/4ZuUv+GblL/vZVo/8idbP/Jnm3/zKN0/9GrfP+HdV3/aGho//Pz8//z8/P/09PT/zs7Ov+NemD/y6yB/9a0hv/Tr4H/z6l6/82kdP/KoG//t5Fl/1tPQv82NTL/XFA//35oTf+PdFP/j3RT/39oTf9eUUD/NzUz/1hNQP+1j2X/yZ9v/8ykdP/PqXr/06+A/9azhf/MrIH/kX1j/zo5OP/Kysr/+Pj4//f39//19fX/xsbG/1RUVP80MzP/UEpB/3NlU/+TfmP/r5Vy/72gef9GQjz/MjIy/25aOP+BZjr/gWY6/4FmOv+BZjr/gWY6/4FmOv9xXDn/MjIy/0NAO/+7n3j/sJVy/5N/ZP90ZlT/UUtC/zQ0M/9TU1P/wMDA//X19f/z8/P/9fX1//X19f/19fX/9fX1/9/f3/+wsLD/i4uL/2NjY/9ERET/MjIy/21tbf9KSkr/qIZf/7+Xaf+PdFb/fGZP/31nT/+PdFb/vpZo/62KYf9DQ0P/c3Nz/zIyMv9CQkL/ZGRk/4aGhv+ysrL/3d3d//X19f/19fX/9fX1//X19f/z8/P/9fX1//f39//z8/P/9vb2//b29v/z8/P/9vb2//b29v/n5+f/8PDw/0pKSv9rWDz/Pzs2/1FKQv9vYlH/bmFR/1JLQv89OjX/bFk9/0NDQ//u7u7/6urq//T09P/09PT/9/f3//T09P/19fX/9/f3//Pz8//19fX/9/f3//j4+P/19fX/8/Pz//j4+P/09PT/8/Pz//j4+P/09PT/9PT0//j4+P/z8/P/S0tL/zU0Mv9/cFr/1bSG/9a0hv/WtIb/1rSG/4VzXP82NDL/QkJC//f39//y8vL/9vb2//b29v/y8vL/9/f3//b29v/y8vL/9/f3//X19f/y8vL/9PT0//X19f/39/f/9PT0//b29v/29vb/9PT0//b29v/29vb/9PT0//Dw8P9AQED/c2VT/9Wzhv/WtIb/1rSG/9a0hv/WtIb/1rSG/3hpVf88PDz/7Ozs//f39//09PT/9PT0//f39//09PT/9fX1//f39//09PT/9fX1//f39//19fX/9fX1//X19f/19fX/9fX1//X19f/19fX/9fX1//X19f/19fX/mJiY/1ZQR//TsoX/1rSG/8+vg/94aVX/eGlV/8ysgP/WtIb/1LKF/1lRRv+Tk5P/9fX1//X19f/19fX/9fX1//X19f/19fX/9vb2//X19f/19fX/9fX1//f39//19fX/8/Pz//f39//09PT/9PT0//f39//09PT/9PT0//f39/9ISEj/rZh4/9Wzhv/MrIH/xKZ9/8KkfP/CpHz/xKZ9/8ysgf/Vs4b/rpRx/0NDQ//w8PD/9vb2//b29v/z8/P/9vb2//b29v/z8/P/9/f3//X19f/z8/P/8vLy//X19f/39/f/8vLy//b29v/39/f/8vLy//b29v/29vb/2NjY/zMzM/91cmn/c3h1/3uEg/+DjIz/hY+O/4WPjv+DjYz/fIWE/3N4dv9zb2X/NDQ0/9fX1//09PT/9PT0//j4+P/z8/P/9PT0//j4+P/z8/P/9fX1//j4+P/29vb/9fX1//T09P/39/f/9fX1//T09P/29vb/9PT0//T09P/Gxsb/TU9P/9Pj4v/I2tn/yNrZ/8ja2f+ap6b/mKSk/8ja2f/I2tn/yNrZ/8ja2f9OUlL/vb29//b29v/29vb/9PT0//b29v/29vb/9PT0//b29v/19fX/9PT0//b29v/19fX/9fX1//b29v/19fX/9fX1//X19f/19fX/9fX1/7CwsP9eYmL/0ODf/8ja2f/I2tn/n6ys/2hmZP9lY2D/mqem/8ja2f/I2tn/yNrZ/11iYv+pqan/9fX1//X19f/09PT/9fX1//X19f/19fX/9vb2//X19f/19fX/8/Pz//X19f/39/f/8/Pz//b29v/29vb/8/Pz//b29v/29vb/lpaW/3R6ev/N3t3/yNrZ/8ja2f+Bior/YF9c/15dW/98hIT/yNrZ/8ja2f/I2tn/cHh4/5GRkf/09PT/9PT0//f39//09PT/9PT0//f39//z8/P/9fX1//f39//39/f/9fX1//Pz8//4+Pj/9PT0//Pz8//4+Pj/9PT0//T09P9/f3//i5KS/8rb2v/I2tn/yNrZ/1Z2fv8cicX/IILA/1Jvff/I2tn/yNrZ/8ja2f+Ejo3/d3d3//b29v/29vb/8vLy//f39//29vb/8/Pz//f39//19fX/8vLy//T09P/19fX/9vb2//T09P/19fX/9vb2//T09P/29vb/9vb2/2VlZf+gqaj/yNrZ/8ja2f+uvbz/KG6W/xyQ2f8ejdT/J26b/6q5uP/I2tn/yNrZ/5ejov9fX1//9PT0//T09P/29vb/9PT0//X19f/29vb/9PT0//X19f/29vb/9fX1//X19f/29vb/9fX1//X19f/19fX/9PT0//b29v/29vb/Tk5O/7S/vv/I2tn/xdfW/0Fpd/8anOz/HJDZ/x6N1P8anO7/P2N4/8PV1P/I2tn/qbe3/0dHR//19fX/9fX1//X19f/19fX/9fX1//b29v/19fX/9fX1//b29v/39/f/9fX1//Pz8//39/f/9fX1//T09P/39/f/9PT0//T09P9ERET/vcnI/8ja2f+hr67/GIu5/xqe8f8he7T/Inmw/xqe8f8ggb7/m6in/8ja2f+ywcH/PT09//b29v/29vb/8/Pz//b29v/29vb/8/Pz//f39//19fX/8/Pz//Pz8//19fX/9/f3//Pz8//29vb/9/f3//Pz8//29vb/9vb2/0lJSf+8x8b/yNrZ/5Sgn/8Snc//Gp7x/yCCwP8ggb3/Gp7x/x6M0f+Pm5r/yNrZ/669vP9BQUH/9PT0//T09P/4+Pj/9PT0//X19f/4+Pj/8/Pz//X19f/4+Pj/9vb2//X19f/09PT/9vb2//X19f/09PT/9vb2//T09P/09PT/X19f/6Strf/N3tz/sMC//xqBov8UqPP/Gp7x/xqe8f8anvH/JHOk/6y7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OP9APDf/PTk2/zk3Nf81NDP/MjIy/zY2Nv9RUVH/e3t7/6ampv/Ly8v/4uLi/+Xl5f/29vb/8vLy//f39//19fX/9fX1//n5+f/y8vL/+vr6//r6+v/y8vL/+Pj4//X19f/09PT/4+Pj/7a2tv+Xl5f/b29v/1FRUf84ODj/NTQz/0U/Of9YTUD/aVlH/3hkTf+GblL/knZX/51+W/+lhF//rIlh/7GNY/+0jmT/pIRe/6SDXv+zjmT/sY1j/6yJYf+lhF//nX5b/5J2V/+GblL/eGRN/2hZR/9XTED/RD85/zQ0M/83Nzf/UFBQ/3Nzc/+SkpL/v7+//9/f3//19fX/9fX1//Ly8v/4+Pj/8fHx//Dw8P/5+fn/8fHx/8rKyv9/f3//T09P/z4+Pv81NTX/Ojg0/15SQ/+GblL/qIZg/7WPZf+7lGf/wZhp/8aca//InWz/yJ1s/8idbP/InWz/yJ1s/8Wba/+KcVT/SEI6/0dBOv+GblL/xZpr/8idbP/InWz/yJ1s/8idbP/InWz/xpxr/8GYaf+7lGf/tY9l/6iGX/+GblL/XlFD/zo4Nf80NDT/Pz8//05OTv96enr/x8fH//j4+P/y8vL/+/v7//f39/++vr7/W1tb/zMyMv87ODX/R0A6/2lZR/+afFr/wZhq/8idbP/InWz/yJ1s/8idbP/InWz/yJ1s/8idbP/InWz/yJ1s/8idbP/InWz/yJ1s/7aQZf9FRD//HG2U/xtvmf9AQkD/tI9k/8idbP/InWz/yJ1s/8idbP/InWz/yJ1s/8idbP/InWz/yJ1s/8idbP/InWz/yJ1s/8GYav+bfVv/allH/0dBOv87ODX/MzIy/1dXV/+7u7v/7u7u/+np6f9zc3P/NzU0/3FfSv+Xeln/uZJm/8idbP/InWz/yJ1s/8idbP/InWz/yJ1s/8idbP/InWz/yJ1s/8idbP/InWz/yJ1s/8idbP/InWz/yJ1s/7GNY/81Q0n/DZbb/wyY3/8wRE3/roti/8idbP/InWz/yJ1s/8idbP/InWz/yJ1s/8idbP/InWz/yJ1s/8idbP/InWz/yJ1s/8idbP/InWz/yJ1s/7qTZv+Ye1n/c2FL/zo4Nf9ra2v/6enp/+3t7f97e3v/OTc0/8KZav/InWz/yJ1s/8idbP/InWz/yJ1s/8idbP/InWz/uZJm/4ZuU/+GblP/hm5T/491V//DmWr/yJ1s/8idbP/InWz/yJ1s/7uUZ/9XTkL/KUhY/yhKW/9SS0H/upNm/8idbP/InWz/yJ1s/8idbP/Fmmv/kXVX/4ZuU/+GblP/hm5T/7WQZf/InWz/yJ1s/8idbP/InWz/yJ1s/8idbP/InWz/xJpq/0M+OP9ycnL/6urq//j4+P+QkJD/MzMz/7STa//Inm3/yJ1s/8idbP/InWz/yJ1s/8idbP/InWz/tI9k/3VhS/91YUv/dWFL/4FqT//BmGn/yJ1s/8idbP/InWz/yJ1s/8idbP+timL/alpI/2hYR/+qiGH/yJ1s/8idbP/InWz/yJ1s/8idbP/Dmmr/gWpQ/3VhS/91YUv/dWFL/7GMY//InWz/yJ1s/8idbP/InWz/yJ1s/8idbP/InW3/v5tv/zQzMv+FhYX/7Ozs//Hx8f+wsLD/PDw8/4NyWv/OqHn/yZ9v/8idbP/InWz/yJ1s/8idbP/InWz/tI9k/3NgS/9zYEv/c2BL/4BpUP/BmGn/yJ1s/8idbP/HnWz/vJVn/6mHYP+cflv/lnlZ/5V5Wf+cfVv/qIZg/7uUZ//HnGz/yJ1s/8idbP/Dmmr/gGlQ/3NgS/9zYEv/c2BL/7CMY//InWz/yJ1s/8idbP/InWz/yJ1s/8mebv/Op3f/kXxh/zg4OP+mpqb/+fn5//v7+//b29v/S0tL/0tGP/+/oXr/1LCC/9GqfP/MpHT/yJ9u/8idbP/InWz/w5lq/7KNY/+yjWP/so1j/7WPZf/GnGv/yJ1s/6SDX/9pWUf/SUI7/0E9OP89Ojb/Ojg1/zo4Nf88OTb/QDw4/0hCOv9mV0b/oIFd/8ecbP/HnGz/tZBl/7KNY/+yjWP/so1j/8KYav/InWz/yJ1s/8iebf/Mo3P/0Kl7/9Swgv/Fpnz/UEpB/0lJSf/X19f/8PDw//Hx8f/4+Pj/nJyc/zc3Nv9rX0//v6J6/9Gwg//WtIb/1bOF/9Kuf//OqHj/y6Fx/8qgb//Jn27/yJ5t/8aca/+qiGD/XlJD/zIyMv85NzT/Qz43/1ZLP/9tXEj/eWRM/3lkTP9uXEj/V0w//0M+OP85NzT/MjIy/1lOQf+nhl//xptr/8iebf/Jn27/yp9v/8uhcf/Op3f/0q1+/9Wzhf/WtIb/0bCE/8Gje/9yZFP/NzY1/4+Pj//y8vL/+vr6//f39//09PT/8fHx/4iIiP87Ozv/T0lB/3VnVP+PfGH/qJBu/8Ciev/RsIT/1bOG/9Sxgv/SrX//0Kp7/5l+Xv9IQTr/MjIy/0pBNP9tWjv/i25G/5p5TP+aeUz/mnlM/5p5TP+aeUz/mnlM/41wR/9vWjz/TEM1/zIyMv9FQDn/k3lb/9Cqe//SrX7/1LCC/9Wzhf/RsYT/wKN7/6mQb/+QfWL/dmhV/1JLQv87Ojr/fn5+/+np6f/29vb/9PT0//X19f/19fX/9fX1/+3t7f+wsLD/VVVV/zIyMv82NTT/Pjw4/0ZCPP9TS0L/b2JR/416Yf+rkXD/qJBv/z47OP8zMzP/MjIy/2RTN/+CZzv/gmc7/4JnO/+CZzv/gmc7/4JnO/+CZzv/gmc7/4JnO/+CZzv/aVY4/zIyMv8zMzP/PDo3/6KLbP+sknD/j3ti/3BjUf9TTEP/RkI8/z88Of83NjT/MjIy/1NTU/+srKz/6urq//X19f/19fX/9fX1//Hx8f/4+Pj/8vLy//X19f/29vb/8/Pz/+Dg4P+pqan/eXl5/1VVVf9JSUn/QUFB/zo6Ov80NDT/MjIy/z8/P/9vb2//Ojo6/5N3V//HnGz/wplq/7aQZv+vi2P/q4hi/6uJYv+vi2P/tpBl/8KYav/HnGz/nH1b/zg4OP9xcXH/Q0ND/zIyMv80NDT/OTk5/0BAQP9JSUn/U1NT/3d3d/+oqKj/1tbW//f39//19fX/9fX1//n5+f/y8vL/+fn5//n5+f/z8/P/+Pj4//X19f/19fX/9/f3//Ly8v/4+Pj/8vLy//Ly8v/X19f/wMDA/6urq/+VlZX/g4OD/5mZmf+np6f/Ojo6/4JqS/+hgVj/dGFL/0tEPP84NjT/MzMy/zMzMv84NjT/SkM7/3FfSv+gf1j/iW9O/zg4OP+fn5//nZ2d/4ODg/+VlZX/qamp/7+/v//X19f/7Ozs//n5+f/z8/P/+fn5//T09P/29vb/9fX1//Ly8v/39/f/8fHx//Dw8P/5+fn/8fHx//b29v/29vb/8/Pz//r6+v/x8fH/+/v7//Hx8f/39/f/9PT0//T09P/29vb/6+vr//f39/+qqqr/Ojo6/2BRN/9LQzb/MzMy/1VNRP+Jdl//mYNn/5eDZ/+Idl7/WE9F/zMzMv9JQTb/ZFM5/zg4OP+mpqb/7e3t//Pz8//y8vL/9/f3//f39//z8/P/+fn5//Dw8P/5+fn/8fHx//f39//19fX/9fX1//n5+f/y8vL/+/v7//v7+//y8vL/+fn5//X19f/19fX/9/f3//Hx8f/4+Pj/8fHx//n5+f/09PT/9vb2//b29v/09PT/+fn5//Hx8f+tra3/Ojo6/zw5M/83NjX/g3Nc/9Wzhf/WtIb/1rSG/9a0hv/WtIb/1bOG/4p4X/85NzX/PDkz/zg4OP+jo6P/+fn5//Hx8f/29vb/9PT0//T09P/29vb/8fHx//n5+f/y8vL/+fn5//Pz8//19fX/9fX1//Hx8f/4+Pj/8PDw//T09P/29vb/9PT0//X19f/29vb/9PT0//f39//09PT/9/f3//T09P/29vb/9fX1//X19f/29vb/9PT0//f39/+rq6v/Ojo6/zc2NP94aVb/za2B/9a0hv/WtIb/1rSG/9a0hv/WtIb/1rSG/8+ugv99bVj/NzY1/zg4OP+lpaX/8/Pz//b29v/09PT/9fX1//X19f/09PT/9vb2//Pz8//29vb/9PT0//b29v/19fX/9fX1//b29v/09PT/9/f3//b29v/19fX/9vb2//X19f/19fX/9fX1//X19f/19fX/9fX1//b29v/19fX/9fX1//X19f/19fX/9vb2//Hx8f+SkpL/NTU1/2ldTv/Lq4D/1rSG/9a0hv/WtIb/1rSG/9a0hv/WtIb/1rSG/9a0hv/NrYH/cGJR/zQ0NP+MjIz/8fHx//X19f/19fX/9fX1//X19f/19fX/9fX1//b29v/09PT/9vb2//X19f/29vb/9fX1//X19f/29vb/9fX1//n5+f/z8/P/+Pj4//X19f/19fX/9/f3//Ly8v/39/f/8vLy//j4+P/09PT/9vb2//b29v/09PT/+Pj4/9PT0/9LS0v/U05G/86ug//WtIb/1rSG/9Syhf+bhWj/b2JR/29iUf+XgmX/0rGE/9a0hv/WtIb/0bCE/1dQRf9HR0f/2NjY//Pz8//29vb/9PT0//T09P/29vb/8/Pz//j4+P/z8/P/+Pj4//T09P/29vb/9fX1//Ly8v/39/f/8fHx//Ly8v/39/f/8vLy//X19f/29vb/9PT0//j4+P/z8/P/+Pj4//Pz8//29vb/9PT0//T09P/29vb/8/Pz/5WVlf89Ozn/sJp6/9a0hv/WtIb/1rSG/9Wzhf+/onr/rpRx/66Ucf++oHn/1LOF/9a0hv/WtIb/1rSG/7CWc/8/PDj/hYWF//f39//09PT/9vb2//b29v/09PT/9/f3//Ly8v/39/f/8vLy//b29v/19fX/9fX1//j4+P/z8/P/+fn5//v7+//y8vL/+fn5//X19f/19fX/9/f3//Dw8P/5+fn/8PDw//n5+f/z8/P/9/f3//f39//z8/P/+Pj4/0ZGRv9lXlH/zrGI/9a0hv/Pr4P/wqR7/7qeeP+2m3b/tpp1/7aadf+2m3b/up54/8Kke//Pr4P/1rSG/8ysgf9nXE3/QEBA/+vr6//39/f/8/Pz//Pz8//39/f/8fHx//v7+//x8fH/+vr6//Pz8//29vb/9vb2//Hx8f/5+fn/7+/v//Dw8P/4+Pj/8fHx//X19f/29vb/8/Pz//r6+v/y8vL/+vr6//Hx8f/39/f/9PT0//T09P/39/f/z8/P/zIyMv9aVU3/cmpc/1hWUP9MTUz/TVBQ/1RYWP9YXFz/WF1d/1hdXf9YXVz/VFlZ/05RUf9LTUz/V1VQ/3BmWf9aU0n/MjIy/8zMzP/09PT/9/f3//f39//09PT/+Pj4//Hx8f/4+Pj/8fHx//f39//09PT/9fX1//n5+f/y8vL/+vr6//f39//09PT/9/f3//X19f/19fX/9vb2//T09P/29vb/8/Pz//b29v/09PT/9fX1//X19f/09PT/tLS0/zY3N/92fHz/oq6u/7LBwP+/0M//x9jX/8ja2f/I2tn/yNrZ/8ja2f/I2tn/yNrZ/8fZ1/+/0dD/ssLB/6Curf9xeXj/Nzc3/6enp//29vb/9fX1//X19f/29vb/9PT0//f39//09PT/9/f3//T09P/19fX/9fX1//T09P/29vb/8/Pz//T09P/29vb/9PT0//X19f/19fX/9fX1//b29v/09PT/9vb2//T09P/19fX/9PT0//T09P/19fX/oaGh/zw8PP+lrq3/zN3c/8ja2f/I2tn/yNrZ/8ja2f+tvLv/bHNz/2pxcf+rubn/yNrZ/8ja2f/I2tn/yNrZ/8ja2f+bqKf/PD09/5eXl//19fX/9vb2//b29v/19fX/9vb2//T09P/29vb/9PT0//b29v/19fX/9fX1//b29v/09PT/9/f3//Ly8v/39/f/8/Pz//X19f/29vb/9PT0//j4+P/z8/P/+Pj4//Pz8//29vb/9PT0//T09P/29vb/iIiI/0BBQf+uubj/y9zb/8ja2f/I2tn/yNrZ/73Ozf9na2v/aGZi/2ZkYf9hZWT/vMzL/8ja2f/I2tn/yNrZ/8ja2f+ls7L/P0FB/39/f//09PT/9vb2//b29v/09PT/9/f3//Ly8v/39/f/8/Pz//f39//19fX/9fX1//f39//z8/P/+fn5//n5+f/z8/P/+Pj4//X19f/19fX/9vb2//Ly8v/39/f/8vLy//f39//09PT/9/f3//b29v/09PT/b29v/0VGRv+7x8f/ytzb/8ja2f/I2tn/yNrZ/7XFxP9mZ2b/jYqG/4eEf/9gYF//tMPD/8ja2f/I2tn/yNrZ/8ja2f+ywcD/REZG/2JiYv/29vb/9PT0//T09P/29vb/8/Pz//j4+P/z8/P/+Pj4//T09P/29vb/9fX1//Ly8v/39/f/8vLy/+/v7//5+fn/8fHx//b29v/29vb/8/Pz//r6+v/x8fH/+/v7//Hx8f/39/f/9PT0//Pz8//19fX/VlZW/0pMS//H1tT/ydva/8ja2f/I2tn/yNrZ/5+sq/8/QD//SEhH/0hHRv8+Pj7/mKSj/8ja2f/I2tn/yNrZ/8ja2f+/0M//SEtL/1JSUv/r6+v/9/f3//f39//z8/P/+fn5//Dw8P/5+fn/8PDw//f39//19fX/9fX1//n5+f/y8vL/+/v7//r6+v/y8vL/+Pj4//X19f/09PT/9/f3//Dw8P/4+Pj/8PDw//j4+P/z8/P/9vb2//b29v/h4eH/TU1N/1FTU//T4uH/ydva/8ja2f/I2tn/yNrZ/4CQkv8gcpX/IHer/yRyo/8lbJf/d4aJ/8ja2f/I2tn/yNrZ/8ja2f/I2tn/UlZW/0tLS//g4OD/9PT0//T09P/39/f/8fHx//r6+v/y8vL/+fn5//T09P/29vb/9fX1//Hx8f/4+Pj/8PDw//Pz8//29vb/8/Pz//X19f/29vb/9PT0//f39//z8/P/9/f3//T09P/29vb/9fX1//X19f/V1dX/SEhI/2Vpaf/U5OP/yNrZ/8ja2f/I2tn/xdbV/1Bka/8cjcr/HYfK/yGCwf8ei8//Slxl/8PU0//I2tn/yNrZ/8ja2f/I2tn/Z21s/0VFRf/Ly8v/9vb2//b29v/09PT/9vb2//Pz8//39/f/8/Pz//b29v/19fX/9fX1//f39//09PT/9/f3//f39//09PT/9vb2//X19f/19fX/9vb2//T09P/29vb/9PT0//f39//19fX/9fX1//X19f/BwcH/QkJC/36Eg//T4+L/yNrZ/8ja2f/I2tn/hY+P/ypad/8anO3/HYfK/yGCwf8anO7/Kl5//36Hh//H2dj/yNrZ/8ja2f/I2tn/fIWE/0BAQP+9vb3/9PT0//T09P/19fX/9PT0//f39//09PT/9vb2//T09P/19fX/9fX1//T09P/29vb/8/Pz//n5+f/z8/P/9/f3//X19f/19fX/9/f3//Pz8//39/f/8vLy//f39//09PT/9/f3//f39/+wsLD/PDw8/5Wenf/R4eD/yNrZ/8ja2f+grq3/Nlll/xuY5P8anvH/HYfK/yGCwf8anvH/G5no/zZXav+ap6b/x9nY/8ja2f/I2tn/kZyc/zo6Ov+vr6//9PT0//T09P/29vb/8/Pz//j4+P/z8/P/+Pj4//T09P/29vb/9fX1//Pz8//39/f/8vLy//Ly8v/39/f/8vLy//X19f/29vb/9PT0//j4+P/z8/P/+Pj4//Pz8//29vb/9PT0//T09P+srKz/OTk5/6Wvrv/R4eD/yNrZ/8LT0v9qfYH/GJLF/xqe8f8bmen/InSn/yRwof8bmOf/Gp7x/yCIyf9kd37/wNHQ/8ja2f/I2tn/nqur/zc3N/+goKD/9vb2//b29v/09PT/9/f3//Ly8v/39/f/8vLy//b29v/19fX/9fX1//j4+P/z8/P/+fn5//v7+//y8vL/+fn5//X19f/19fX/9/f3//Dw8P/5+fn/8PDw//n5+f/z8/P/9/f3//f39/+hoaH/ODg4/6q0s//S4uH/yNrZ/7nJyP9GdoP/EqTj/xqe8f8bl+b/Inet/yJ2rP8cluP/Gp7x/xyW4/9EbIP/t8fG/8ja2f/I2tn/pbKx/zY2Nv+ioqL/8/Pz//Pz8//39/f/8fHx//v7+//x8fH/+vr6//Pz8//29vb/9vb2//Hx8f/5+fn/7+/v//Dw8P/4+Pj/8fHx//X19f/29vb/9PT0//r6+v/y8vL/+vr6//Ly8v/39/f/8/Pz//Pz8/+srKz/OTk5/6exsP/T4+L/yNrZ/7bGxf86dYf/D6vp/xqe8f8bmun/IYG//yGCvv8cmOf/Gp7x/xuY5/87a4f/tcTD/8ja2f/I2tn/oK6t/zY2Nv+dnZ3/9/f3//f39//09PT/+fn5//Dw8P/5+fn/8fHx//f39//19fX/9fX1//n5+f/y8vL/+/v7//j4+P/z8/P/9/f3//X19f/19fX/9vb2//Pz8//29vb/8/Pz//f39//09PT/9vb2//b29v+xsbH/PDw8/5aenv/W5eT/ydrZ/7rKyf9IdYP/DK/l/xei8v8bmen/HoTE/x+Dw/8bmOf/Gp7x/xyV4f9HbYH/uMjH/8ja2f/I2tn/kJub/zo6Ov+urq7/9PT0//T09P/29vb/8/Pz//j4+P/z8/P/+Pj4//T09P/29vb/9fX1//Pz8//39/f/8/Pz//Pz8//29vb/9PT0//X19f/19fX/9PT0//b29v/09PT/9/f3//Pz8//19fX/9PT0//T09P/IyMj/Q0ND/3J3d//a6ef/ytza/8PU0/9sfH7/Ep3J/w2y9f8Zn/H/Gp7x/xqe8f8anvH/Gp7x/yCIyv9od3v/wdPS/8ja2f/I2tn/cXl5/0FBQf/AwMD/9fX1//X19f/19fX/9/f3//T09P/29vb/9PT0//b29v/19fX/9fX1//b29v/09PT/9/f3//Ly8v/39/f/8/Pz//X19f/29vb/9PT0//j4+P/z8/P/+Pj4//Pz8//29vb/9PT0//T09P/n5+f/UlJS/0tMTP/P3Nv/zt7d/8ja2f+hr67/OV5p/w2s3/8Pr/P/F6Ly/xmg8f8anvD/HZPc/zpabP+cqan/yNrZ/8ja2f++zs3/S05O/05OTv/e3t7/9vb2//b29v/09PT/9/f3//Ly8v/39/f/8/Pz//f39//19fX/9fX1//f39//z8/P/+Pj4//j4+P/z8/P/9/f3//X19f/19fX/9vb2//Pz8//39/f/8vLy//f39//09PT/9vb2//b29v/09PT/j4+P/zk6Ov+Xn57/2Obl/8rc2//G2Nf/k56d/0BmcP8agKH/FJXE/xePw/8gdqH/QGBx/42ZmP/F19b/yNrZ/8bY1/+OmZj/OTo6/4SEhP/19fX/9PT0//T09P/29vb/8/Pz//j4+P/z8/P/+Pj4//T09P/29vb/9fX1//Pz8//39/f/8vLy/+/v7//5+fn/8fHx//b29v/29vb/8/Pz//v7+//x8fH/+/v7//Hx8f/39/f/8/Pz//Pz8//39/f/4+Pj/0tLS/9ISkr/vcjH/9rp6P/L3Nv/x9nY/7PCwf+Dk5T/W3B1/1pvdP+AkJL/scHA/8bY1//I2tn/yNrZ/668vP9JTEz/Q0ND/+fn5//z8/P/9/f3//f39//z8/P/+fn5//Dw8P/5+fn/8PDw//j4+P/19fX/9PT0//n5+f/y8vL/+/v7//v7+//x8fH/+vr6//X19f/19fX/+Pj4//Dw8P/5+fn/8PDw//n5+f/z8/P/9/f3//f39//z8/P/+fn5/76+vv9DQ0P/P0BA/6Osq//O29n/z9/e/8vd3P/K3Nv/ydva/8nb2v/J2tn/ydvZ/8fY1/+7zMv/l6Sj/0BCQv9CQkL/wMDA//Hx8f/39/f/8/Pz//Pz8//39/f/8fHx//r6+v/x8fH/+vr6//Pz8//29vb/9fX1//Hx8f/4+Pj/7+/v//Ly8v/39/f/8/Pz//b29v/29vb/9PT0//j4+P/z8/P/+Pj4//Pz8//29vb/9PT0//T09P/29vb/8/Pz//T09P+zs7P/VlZW/zY2Nv9aXV3/gYeH/5ihoP+krq3/qLSy/6eysv+gq6r/kZyb/3uCgv9XXFv/Njc3/1JSUv+0tLT/7u7u//f39//09PT/9vb2//b29v/09PT/9/f3//Pz8//39/f/8/Pz//b29v/19fX/9fX1//f39//z8/P/+Pj4//f39//09PT/9vb2//X19f/19fX/9vb2//T09P/39/f/9PT0//f39//19fX/9vb2//b29v/19fX/9/f3//T09P/19fX/3d3d/5ycnP9NTU3/MzMz/zg4OP89Pj7/P0BA/z9AQP89Pj7/ODk5/zMzM/9ISEj/lZWV/+Hh4f/x8fH/9/f3//Pz8//29vb/9fX1//X19f/29vb/8/Pz//f39//09PT/9/f3//T09P/29vb/9vb2//T09P/29vb/8/Pz//j4+P/09PT/9/f3//X19f/19fX/9vb2//Pz8//39/f/8/Pz//f39//19fX/9vb2//b29v/19fX/9/f3//Pz8//39/f/8/Pz//b29v/w8PD/zMzM/6Wlpf+NjY3/fHx8/4CAgP+Kior/o6Oj/8vLy//v7+//9PT0//f39//z8/P/9/f3//Pz8//29vb/9fX1//X19f/29vb/8/Pz//f39//z8/P/9/f3//T09P/19fX/9fX1//Pz8//29vb/8/Pz//Ly8v/39/f/8/Pz//X19f/29vb/9PT0//f39//z8/P/+Pj4//Pz8//29vb/9PT0//T09P/29vb/8/Pz//j4+P/z8/P/9/f3//T09P/29vb/9fX1//Pz8//39/f/8vLy//j4+P/z8/P/9/f3//X19f/19fX/9vb2//Pz8//39/f/8/Pz//f39//09PT/9vb2//b29v/09PT/9/f3//Pz8//39/f/8/Pz//b29v/19fX/9fX1//f39//z8/P/+Pj4//v7+//x8fH/+vr6//X19f/19fX/+Pj4//Dw8P/5+fn/8PDw//n5+f/z8/P/9/f3//f39//z8/P/+fn5//Dw8P/5+fn/8PDw//j4+P/19fX/9fX1//r6+v/x8fH/+/v7/+/v7//5+fn/8fHx//b29v/29vb/8/Pz//v7+//y8vL/+/v7//Hx8f/39/f/8/Pz//Pz8//39/f/8fHx//v7+//y8vL/+/v7//Pz8//29vb/9vb2//Hx8f/5+fn/7+/v/wAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=='
    return web.Response(status=200
                        , body=base64.decodebytes(b_data.encode('utf-8'))
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


@routes.delete(r'/{id:\S+}')
async def delete_image(req: web.Request) -> web.Response:
    file_id = str(req.match_info['id'])
    check_key = req.headers.get('WEB_AP_KEY')
    if check_key is None or check_key != web_api_key:
        return web.Response(status=401, text='<h3>401 Not Allowed</h3>', content_type='text/html')
    peer, msg_id = extract_peer(file_id)
    if not peer or not msg_id:
        return web.Response(status=404, text='<h3>404 Not Found</h3>', content_type='text/html')
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
