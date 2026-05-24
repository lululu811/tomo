# Tomo（友）

你的本地 AI 工作伴侣，以养成宠物的形式陪伴你的开发工作。

> 核心定位：**不打扰、零侵入、有温度**。Tomo 只读取 Claude Code 本地状态文件，不拦截任何行为，将冷冰冰的工作数据转化为有温度的陪伴体验。

---

## 安装

```bash
# 克隆或进入项目目录
cd /home/chenlei/001_AI

# 安装到本地 Python 环境
pip install -e . --break-system-packages
```

---

## 快速开始

### 1. 初始化

```bash
tomo init
```

这会创建 `~/.tomo/` 目录，包含：
- `config.yaml` —— 宠物名称、性格、LLM 配置
- `tomo.db` —— SQLite 数据库（宠物状态、成长日志）

### 2. 查看状态

```bash
tomo status
```

输出示例：

```
╭────────────────────────── 🦊 Tomo ───────────────────────────╮
│ 🦊 Tomo lv.1 ⚡                                              │
│                                                               │
│ Energy:    ████████████████████ 100/100                      │
│ Satiation: ████████████████████ 100/100                      │
│ Progress:  ░░░░░░░░░░░░░░░░░░░░ 0/100 (to lv.2)              │
│                                                               │
│ Today's work: 金融分析 (80%)                                 │
│ Sessions: 149 | Total calls: 13938                           │
│                                                               │
│ Full of energy today!                                        │
╰───────────────────────────────────────────────────────────────╯
```

### 3. 添加到 Shell Prompt（可选）

```bash
# 查看集成方式
tomo install --shell=zsh

# 添加到 ~/.zshrc
echo 'RPROMPT="$(tomo prompt 2>/dev/null)"' >> ~/.zshrc
```

效果：

```
~/projects/myapp git:main >
                              [🦊 Tomo lv.12 ^_^]
```

---

## 命令一览

### 核心命令

| 命令 | 说明 |
|------|------|
| `tomo init` | 初始化配置和数据库 |
| `tomo status` | 查看宠物当前状态（含成就） |
| `tomo feed` | 喂食增加饱食度 |
| `tomo rest` | 休息恢复能量 |
| `tomo play` | 玩耍（消耗能量，改善心情） |
| `tomo prompt` | 输出紧凑字符串（用于 shell 集成） |
| `tomo growth` | 查看成长记录和经验趋势 |
| `tomo install --shell=(zsh\|bash\|fish)` | 查看 shell 集成代码 |

### 守护进程

| 命令 | 说明 |
|------|------|
| `tomo daemon start [--interval]` | 启动后台守护进程（默认 300s 同步） |
| `tomo daemon stop` | 停止守护进程 |
| `tomo daemon status` | 查看守护进程状态 |

守护进程在后台自动：
- 每 5 分钟同步 Claude Code 工作数据，自动增加经验
- 检测并解锁成就，桌面通知提醒
- 每 30 分钟自然衰减能量（-5）和饱食度（-3）
- 能量/饱食度低于 20 时弹窗提醒
- 连续工作 1 小时提醒休息
- 深夜工作主动关心

### LLM 对话

| 命令 | 说明 |
|------|------|
| `tomo chat <message>` | 与宠物对话 |

对话会根据当前宠物状态（心情、等级、能量）和人格配置生成回复，支持多轮上下文（保留最近 100 条）。

### 报表与日志

| 命令 | 说明 |
|------|------|
| `tomo report [--days]` | 工作统计报表 |
| `tomo logs [--limit]` | 成长与互动日志 |
| `tomo update [--check]` | 检查/安装更新 |
| `tomo --version` | 显示版本 |

---

## 配置

配置文件位于 `~/.tomo/config.yaml`：

```yaml
pet:
  name: "Tomo"           # 宠物名字
  avatar: "🦊"            # 头像
  personality:
    description: |
      你是一只活泼好奇的小狐狸...
    traits:
      curiosity: 0.8
      clinginess: 0.6
      wisdom: 0.4
    speech:
      style: "口语化、简短（20字以内）、用emoji"
      tone: "温暖、治愈、略带俏皮"
      forbidden:
        - "不说教"
        - "不批评主人的工作方式"
    evolution_path: "知识型"

  llm:
    provider: "ollama"   # ollama | anthropic | openai
    model: "qwen2.5:7b"
    api_key: null
    call_budget:
      daily_limit: 20
      important_only: true
```

修改配置后无需重启，下次运行命令自动生效。

---

## 成长机制

### 经验值获取

Tomo 通过观察你的 Claude Code 使用来自动获取经验：

| 行为 | 经验值 |
|------|--------|
| 每次 tool call | +1 EXP |
| 每次 Skill 调用 | +5 EXP |

### 等级公式（对数曲线，无上限）

```
level = log(exp/100 + 1) / log(1.5) + 1
```

特点：
- **前期快**：lv.1 → lv.2 约需 82 EXP
- **后期慢**：lv.10 → lv.11 约需 1157 EXP
- **无上限**：可无限成长

### 心情系统

心情由能量（energy）和饱食度（satiation）共同决定：

| 心情 | 能量 | 饱食度 |
|------|------|--------|
| ⚡ energetic | ≥80 | ≥80 |
| 😊 happy | ≥60 | ≥60 |
| 😐 neutral | ≥40 | ≥40 |
| 😴 tired | ≥20 | ≥20 |
| 💀 exhausted | <20 | <20 |

---

## 工作类型推断

Tomo **不硬编码任何目录关键词**。守护进程会根据你的 tool 使用模式，通过 LLM 智能推断工作类型：

```
工具使用记录：
- Bash: 15 次
- Read: 8 次
- Edit: 6 次

推断结果 → 软件开发
```

- 每天只推断一次，避免重复消耗 LLM 额度
- 需要至少 5 次 tool calls 才会触发推断
- 结果保存在 `daily_stats.detected_type` 中

---

## 技术栈

| 层级 | 技术 |
|------|------|
| 语言 | Python 3.10+ |
| CLI | Click |
| TUI | Rich |
| 数据库 | SQLite |
| 配置 | PyYAML |
| 通知 | plyer（跨平台桌面通知） |
| LLM | Ollama / Anthropic / OpenAI / SiliconFlow / DeepSeek |

---

## 项目结构

```
tomo/
├── pyproject.toml
├── tomo/
│   ├── __init__.py
│   ├── __main__.py       # python -m tomo
│   ├── cli.py            # CLI 入口
│   ├── config.py         # 配置管理
│   ├── daemon.py         # 后台守护进程
│   ├── db.py             # SQLite 数据库
│   ├── detector.py       # Claude Code 数据解析
│   ├── llm.py            # LLM 客户端（多 provider）
│   ├── notification.py   # 跨平台桌面通知
│   ├── pet_engine.py     # 宠物核心逻辑
│   └── templates/
│       └── default_fox.yaml
└── tests/
    ├── test_cli.py
    ├── test_config.py
    ├── test_daemon.py
    ├── test_db.py
    ├── test_detector.py
    ├── test_llm.py
    ├── test_notification.py
    └── test_pet_engine.py
```

---

## 运行测试

```bash
python3 -m pytest tests/ -v
```

---

## Roadmap

- [x] Phase 1: 核心骨架（MVP）
- [x] Phase 2: 守护进程 + 定时同步
- [x] Phase 3: LLM 集成（个性化对话）
- [ ] Phase 4: 宠物进化系统 + 成长可视化
- [ ] Phase 5: Dashboard 数据可视化
