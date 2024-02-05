# ApproveByPoll / Telegram 投票入群机器人

## 安装 / Installation

- 下载源码。Download the code.
```shell
git clone https://github.com/KimmyXYC/ApproveByPoll.git
cd ApproveByPoll
```

- 复制配置文件。Copy configuration file.
```shell
cp Config/app_exp.toml Config/app.toml
```

- 填写配置文件。Fill out the configuration file.
```toml
[bot]
master = [100, 200]
botToken = 'key' # Required, Bot Token


[proxy]
status = false
url = "socks5://127.0.0.1:7890"

[log]
channel = -100123456789
```

### 本地 / Local
- 安装依赖并运行。Install dependencies and run.
```shell
pip3 install -r requirements.txt
python3 main.py
```

### Docker
- 使用预构建镜像。Use pre-built image.
```shell
docker run -d --name approvebypoll -v $(pwd)/Config:/app/Config ghcr.io/kimmyxyc/approvebypoll:main
```

## 注意 / Attention
- 机器人必须有邀请用户，封禁用户，删除消息，置顶消息的权限。The robot must have the permission to invite users, ban users, delete messages, and pin messages.
