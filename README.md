# 每日后端知识邮箱推送

每天 06:02 和 18:02（北京时间）各推送一份「后端面试知识」到你的邮箱，
早晨为「晨读」版、傍晚为「晚间回顾」版。
纯云端运行，电脑关机也不影响，适合 Java 后端准备跳槽、通勤 10 分钟阅读。

## 工作原理

```text
GitHub Actions（每天 06:02 / 18:02 云端触发）
        │
        ▼
Python 脚本按日期从 content/knowledge_bank.json 选题
        │
        ▼
生成 Markdown（核心要点 + 面试问答 + 今日提示）
        │
        ▼
调用 PushPlus 接口 → 推送到你的邮箱
```

## 目录结构

```text
.
├── .github/workflows/daily-push.yml   # 定时任务：每天 06:02 / 18:02 触发
├── scripts/daily_push.py              # 选题、生成内容、调用邮箱推送
├── content/knowledge_bank.json        # 知识库（目前 18 个主题，可扩充）
└── README.md
```

## 一次性配置（约 5 分钟）

### 第 1 步：获取 PushPlus Token

1. 打开 <https://www.pushplus.plus/>，用微信扫码登录。
2. 进入个人中心，在「修改个人资料」里填写你的接收邮箱（建议 QQ 邮箱），收信并点击验证链接完成验证。
3. 进入「一对一推送」页面，复制你的 token（首次获取可能有 1 元验证费）。

### 第 2 步：创建 GitHub 仓库并推送代码

1. 在 GitHub 新建一个仓库（Public 或 Private 均可）。
2. 在项目目录执行：

```bash
git init
git add .
git commit -m "init: daily backend knowledge push"
git branch -M main
git remote add origin https://github.com/<你的用户名>/<仓库名>.git
git push -u origin main
```

### 第 3 步：配置 Secret

在 GitHub 仓库页面：`Settings → Secrets and variables → Actions → New repository secret`，添加：

```text
Name:  PUSHPLUS_TOKEN
Value: 第 1 步复制的 token
```

### 第 4 步：手动触发一次验证

在仓库 `Actions` 页面选择 `Daily Backend Knowledge Push` 工作流，点击 `Run workflow`。
运行成功后，你的邮箱（含垃圾箱）应能收到今天的知识卡片。

## 时间与频率

- 每天 06:02（晨读）和 18:02（晚间回顾）北京时间各推送一次，无需电脑开机。
- 想改时间：编辑 `.github/workflows/daily-push.yml` 里的 cron（UTC 时间，北京时间 = UTC + 8）。
- 想暂停：在 GitHub Actions 页面把工作流禁用即可。

## 本地预览（可选）

```bash
python scripts/daily_push.py --print
```

只打印今天的内容，不发送。

## 常用维护

- **扩充内容**：往 `content/knowledge_bank.json` 的 `entries` 里追加条目即可，脚本按日期轮换，加得越多重复周期越长。
- **换推送渠道**（如换回微信服务号）：把 `scripts/daily_push.py` 里请求的 `channel` 从 `mail` 改为 `wechat` 即可，同时需在 PushPlus 绑定对应渠道。

## 常见问题

- **需要电脑一直开着吗？** 不需要。任务在 GitHub 云服务器上运行，与你的电脑无关。
- **免费吗？** GitHub Actions 免费额度对公开仓库无限制，私有仓库每月 2000 分钟，本任务每天约 1 分钟，完全够用。
- **收不到邮件？** 先确认已在 PushPlus 个人中心填写并验证接收邮箱；再检查邮箱垃圾箱；发送失败时工作流会标红，可在 Actions 页面查看日志。
- **内容会重复吗？** 知识库共 18 条，约 2.5 周轮换一次；追加新条目后周期变长，也可定期更新旧条目。
