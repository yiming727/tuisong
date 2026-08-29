#!/usr/bin/env python3
# 每日后端知识 -> 微信推送（PushPlus）
# 每天 07:00 由 GitHub Actions 调度执行：按日期轮换选题，
# 生成 Markdown 后调用 PushPlus 接口推送到微信。
#
# 本地预览：python scripts/daily_push.py --print

import argparse
import json
import os
import pathlib
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone

ROOT = pathlib.Path(__file__).resolve().parent.parent
CONTENT_FILE = ROOT / "content" / "knowledge_bank.json"
PUSHPLUS_URL = "https://www.pushplus.plus/send"
CHINA_TZ = timezone(timedelta(hours=8))


def china_now() -> datetime:
    return datetime.now(CHINA_TZ)


def load_entries() -> list[dict]:
    with open(CONTENT_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    entries = data.get("entries", [])
    if not entries:
        sys.exit("内容库为空，请检查 content/knowledge_bank.json")
    return entries


def pick_entry(entries: list[dict], day_index: int) -> dict:
    """按日期轮换：第 day_index 天取第 day_index % len(entries) 条。"""
    return entries[day_index % len(entries)]


def render(entry: dict, now: datetime, day_index: int) -> tuple[str, str]:
    title = f"后端每日知识 · {entry['category']} · {entry['title']}"
    lines = [
        f"# {now.strftime('%m月%d日')} · 每日后端知识",
        "",
        f"## 🎯 {entry['title']}",
        "",
        f"> {entry['summary']}",
        "",
        "**核心要点**",
        "",
    ]
    for point in entry["core"]:
        lines.append(f"- {point}")
    lines.append("")
    lines.append("**面试问答**")
    lines.append("")
    for i, item in enumerate(entry["qa"], 1):
        lines.append(f"**Q{i}：** {item['q']}")
        lines.append("")
        lines.append(f"**A{i}：** {item['a']}")
        lines.append("")
    if entry.get("tip"):
        lines.append("**今日提示**")
        lines.append("")
        lines.append(entry["tip"])
        lines.append("")
    lines.append("---")
    lines.append("坚持每天 10 分钟，跳槽加油 💪")
    return title, "\n".join(lines)


def send_to_wechat(token: str, title: str, content: str) -> dict:
    payload = urllib.parse.urlencode(
        {
            "token": token,
            "title": title,
            "content": content,
            "template": "markdown",
            # 强制走微信服务号渠道，以公众号消息形式出现在微信聊天列表
            "channel": "wechat",
        }
    ).encode("utf-8")
    req = urllib.request.Request(PUSHPLUS_URL, data=payload, method="POST")
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def main() -> int:
    # Windows 控制台默认 GBK，先切到 UTF-8 避免打印 emoji/中文报错
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser(description="生成每日后端知识并推送到微信")
    parser.add_argument(
        "--print",
        dest="preview",
        action="store_true",
        help="只打印内容，不发送（本地预览）",
    )
    args = parser.parse_args()

    now = china_now()
    day_index = now.toordinal()
    entries = load_entries()
    entry = pick_entry(entries, day_index)
    title, content = render(entry, now, day_index)

    print(f"今日选题（内容库共 {len(entries)} 条）：{entry['category']} - {entry['title']}")

    if args.preview:
        print(content)
        return 0

    token = os.environ.get("PUSHPLUS_TOKEN", "").strip()
    if not token:
        print("错误：未设置 PUSHPLUS_TOKEN 环境变量", file=sys.stderr)
        return 1

    try:
        result = send_to_wechat(token, title, content)
    except Exception as exc:
        print(f"推送失败：{exc}", file=sys.stderr)
        return 1

    if result.get("code") == 200:
        print(f"推送成功：{result.get('msg')}")
        return 0

    print(f"推送失败：{result}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
