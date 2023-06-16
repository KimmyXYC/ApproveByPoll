# ApproveByPoll Telegram 投票入群机器人

## 安装/Installation

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
```
- 安装依赖并运行。Install dependencies and run.
```shell
git clone https://github.com/KimmyXYC/ApproveByPoll.git
pip3 install -r requirements.txt
python3 main.py
```