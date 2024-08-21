# ApproveByPoll / Telegram 投票入群机器人
[![wakatime](https://wakatime.com/badge/user/f5b3fb10-0bfa-4783-9750-a21ca2b68285/project/f4986200-f605-49a5-8163-e53dddb58e7b.svg)](https://wakatime.com/badge/user/f5b3fb10-0bfa-4783-9750-a21ca2b68285/project/f4986200-f605-49a5-8163-e53dddb58e7b)
[![actions](https://github.com/KimmyXYC/ApproveByPoll/actions/workflows/docker-ci.yml/badge.svg)](https://github.com/KimmyXYC/ApproveByPoll/actions/workflows/docker-ci.yaml)
[![actions](https://github.com/KimmyXYC/ApproveByPoll/actions/workflows/ruff.yml/badge.svg)](https://github.com/KimmyXYC/ApproveByPoll/actions/workflows/ruff.yml)
## 安装 / Installation

- 下载源码。 Download the code.
```shell
git clone https://github.com/KimmyXYC/ApproveByPoll.git
cd ApproveByPoll
```

- 复制配置文件。 Copy configuration file.
```shell
cp .env.exp .env
```

- 填写配置文件。 Fill out the configuration file.
```
TELEGRAM_BOT_TOKEN=xxx
# TELEGRAM_BOT_PROXY_ADDRESS=socks5://127.0.0.1:7890
TELEGRAM_BOT_LOG_CHANNEL=-1001234567890
```

### 本地部署 / Local Deployment
- 安装依赖并运行。 Install dependencies and run.
```shell
pip3 install pdm
pdm install
pdm run python main.py
```
- 使用 PM2 守护进程。 Use PM2 to daemonize the process.
```shell
pm2 start pm2.json
pm2 monit
pm2 restart pm2.json
pm2 stop pm2.json
```

### Docker 部署 / Docker Deployment
- 使用预构建镜像。 Use pre-built image.
```shell
docker run -d --name approvebypoll --env-file .env ghcr.io/kimmyxyc/approvebypoll:main
```

## 注意 / Attention
- 机器人必须有邀请用户，封禁用户，删除消息，置顶消息的权限。
- The robot must have the permission to invite users, ban users, delete messages, and pin messages.
