import logging
import os
import sys

import hjson
from yarl import URL


def get_config(key_name: str, default: str = '') -> str:
    json_env_map = {
        'port': 'PORT',
        'tg_api_id': 'TG_API_ID',
        'tg_api_hash': 'TG_API_HASH',
        'tg_bot_token': 'TG_BOT_TOKEN',
        'host': 'HOST',
        'link_prefix': 'LINK_PREFIX',
        'keep_awake': 'KEEP_AWAKE',
        'keep_awake_url': 'KEEP_AWAKE_URL',
        'web_api_key': 'WEB_API_KEY',
        'show_index': 'SHOW_INDEX',
        'debug': 'DEBUG',
        'allow_user_ids': 'ALLOW_USER_IDS',
        'admin_id': 'ADMIN_ID',
        'max_file_size': 'MAX_FILE_SIZE'
    }
    config_file_name = os.environ.get('CFG_FILE', 'env.json')
    config_file = os.path.join(os.path.dirname(__file__), '..', config_file_name)
    if os.path.isfile(config_file):
        config_obj = hjson.load(config_file)
        return config_obj.get(key_name, os.environ.get(json_env_map[key_name], default))
    return os.environ.get(json_env_map[key_name], default)


log = logging.getLogger('telegram-file-to-web')
try:
    port = int(get_config('port', '8080'))
except ValueError:
    port = -1
if not 1 <= port <= 65535:
    print('Please make sure the PORT environment variable is an integer between 1 and 65535')
    sys.exit(1)

try:
    api_id = int(get_config('tg_api_id', ''))
    api_hash = get_config('tg_api_hash', '')
    bot_token = get_config('tg_bot_token', '')
except (KeyError, ValueError):
    print('Please set the TG_API_ID and TG_API_HASH and TG_BOT_TOKEN environment variables correctly')
    print('You can get your own API keys at https://my.telegram.org/apps and @botfather')
    sys.exit(1)

trust_headers = False
host = get_config('host', '0.0.0.0')
# public_url = URL(os.environ.get('PUBLIC_URL', f'http://{host}:{port}'))
link_prefix = URL(get_config('link_prefix', f'http://{host}:{port}'))
keep_awake = get_config('keep_awake', '0') != '0'
keep_awake_url = get_config('keep_awake_url', str(link_prefix))
session = "dyimg"
# log_config = os.environ.get('LOG_CONFIG')
debug = get_config('debug', '0') != '0'
web_api_key = get_config('web_api_key', '')
show_index = get_config('show_index', '0') != '0'

if web_api_key == '':
    web_api_key = None

try:
    # The per-user ongoing request limit
    request_limit = 5
except ValueError:
    print('Please make sure the REQUEST_LIMIT environment variable is an integer')
    sys.exit(1)

try:
    # The per-DC connection limit
    connection_limit = 20
except ValueError:
    print('Please make sure the CONNECTION_LIMIT environment variable is an integer')
    sys.exit(1)

allowed_user = get_config('allow_user_ids', '').split(',')
max_file_size = int(get_config('max_file_size', str(1024 * 1024 * 20)))
if max_file_size > 1024 ** 2 * 1500:
    log.info('set max file size to 1.5GB due to telegram restriction')
try:
    admin_id = int(get_config('admin_id', '0'))
except ValueError:
    admin_id = 0
