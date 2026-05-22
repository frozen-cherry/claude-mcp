"""测试 Bug 修复：空结果 + None 字段防御性处理"""
import asyncio
import sys

# 导入被测函数
from server import format_tweet, format_user, _safe_int

passed = 0
failed = 0

def test(name, actual, expected_contains=None, should_not_raise=True):
    """简单测试工具"""
    global passed, failed
    ok = True
    if expected_contains and expected_contains not in actual:
        ok = False
    if ok:
        passed += 1
        print(f"  PASS  {name}")
    else:
        failed += 1
        print(f"  FAIL  {name}")
        print(f"        Expected to contain: {expected_contains!r}")
        print(f"        Got: {actual!r}")


def test_safe_int():
    print("\n=== _safe_int ===")
    test("None -> 0", str(_safe_int(None)), "0")
    test("123 -> 123", str(_safe_int(123)), "123")
    test("'456' -> 456", str(_safe_int("456")), "456")
    test("'abc' -> 0", str(_safe_int("abc")), "0")
    test("None with default 99", str(_safe_int(None, 99)), "99")
    test("[] -> 0", str(_safe_int([])), "0")
    test("{} -> 0", str(_safe_int({})), "0")


def test_format_tweet_empty():
    print("\n=== format_tweet: 空/None 推文 ===")
    test("None tweet", format_tweet(None), "(空推文)")
    test("Empty dict tweet", format_tweet({}), "(空推文)")


def test_format_tweet_all_none_fields():
    print("\n=== format_tweet: 所有字段为 None ===")
    tweet = {
        "user": None,
        "full_text": None,
        "text": None,
        "tweet_created_at": None,
        "retweet_count": None,
        "favorite_count": None,
        "reply_count": None,
        "quote_count": None,
        "views_count": None,
        "bookmark_count": None,
        "id_str": None,
    }
    try:
        result = format_tweet(tweet)
        test("No crash with all None fields", result, "@unknown (Unknown)")
        test("Likes shows 0", result, "0")
    except Exception as e:
        global failed
        failed += 1
        print(f"  FAIL  format_tweet with all None fields raised: {e}")


def test_format_tweet_partial_none():
    print("\n=== format_tweet: 部分字段为 None ===")
    tweet = {
        "user": {"name": "Test", "screen_name": "test_user", "followers_count": None},
        "full_text": "Hello world",
        "tweet_created_at": "2025-01-01",
        "retweet_count": 5,
        "favorite_count": None,
        "reply_count": 10,
        "quote_count": None,
        "views_count": 1000,
        "bookmark_count": None,
        "id_str": "123456",
    }
    try:
        result = format_tweet(tweet)
        test("No crash with partial None", result, "@test_user (Test)")
        test("Text preserved", result, "Hello world")
        test("Valid retweet count", result, "5")
    except Exception as e:
        global failed
        failed += 1
        print(f"  FAIL  format_tweet partial None raised: {e}")


def test_format_tweet_user_missing_fields():
    print("\n=== format_tweet: user 字典缺少字段 ===")
    tweet = {
        "user": {},
        "retweet_count": 0,
        "favorite_count": 0,
        "reply_count": 0,
        "quote_count": 0,
        "views_count": 0,
        "bookmark_count": 0,
    }
    try:
        result = format_tweet(tweet)
        test("No crash with empty user", result, "@unknown (Unknown)")
    except Exception as e:
        global failed
        failed += 1
        print(f"  FAIL  format_tweet empty user raised: {e}")


def test_format_user_empty():
    print("\n=== format_user: 空/None 用户 ===")
    test("None user", format_user(None), "(未知用户)")
    test("Empty dict user", format_user({}), "(未知用户)")


def test_format_user_all_none():
    print("\n=== format_user: 所有字段为 None ===")
    user = {
        "screen_name": None,
        "name": None,
        "description": None,
        "location": None,
        "followers_count": None,
        "friends_count": None,
        "statuses_count": None,
        "favourites_count": None,
        "created_at": None,
        "verified": None,
        "id_str": None,
    }
    try:
        result = format_user(user)
        test("No crash with all None user fields", result, "@")
        test("Followers shows 0", result, "Followers: 0")
    except Exception as e:
        global failed
        failed += 1
        print(f"  FAIL  format_user all None raised: {e}")


def test_format_tweet_normal():
    print("\n=== format_tweet: 正常数据 ===")
    tweet = {
        "user": {
            "name": "Elon Musk",
            "screen_name": "elonmusk",
            "followers_count": 150000000,
        },
        "full_text": "Mars is looking good today",
        "tweet_created_at": "2025-06-15T10:00:00Z",
        "retweet_count": 5000,
        "favorite_count": 25000,
        "reply_count": 3000,
        "quote_count": 800,
        "views_count": 10000000,
        "bookmark_count": 1200,
        "id_str": "1234567890",
    }
    result = format_tweet(tweet)
    test("Screen name", result, "@elonmusk")
    test("Name", result, "Elon Musk")
    test("Text content", result, "Mars is looking good today")
    test("Likes formatted", result, "25,000")
    test("Followers formatted", result, "150,000,000")
    test("Tweet URL", result, "https://x.com/elonmusk/status/1234567890")


def test_simulated_empty_search():
    """模拟 API 返回空列表 / null 的场景"""
    print("\n=== 模拟空搜索结果处理 ===")

    # 模拟 data.get("tweets") or [] 的行为
    # 场景1: API 返回 {"tweets": []}
    data1 = {"tweets": []}
    tweets1 = data1.get("tweets") or []
    test("Empty list -> []", str(tweets1), "[]")

    # 场景2: API 返回 {"tweets": null} (Python 中为 None)
    data2 = {"tweets": None}
    tweets2 = data2.get("tweets") or []
    test("None -> []", str(tweets2), "[]")

    # 场景3: API 返回 {} (无 tweets 键)
    data3 = {}
    tweets3 = data3.get("tweets") or []
    test("Missing key -> []", str(tweets3), "[]")

    # 验证旧写法会出问题
    tweets_old = data2.get("tweets", [])  # 返回 None！
    test("Old pattern returns None (bug)", str(tweets_old), "None")


if __name__ == "__main__":
    print("=" * 60)
    print("Twitter MCP Bug 修复测试")
    print("=" * 60)

    test_safe_int()
    test_format_tweet_empty()
    test_format_tweet_all_none_fields()
    test_format_tweet_partial_none()
    test_format_tweet_user_missing_fields()
    test_format_user_empty()
    test_format_user_all_none()
    test_format_tweet_normal()
    test_simulated_empty_search()

    print(f"\n{'=' * 60}")
    print(f"结果: {passed} passed, {failed} failed")
    print(f"{'=' * 60}")
    sys.exit(1 if failed else 0)
