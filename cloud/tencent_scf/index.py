# -*- coding: utf-8 -*-
"""腾讯云函数：每天 06:02 / 18:02 推送后端知识到邮箱（PushPlus）。

部署方式：
1. 新建事件函数（Python 3.9+），执行方法保持默认 index.main_handler。
2. 把本文件和 knowledge_bank.json 一起上传（可打成 zip 上传）。
3. 配置环境变量 PUSHPLUS_TOKEN = 你的 PushPlus token。
4. 创建两个定时触发器（北京时间）：
   每天 03:02  ->  cron: 0 2 3 * * * *
   每天 15:02  ->  cron: 0 2 15 * * * *
5. 点击「测试」运行一次验证，邮箱应能收到邮件。
"""

import html as html_module
import json
import os
import re
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone

PUSHPLUS_URL = "https://www.pushplus.plus/send"
CHINA_TZ = timezone(timedelta(hours=8))


def load_entries() -> list[dict]:
    here = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(here, "knowledge_bank.json"), "r", encoding="utf-8") as f:
        return json.load(f)["entries"]


def slot_label(now: datetime) -> str:
    return "晨读" if now.hour < 12 else "晚间回顾"


def render(entry: dict, now: datetime) -> tuple[str, str]:
    slot = slot_label(now)
    title = f"【{slot}】后端每日知识 · {entry['category']} · {entry['title']}"
    lines = [
        f"# {now.strftime('%m月%d日')} · 每日后端知识",
        "",
        f"## 🎯 {entry['title']}（{slot}）",
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
    if slot == "晨读":
        lines.append("新的一天，从 10 分钟开始 💪")
    else:
        lines.append("晚间回顾，今天也进步了一点 💪")
    return title, "\n".join(lines)


def inline_md(text: str) -> str:
    escaped = html_module.escape(text)
    return re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", escaped)


def md_to_html(md: str) -> str:
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
            "channel": "mail",
        }
    ).encode("utf-8")
    req = urllib.request.Request(PUSHPLUS_URL, data=payload, method="POST")
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def main_handler(event, context):
    now = datetime.now(CHINA_TZ)
    day_index = now.toordinal()
    entries = load_entries()
    entry = entries[day_index % len(entries)]
    title, content = render(entry, now)

    token = os.environ.get("PUSHPLUS_TOKEN", "").strip()
    if not token:
        return {"code": 500, "msg": "未配置 PUSHPLUS_TOKEN 环境变量"}

    try:
        result = send_email(token, title, content)
    except Exception as exc:
        return {"code": 500, "msg": str(exc)}
    return result
