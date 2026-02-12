"""
Twitter/X MCP Server - 基于 SocialData API
让 Claude 能够搜索推文、拉取用户时间线、获取互动数据

使用方法:
1. 注册 SocialData: https://socialdata.tools
2. 设置环境变量: export SOCIALDATA_API_KEY=your_key
3. 运行: python server.py
"""

import os
import json
import httpx
from datetime import datetime
from typing import Optional
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from mcp.server.fastmcp import FastMCP

# 从 .env 文件加载环境变量
load_dotenv()

# ============================================================
# 配置
# ============================================================

SOCIALDATA_API_KEY = os.environ.get("SOCIALDATA_API_KEY", "")
BASE_URL = "https://api.socialdata.tools"

mcp = FastMCP("twitter_mcp")

# ============================================================
# HTTP 客户端
# ============================================================

async def api_request(endpoint: str, params: dict = None) -> dict:
    """发送请求到 SocialData API"""
    if not SOCIALDATA_API_KEY:
        return {"error": "SOCIALDATA_API_KEY 未设置。请设置环境变量后重试。"}

    headers = {
        "Authorization": f"Bearer {SOCIALDATA_API_KEY}",
        "Accept": "application/json",
    }

    async with httpx.AsyncClient(timeout=30) as client:
        try:
            resp = await client.get(
                f"{BASE_URL}{endpoint}",
                headers=headers,
                params=params,
            )
            if resp.status_code == 402:
                return {"error": "SocialData 余额不足，请充值。"}
            if resp.status_code == 422:
                return {"error": f"参数错误: {resp.text}"}
            if resp.status_code >= 400:
                return {"error": f"API 错误 {resp.status_code}: {resp.text}"}
            return resp.json()
        except httpx.TimeoutException:
            return {"error": "请求超时，请稍后重试。"}
        except Exception as e:
            return {"error": f"请求失败: {str(e)}"}


# ============================================================
# 格式化工具
# ============================================================

def format_tweet(tweet: dict) -> str:
    """将推文格式化为可读文本"""
    user = tweet.get("user", {})
    text = tweet.get("full_text") or tweet.get("text") or ""
    created = tweet.get("tweet_created_at", "")
    
    # 互动数据
    retweets = tweet.get("retweet_count", 0)
    likes = tweet.get("favorite_count", 0)
    replies = tweet.get("reply_count", 0)
    quotes = tweet.get("quote_count", 0)
    views = tweet.get("views_count", 0)
    bookmarks = tweet.get("bookmark_count", 0)
    
    # 用户信息
    name = user.get("name", "Unknown")
    screen_name = user.get("screen_name", "unknown")
    followers = user.get("followers_count", 0)
    
    lines = [
        f"@{screen_name} ({name}) · {created}",
        f"Followers: {followers:,}",
        f"",
        text,
        f"",
        f"❤️ {likes:,}  🔁 {retweets:,}  💬 {replies:,}  🔖 {bookmarks:,}  👁️ {views:,}",
        f"Tweet ID: {tweet.get('id_str', '')}",
        f"URL: https://x.com/{screen_name}/status/{tweet.get('id_str', '')}",
    ]
    return "\n".join(lines)


def format_user(user: dict) -> str:
    """将用户资料格式化为可读文本"""
    lines = [
        f"@{user.get('screen_name', '')} ({user.get('name', '')})",
        f"Bio: {user.get('description', '')}",
        f"Location: {user.get('location', '')}",
        f"Followers: {user.get('followers_count', 0):,}",
        f"Following: {user.get('friends_count', 0):,}",
        f"Tweets: {user.get('statuses_count', 0):,}",
        f"Likes: {user.get('favourites_count', 0):,}",
        f"Created: {user.get('created_at', '')}",
        f"Verified: {user.get('verified', False)}",
        f"User ID: {user.get('id_str', '')}",
        f"URL: https://x.com/{user.get('screen_name', '')}",
    ]
    return "\n".join(lines)


# ============================================================
# MCP Tools
# ============================================================

class SearchTweetsInput(BaseModel):
    """搜索推文的参数"""
    query: str = Field(
        description="搜索关键词。支持 Twitter 高级搜索语法，例如: "
                    "'from:elonmusk' (某用户的推文), "
                    "'#bitcoin' (话题标签), "
                    "'crypto min_faves:100' (至少100赞), "
                    "'byreal lang:en' (英文推文), "
                    "'solana since:2025-01-01 until:2025-02-01' (时间范围)"
    )
    search_type: str = Field(
        default="Latest",
        description="搜索类型: 'Latest' 最新推文, 'Top' 热门推文"
    )
    max_pages: int = Field(
        default=1,
        description="拉取的页数 (每页约20条)。1-3页通常足够，避免浪费额度。",
        ge=1,
        le=5,
    )


@mcp.tool(
    name="twitter_search_tweets",
    annotations={"readOnlyHint": True, "openWorldHint": True},
)
async def search_tweets(params: SearchTweetsInput) -> str:
    """搜索推文。支持关键词、话题、用户、时间范围等高级搜索。
    
    适用场景:
    - 调研某个项目的社区讨论热度和情绪
    - 查找 KOL 对某话题的观点
    - 追踪某个事件的推特反应
    - 分析某 token/协议的社交热度
    """
    all_tweets = []
    cursor = None

    for page in range(params.max_pages):
        p = {"query": params.query, "type": params.search_type}
        if cursor:
            p["cursor"] = cursor

        data = await api_request("/twitter/search", params=p)
        if "error" in data:
            return f"搜索失败: {data['error']}"

        tweets = data.get("tweets", [])
        if not tweets:
            break

        all_tweets.extend(tweets)
        cursor = data.get("next_cursor")
        if not cursor:
            break

    if not all_tweets:
        return f"未找到关于 '{params.query}' 的推文。"

    results = [f"=== 搜索: {params.query} | 类型: {params.search_type} | 共 {len(all_tweets)} 条 ===\n"]
    for i, tweet in enumerate(all_tweets, 1):
        results.append(f"--- [{i}] ---")
        results.append(format_tweet(tweet))
        results.append("")

    return "\n".join(results)


class GetUserProfileInput(BaseModel):
    """获取用户资料的参数"""
    screen_name: str = Field(
        description="Twitter 用户名 (不含@)，如 'elonmusk', 'VitalikButerin'"
    )


@mcp.tool(
    name="twitter_get_user_profile",
    annotations={"readOnlyHint": True, "openWorldHint": True},
)
async def get_user_profile(params: GetUserProfileInput) -> str:
    """获取 Twitter 用户的详细资料，包括粉丝数、推文数等。
    
    适用场景:
    - 查看项目方/KOL 的账号信息和影响力
    - 对比不同项目的官方推特规模
    """
    data = await api_request(f"/twitter/user/{params.screen_name}")
    if "error" in data:
        return f"获取用户资料失败: {data['error']}"

    return format_user(data)


class GetUserTweetsInput(BaseModel):
    """获取用户推文的参数"""
    screen_name: str = Field(
        description="Twitter 用户名 (不含@)"
    )
    max_pages: int = Field(
        default=1,
        description="拉取页数 (每页约20条)",
        ge=1,
        le=5,
    )
    include_replies: bool = Field(
        default=False,
        description="是否包含回复。False 只看原创推文，True 包含回复。"
    )


@mcp.tool(
    name="twitter_get_user_tweets",
    annotations={"readOnlyHint": True, "openWorldHint": True},
)
async def get_user_tweets(params: GetUserTweetsInput) -> str:
    """获取某用户的最近推文时间线。
    
    适用场景:
    - 查看项目方最近在发什么
    - 追踪 KOL 的最新观点
    - 分析某人的发推频率和互动数据
    """
    # 先获取 user_id
    user_data = await api_request(f"/twitter/user/{params.screen_name}")
    if "error" in user_data:
        return f"获取用户信息失败: {user_data['error']}"

    user_id = user_data.get("id_str")
    if not user_id:
        return f"找不到用户 @{params.screen_name}"

    endpoint = f"/twitter/user/{user_id}/tweets"
    if params.include_replies:
        endpoint = f"/twitter/user/{user_id}/tweets-and-replies"

    all_tweets = []
    cursor = None

    for page in range(params.max_pages):
        p = {}
        if cursor:
            p["cursor"] = cursor

        data = await api_request(endpoint, params=p)
        if "error" in data:
            return f"获取推文失败: {data['error']}"

        tweets = data.get("tweets", [])
        if not tweets:
            break

        all_tweets.extend(tweets)
        cursor = data.get("next_cursor")
        if not cursor:
            break

    if not all_tweets:
        return f"@{params.screen_name} 没有找到推文。"

    results = [
        f"=== @{params.screen_name} 的推文 | 共 {len(all_tweets)} 条 ===\n",
        format_user(user_data),
        "\n",
    ]
    for i, tweet in enumerate(all_tweets, 1):
        results.append(f"--- [{i}] ---")
        results.append(format_tweet(tweet))
        results.append("")

    return "\n".join(results)


class GetTweetDetailInput(BaseModel):
    """获取推文详情的参数"""
    tweet_id: str = Field(
        description="推文 ID，纯数字字符串"
    )


@mcp.tool(
    name="twitter_get_tweet_detail",
    annotations={"readOnlyHint": True, "openWorldHint": True},
)
async def get_tweet_detail(params: GetTweetDetailInput) -> str:
    """获取单条推文的完整详情和互动数据。
    
    适用场景:
    - 查看某条重要公告的具体内容和互动
    - 获取推文下的讨论概况
    """
    data = await api_request(f"/twitter/tweets/{params.tweet_id}")
    if "error" in data:
        return f"获取推文详情失败: {data['error']}"

    return format_tweet(data)


class GetTweetRepliesInput(BaseModel):
    """获取推文回复的参数"""
    tweet_id: str = Field(
        description="推文 ID，纯数字字符串"
    )
    max_pages: int = Field(
        default=1,
        description="拉取页数",
        ge=1,
        le=3,
    )


@mcp.tool(
    name="twitter_get_tweet_replies",
    annotations={"readOnlyHint": True, "openWorldHint": True},
)
async def get_tweet_replies(params: GetTweetRepliesInput) -> str:
    """获取某条推文下的回复。用于分析社区对某公告/观点的反应。
    
    适用场景:
    - 分析社区对项目公告的反应和情绪
    - 查看 KOL 推文下的讨论
    """
    all_replies = []
    cursor = None

    for page in range(params.max_pages):
        p = {}
        if cursor:
            p["cursor"] = cursor

        data = await api_request(
            f"/twitter/tweets/{params.tweet_id}/comments",
            params=p,
        )
        if "error" in data:
            return f"获取回复失败: {data['error']}"

        tweets = data.get("tweets", [])
        if not tweets:
            break

        all_replies.extend(tweets)
        cursor = data.get("next_cursor")
        if not cursor:
            break

    if not all_replies:
        return f"推文 {params.tweet_id} 没有找到回复。"

    results = [f"=== 推文 {params.tweet_id} 的回复 | 共 {len(all_replies)} 条 ===\n"]
    for i, reply in enumerate(all_replies, 1):
        results.append(f"--- [{i}] ---")
        results.append(format_tweet(reply))
        results.append("")

    return "\n".join(results)


class GetCommunityTweetsInput(BaseModel):
    """获取 Twitter Community 推文的参数"""
    community_id: str = Field(
        description="Twitter Community ID，纯数字字符串"
    )
    max_pages: int = Field(
        default=1,
        description="拉取页数",
        ge=1,
        le=3,
    )


@mcp.tool(
    name="twitter_get_community_tweets",
    annotations={"readOnlyHint": True, "openWorldHint": True},
)
async def get_community_tweets(params: GetCommunityTweetsInput) -> str:
    """获取 Twitter Community 里的推文。
    
    适用场景:
    - 监控某个项目的 Community 讨论
    - 了解社区活跃度和讨论话题
    """
    all_tweets = []
    cursor = None

    for page in range(params.max_pages):
        p = {}
        if cursor:
            p["cursor"] = cursor

        data = await api_request(
            f"/twitter/community/{params.community_id}/tweets",
            params=p,
        )
        if "error" in data:
            return f"获取社区推文失败: {data['error']}"

        tweets = data.get("tweets", [])
        if not tweets:
            break

        all_tweets.extend(tweets)
        cursor = data.get("next_cursor")
        if not cursor:
            break

    if not all_tweets:
        return f"Community {params.community_id} 没有找到推文。"

    results = [f"=== Community {params.community_id} | 共 {len(all_tweets)} 条 ===\n"]
    for i, tweet in enumerate(all_tweets, 1):
        results.append(f"--- [{i}] ---")
        results.append(format_tweet(tweet))
        results.append("")

    return "\n".join(results)


class SearchUsersInput(BaseModel):
    """搜索用户的参数"""
    query: str = Field(
        description="搜索用户名或关键词"
    )


@mcp.tool(
    name="twitter_search_users",
    annotations={"readOnlyHint": True, "openWorldHint": True},
)
async def search_users(params: SearchUsersInput) -> str:
    """通过关键词搜索 Twitter 用户。
    
    适用场景:
    - 查找项目的官方推特账号
    - 搜索相关 KOL
    """
    data = await api_request(
        "/twitter/user/search",
        params={"query": params.query},
    )
    if "error" in data:
        return f"搜索用户失败: {data['error']}"

    users = data.get("users", [])
    if not users:
        return f"未找到与 '{params.query}' 相关的用户。"

    results = [f"=== 用户搜索: {params.query} | 共 {len(users)} 个 ===\n"]
    for i, user in enumerate(users, 1):
        results.append(f"--- [{i}] ---")
        results.append(format_user(user))
        results.append("")

    return "\n".join(results)


# ============================================================
# 启动服务器
# ============================================================

if __name__ == "__main__":
    mcp.run()
