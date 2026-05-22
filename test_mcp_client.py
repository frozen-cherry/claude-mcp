"""以 MCP 客户端身份连接 server.py，验证 username/screen_name 别名都可用。"""
import asyncio
import sys
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def call_tool(session: ClientSession, name: str, args: dict) -> str:
    result = await session.call_tool(name, arguments=args)
    parts = []
    for c in result.content:
        text = getattr(c, "text", None)
        if text:
            parts.append(text)
    return "\n".join(parts)


async def main():
    params = StdioServerParameters(command=sys.executable, args=["server.py"])

    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            tools = await session.list_tools()
            names = [t.name for t in tools.tools]
            print(f"Tools exposed: {names}\n")

            checks = [
                ("twitter_get_user_profile", {"params": {"username": "jun_song"}}, "username 别名"),
                ("twitter_get_user_profile", {"params": {"screen_name": "jun_song"}}, "screen_name 原名"),
                ("twitter_get_user_tweets",  {"params": {"username": "jun_song"}}, "tweets + username"),
                ("twitter_get_user_tweets",  {"params": {"screen_name": "jun_song"}}, "tweets + screen_name"),
            ]

            failed = 0
            for tool_name, args, label in checks:
                print(f"=== {label}: {tool_name} {args} ===")
                try:
                    out = await call_tool(session, tool_name, args)
                except Exception as e:
                    failed += 1
                    print(f"  FAIL  raised: {e}\n")
                    continue

                snippet = out[:200].replace("\n", " | ").encode("ascii", "replace").decode("ascii")
                # 没有 validation error 就算通过 —— API 没 key 会返回 "API 错误" 但参数已被正确解析
                if "validation error" in out.lower() or "field required" in out.lower():
                    failed += 1
                    print(f"  FAIL  validation error: {snippet}\n")
                else:
                    print(f"  PASS  {snippet}\n")

            print(f"结果: {len(checks) - failed}/{len(checks)} 通过")
            return failed


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
