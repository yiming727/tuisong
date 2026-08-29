#!/usr/bin/env python3
# 每日后端知识 -> 邮箱推送（PushPlus）
# 每天 07:00 由 GitHub Actions 调度执行：按日期轮换选题，
# 生成 Markdown 后调用 PushPlus 接口推送到邮箱。
#
# 本地预览：python scripts/daily_push.py --print

import argparse
import html as html_module
import json
import os
import pathlib
import re
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


def inline_md(text: str) -> str:
    """把行内 Markdown（**加粗**）转成 HTML。"""
    escaped = html_module.escape(text)
    return re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", escaped)


def md_to_html(md: str) -> str:
    """把脚本生成的 Markdown 子集转成简单 HTML，用于邮件展示。"""
    lines = md.replace("\r\n", "\n").split("\n")
    out: list[str] = []
    in_list = False

    def close_list() -> None:
        nonlocal in_list
        if in_list:
            out.append("</ul>")
            in_list = False

    for line in lines:
        stripped = line.strip()
        if not stripped:
            close_list()
            continue
        if stripped == "---":
            close_list()
            out.append("<hr>")
            continue
        if stripped.startswith("# "):
            out.append(f"<h1>{html_module.escape(stripped[2:])}</h1>")
        elif stripped.startswith("## "):
            out.append(f"<h2>{html_module.escape(stripped[3:])}</h2>")
        elif stripped.startswith("> "):
            out.append(f"<blockquote>{inline_md(stripped[2:])}</blockquote>")
        elif stripped.startswith("- "):
            if not in_list:
                out.append("<ul>")
                in_list = True
            out.append(f"<li>{inline_md(stripped[2:])}</li>")
        elif re.fullmatch(r"\*\*.+\*\*", stripped):
            out.append(f"<p><strong>{html_module.escape(stripped[2:-2])}</strong></p>")
        else:
            out.append(f"<p>{inline_md(stripped)}</p>")
    close_list()
    return "\n".join(out)


def send_email(token: str, title: str, content: str) -> dict:
    payload = urllib.parse.urlencode(
        {
            "token": token,
            "title": title,
            "content": md_to_html(content),
            "template": "html",
            # 邮件渠道：推送到 PushPlus 个人中心里绑定并验证过的接收邮箱
            "channel": "mail",
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

    test_mode = os.environ.get("TEST_MODE", "").strip().lower() in ("1", "true", "yes", "on")
    if test_mode:
        stamp = now.strftime("%Y-%m-%d %H:%M:%S")
        title = f"{title}（测试 {stamp}）"
        content = f"{content}\n\n---\n（测试消息 {stamp}，可安全重复发送）"

    print(f"今日选题（内容库共 {len(entries)} 条）：{entry['category']} - {entry['title']}")

    if args.preview:
        print(content)
        return 0

    token = os.environ.get("PUSHPLUS_TOKEN", "").strip()
    if not token:
        print("错误：未设置 PUSHPLUS_TOKEN 环境变量", file=sys.stderr)
        return 1

    try:
        result = send_email(token, title, content)
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
