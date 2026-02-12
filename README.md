# Twitter/X MCP Server

让 Claude 能够直接搜索推文、拉取用户时间线、分析社交数据的 MCP Server。

基于 [SocialData API](https://socialdata.tools)，按量付费，无月费。

## 功能

| Tool | 用途 |
|------|------|
| `twitter_search_tweets` | 关键词/话题搜索推文，支持高级搜索语法 |
| `twitter_get_user_profile` | 获取用户资料（粉丝数、推文数等） |
| `twitter_get_user_tweets` | 拉取用户最近推文时间线 |
| `twitter_get_tweet_detail` | 获取单条推文详情和互动数据 |
| `twitter_get_tweet_replies` | 获取推文下的回复（分析情绪用） |
| `twitter_get_community_tweets` | 获取 Twitter Community 讨论 |
| `twitter_search_users` | 搜索用户 |

## Crypto 调研场景示例

对 Claude 说：
- "搜一下推特上关于 Byreal 的讨论"
- "看看 @BybitChinese 最近发了什么"
- "搜索 #Mantle 最近的热门推文"
- "这条推文下面的评论是什么情绪"
- "对比 Byreal 和 Mantle 在推特上的讨论热度"

## 安装步骤

### 1. 注册 SocialData

前往 https://socialdata.tools 注册，获取 API Key。

计费方式：按请求量付费，没有月费。搜索推文大约 $0.0002/条，用户资料约 $0.0004/个。
日常调研级别的用量，一个月几美元就够了。

### 2. 安装依赖

```bash
cd twitter-mcp
pip install -e .
```

或者直接：

```bash
pip install "mcp[cli]" httpx pydantic
```

### 3. 设置环境变量

```bash
export SOCIALDATA_API_KEY=your_api_key_here
```

建议写入 `~/.bashrc` 或 `~/.zshrc`。

### 4. 测试运行

```bash
# 直接运行测试
python server.py

# 或用 MCP Inspector 测试
npx @modelcontextprotocol/inspector python server.py
```

### 5. 配置 Claude Desktop

编辑 Claude Desktop 配置文件：

**macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
**Windows**: `%APPDATA%\Claude\claude_desktop_config.json`
**Linux**: `~/.config/Claude/claude_desktop_config.json`

```json
{
  "mcpServers": {
    "twitter": {
      "command": "python",
      "args": ["/你的路径/twitter-mcp/server.py"],
      "env": {
        "SOCIALDATA_API_KEY": "your_api_key_here"
      }
    }
  }
}
```

如果你用 `uv`（推荐）：

```json
{
  "mcpServers": {
    "twitter": {
      "command": "uv",
      "args": ["run", "--directory", "/你的路径/twitter-mcp", "python", "server.py"],
      "env": {
        "SOCIALDATA_API_KEY": "your_api_key_here"
      }
    }
  }
}
```

### 6. 重启 Claude Desktop

配置完成后重启 Claude Desktop，你应该能在对话中看到 twitter 相关的工具了。

## 搜索语法参考

SocialData 支持完整的 Twitter 高级搜索语法：

```
# 基础搜索
bitcoin                          # 包含 bitcoin 的推文
"exact phrase"                   # 精确短语匹配

# 用户相关
from:elonmusk                   # 某用户发的推文
to:VitalikButerin               # 回复某用户的推文
@binance                        # 提及某用户

# 时间范围
since:2025-01-01                # 某日期之后
until:2025-02-01                # 某日期之前
since_time:1704067200           # UNIX 时间戳之后
until_time:1706745600           # UNIX 时间戳之前

# 互动过滤
min_faves:100                   # 至少 100 赞
min_retweets:50                 # 至少 50 转发
min_replies:10                  # 至少 10 回复

# 语言
lang:en                         # 英文
lang:zh                         # 中文

# 组合示例
#solana min_faves:50 lang:en    # 英文 Solana 推文，至少 50 赞
from:benbybit byreal            # Ben Zhou 关于 Byreal 的推文
```

## 部署到 VPS（可选）

如果你想在 VPS 上跑这个 server 供远程访问，可以改成 HTTP 模式：

```python
# 在 server.py 末尾替换为:
if __name__ == "__main__":
    mcp.run(transport="streamable-http", host="0.0.0.0", port=8080)
```

然后用 systemd 或 Docker 管理进程。

## 费用估算

| 操作 | 单价 | 调研一个项目约需 |
|------|------|-----------------|
| 搜索推文 | ~$0.0002/条 | 搜 100 条 ≈ $0.02 |
| 用户资料 | ~$0.0004/个 | 查 5 个 ≈ $0.002 |
| 用户时间线 | ~$0.0004/条 | 拉 40 条 ≈ $0.016 |

一次完整的项目调研（搜索 + 看几个账号 + 看回复）大约 $0.05-0.10。
一个月高频使用估计 $5-10 足够。

## 替代数据源

如果你不想用 SocialData，以下也可以作为数据源（需要修改 `api_request` 函数和端点）：

- **TwitterAPI.io**: $0.15/1000条，pay-as-you-go，API 风格类似
- **Xpoz**: 专为 MCP 设计，可直接用自然语言查询
- **X Official API Basic**: $100/月，10000 条/月，如果你有其他用途可以考虑
