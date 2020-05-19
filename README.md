# tgfilestream
A Telegram bot that can stream Telegram files to users over HTTP.

## 安装流程
- 使用 `pip3 install -r requirements.txt` 安装依赖, 
- 配置 环境变量 
- 最后 `python3 start.py` 开始

### nginx 反代
```bash
location / {
  #Proxy Settings
  proxy_set_header Host               $host;
  proxy_set_header X-Real-IP          $remote_addr;
  proxy_set_header X-Forwarded-For    $proxy_add_x_forwarded_for;
  proxy_set_header Accept-Encoding    "";
  
  proxy_redirect off;
  proxy_intercept_errors on;
  proxy_max_temp_file_size 5120k;
  proxy_headers_hash_max_size 512;
  proxy_headers_hash_bucket_size  512;
  proxy_connect_timeout   90;
  proxy_send_timeout 90;
  
  proxy_buffer_size 128k;
  proxy_buffers 4 256k;
  proxy_busy_buffers_size 256k;
  proxy_temp_file_write_size 2560k;
  proxy_next_upstream error timeout invalid_header http_500 http_502 http_503 http_504;
  proxy_pass http://<HOST>:<PORT>;
}
```
### 必要的环境变量
* `TG_API_ID` (required) - Telegram API ID ,从 https://my.telegram.org 获取.
* `TG_API_HASH` (required) - Telegram API hash, 同上
* `PORT` (defaults to `8080`) - 默认监听端口.
* `HOST` (defaults to `0.0.0.0`) - 默认监听地址.
* `LINK_PREFIX` (defaults to `http://HOST:PORT`) - 图片访问前缀
* `DEBUG` (defaults to False) - 是否显示 debug 日志
* `ALLOW_USER_IDS` (defaults to []) - bot服务白名单, `*` 为所有用户,当指定 `*` 时,只响应私聊消息
* `MAX_FILE_SIZE` (defaults to 20 MB) - 文件最大值(单位字节)
* `WEB_API_KEY` (default to NULL) Web 接口删除图片认证Key
* `SHOW_INDEX` (default to False) 是否在 `LINK_PREFIX` 下显示 bot 信息和链接

### Try
[![Deploy](https://www.herokucdn.com/deploy/button.svg)](https://heroku.com/deploy)
