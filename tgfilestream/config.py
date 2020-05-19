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
import os
import sys

from yarl import URL

try:
    port = int(os.environ.get('PORT', '8080'))
except ValueError:
    port = -1
if not 1 <= port <= 65535:
    print('Please make sure the PORT environment variable is an integer between 1 and 65535')
    sys.exit(1)

try:
    api_id = int(os.environ['TG_API_ID'])
    api_hash = os.environ['TG_API_HASH']
    bot_token = os.environ['TG_BOT_TOKEN']
except (KeyError, ValueError):
    print('Please set the TG_API_ID and TG_API_HASH and TG_BOT_TOKEN environment variables correctly')
    print('You can get your own API keys at https://my.telegram.org/apps and @botfather')
    sys.exit(1)

trust_headers = os.environ.get('TRUST_FORWARD_HEADERS', '0') != '0'
host = os.environ.get('HOST', '0.0.0.0')
public_url = URL(os.environ.get('PUBLIC_URL', f'http://{host}:{port}'))
link_prefix = URL(os.environ.get('LINK_PREFIX', public_url))
keep_awake = os.environ.get('KEEP_AWAKE', '0') != '0'
keep_awake_url = os.environ.get('KEEP_AWAKE_URL', link_prefix)
session = "dyimg"
log_config = os.environ.get('LOG_CONFIG')
debug = os.environ.get('DEBUG', '0') != '0'
web_api_key = os.environ.get('WEB_API_KEY', None)
show_index = os.environ.get('SHOW_INDEX', '0') != '0'

if web_api_key == '':
    web_api_key = None

try:
    # The per-user ongoing request limit
    request_limit = int(os.environ.get('REQUEST_LIMIT', '5'))
except ValueError:
    print('Please make sure the REQUEST_LIMIT environment variable is an integer')
    sys.exit(1)

try:
    # The per-DC connection limit
    connection_limit = int(os.environ.get('CONNECTION_LIMIT', '20'))
except ValueError:
    print('Please make sure the CONNECTION_LIMIT environment variable is an integer')
    sys.exit(1)

allowed_user = os.environ.get('ALLOW_USER_IDS', '').split(',')
max_file_size = int(os.environ.get('MAX_FILE_SIZE', str(1024 * 1024 * 20)))
try:
    admin_id = int(os.environ.get('ADMIN_ID', 0))
except ValueError:
    admin_id = 0
