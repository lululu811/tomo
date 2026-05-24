# Tomo (友)

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

**Tomo** 是你的本地 AI 工作伴侣，一只会成长、会进化、会吐槽的虚拟宠物。

> 核心定位：**不打扰、零侵入、有温度**。Tomo 只读取 Claude Code 本地状态文件，将冷冰冰的工作数据转化为有温度的陪伴体验。

```
        /\_/\
       ( o.o )     Tomo lv.5 ^_^  [成年期]
        > ^ <

Energy:    ████████████████░░░░ 80/100
Satiation: ████████████████████ 100/100
Progress:  ████████░░░░░░░░░░░░ 40/100 (to lv.6)

Today's work: 软件开发 | 心情: 😊 happy
Sessions: 12 | Total calls: 847

Ready to build something amazing!
```

## 功能亮点

- **宠物养成系统** — 从蛋开始，经历 5 个成长阶段，等级无上限
- **多物种选择** — 狐狸、猫、龙，每种有独特的 ASCII 艺术和性格
- **程序员鼓励师** — 4 种对话风格（温暖鼓励师 / 毒舌损友 / 二次元 / 默认），懂你的一切
- **代码彩蛋** — 检测 commit 关键词、TODO/FIXME、深夜 commit，宠物会吐槽
- **成就系统** — 11+ 可解锁成就，见证你的成长
- **记忆系统** — Tomo 会记住你说的话，自动提取 deadline、喜好、目标、压力状态
- **亲密度系统** — 互动提升亲密度，解锁「陌生人→认识→朋友→搭档→知己→灵魂伴侣」关系等级
- **成就分享卡片** — `tomo share` 生成精美终端卡片，一键分享解锁成就
- **GitHub Profile Badge** — `tomo badge` 生成 SVG 状态图，嵌入 README 自动更新
- **零配置 LLM** — 支持 Ollama / Anthropic / OpenAI / SiliconFlow / DeepSeek / Minimax

---

## 安装

```bash
git clone https://github.com/lululu811/tomo.git
cd tomo
pip install -e . --break-system-packages
```

**依赖：** Python 3.10+，Click, Rich, PyYAML, plyer（可选，桌面通知）

---

## 快速开始

### 1. 初始化

```bash
tomo init
```

创建 `~/.tomo/` 目录，包含配置和 SQLite 数据库。

### 2. 查看状态

```bash
tomo status
```

### 3. 选择你的宠物物种

```bash
# 查看可选物种
tomo species --list

# 切换到猫
tomo species --switch cat
```

### 4. 与宠物聊天

```bash
tomo chat "今天写代码好累"
```

### 5. 让 Tomo 记住你

```bash
# 记住一件事
tomo remember "我喜欢喝美式咖啡" --category preference

# 查看记住的内容
tomo memories

# 忘记一件事
tomo forget "我喜欢喝美式咖啡"
```

Tomo 会自动从聊天中提取信息：
- **deadline**：「明天要发布 v2.0」
- **preference**：「我喜欢 Python」
- **goal**：「我要学完 Rust」
- **stress**：「最近压力好大」
- **tech**：「我在用 React」

### 6. 分享成就

```bash
# 分享最新解锁的成就
tomo share

# 分享指定成就
tomo share first_meeting

# 输出纯文本版本（适合复制到社交平台）
tomo share first_meeting --ascii
```

### 7. 生成 GitHub Badge

```bash
# 生成 SVG badge
tomo badge

# 输出到指定路径
tomo badge --output ./tomo-badge.svg

# 获取 GitHub Actions 自动更新配置
tomo badge --github
```

### 8. 添加到 Shell Prompt（可选）

```bash
tomo install --shell=zsh
# 添加到 ~/.zshrc:
echo 'RPROMPT="$(tomo prompt 2>/dev/null)"' >> ~/.zshrc
```

---

## 命令一览

### 核心命令

| 命令 | 说明 |
|------|------|
| `tomo init` | 初始化配置和数据库 |
| `tomo status` | 查看宠物状态（含成就、彩蛋提示） |
| `tomo feed` | 喂食增加饱食度 |
| `tomo rest` | 休息恢复能量 |
| `tomo play` | 玩耍（消耗能量，改善心情） |
| `tomo chat <msg>` | 与宠物对话（4 种风格） |
| `tomo prompt` | 输出紧凑字符串（用于 shell 集成） |
| `tomo growth` | 查看成长记录和经验趋势 |
| `tomo species --list` | 列出可选物种 |
| `tomo species --switch <name>` | 切换宠物物种 |
| `tomo remember <text>` | 让 Tomo 记住一件事 |
| `tomo memories` | 查看 Tomo 记住的所有事 |
| `tomo forget <key>` | 删除一条记忆 |
| `tomo share [key] [--ascii]` | 分享成就卡片（--ascii 输出纯文本） |
| `tomo badge [--output]` | 生成 GitHub Profile SVG Badge |
| `tomo badge --github` | 输出 GitHub Actions workflow 配置 |
| `tomo install --shell=(zsh\|bash\|fish)` | 查看 shell 集成代码 |

### 守护进程

| 命令 | 说明 |
|------|------|
| `tomo daemon start [--interval]` | 启动后台守护进程（默认 300s） |
| `tomo daemon stop` | 停止守护进程 |
| `tomo daemon status` | 查看守护进程状态 |

守护进程自动：
- 每 5 分钟同步 Claude Code 数据，自动增加经验
- 检测成就并桌面通知
- 检测代码彩蛋（commit 关键词、TODO、深夜提交等）
- 每 30 分钟衰减能量/饱食度
- 能量/饱食度低于 20 时提醒
- 连续工作 1 小时提醒休息
- 深夜工作主动关心

### 报表与日志

| 命令 | 说明 |
|------|------|
| `tomo report [--days]` | 工作统计报表 |
| `tomo logs [--limit]` | 成长与互动日志 |
| `tomo update [--check]` | 检查/安装更新 |
| `tomo --version` | 显示版本 |

---

## 宠物物种

| 物种 | 性格 | 特点 |
|------|------|------|
| 🦊 **fox**（默认） | 温暖幽默 | 程序员的最佳拍档，会讲代码梗 |
| 🐱 **cat** | 傲娇毒舌 | 表面嫌弃你，实则关心你 |
| 🐉 **dragon** | 热血霸气 | 把 bug 当龙来屠，把部署当征服 |

每种物种有独立的 ASCII 艺术（5 个成长阶段）和专属对话文案。

---

## 成长机制

### 5 个成长阶段

| 阶段 | 等级要求 | 特点 |
|------|---------|------|
| 🥚 Egg | lv.1 | 刚破壳，萌萌的蛋形态 |
| 👶 Baby | lv.2+ | 学会爬行，开始认识世界 |
| 🧒 Child | lv.3+ | 掌握基础，快速成长 |
| 🧑 Teen | lv.5+ | 青春期，偶尔会写 bug |
| 🧔 Adult | lv.10+ | 完全体，资深老油条 |

### 经验获取

| 行为 | 经验值 |
|------|--------|
| 每次 tool call | +1 EXP |
| 每次 Skill 调用 | +5 EXP |

### 等级公式（对数曲线，无上限）

```
level = log(exp/100 + 1) / log(1.5) + 1
```

- **前期快**：lv.1 → lv.2 约需 82 EXP
- **后期慢**：lv.10 → lv.11 约需 1157 EXP
- **无上限**：可无限成长

### 心情系统

由能量和饱食度共同决定：

| 心情 | 条件 |
|------|------|
| ⚡ energetic | ≥80 |
| 😊 happy | ≥60 |
| 😐 neutral | ≥40 |
| 😴 tired | ≥20 |
| 💀 exhausted | <20 |

### 亲密度系统

每次互动都会增加亲密度，关系等级会解锁不同的称呼：

| 等级 | 亲密度要求 | 称呼 |
|------|-----------|------|
| 陌生人 | 0 | 初次见面 |
| 认识 | 10 | 开始熟悉 |
| 朋友 | 50 | 建立友谊 |
| 搭档 | 150 | 默契配合 |
| 知己 | 300 | 心意相通 |
| 灵魂伴侣 | 500 | 无可替代 |

**互动加分：**

| 行为 | 亲密度 |
|------|--------|
| 聊天 | +1 |
| 喂食 | +2 |
| 休息 | +1 |
| 玩耍 | +3 |
| 记住一件事 | +2 |
| 解锁成就 | +5 |

---

## LLM 对话风格

Tomo 不只是聊天机器人，它是懂程序员的**鼓励师**。

支持 4 种风格（在 `config.yaml` 中设置 `pet.personality.style`）：

| 风格 | 特点 |
|------|------|
| **encourager**（默认） | 温暖治愈，善用类比，鼓励为主 |
| **roaster** | 毒舌损友，先吐槽再关心，程序员梗密集 |
| **anime** | 二次元热血，中二口号，「代码之魂燃烧吧！」 |
| **default** | 温暖简短，像朋友一样聊天 |

对话会根据你的 coding 统计、宠物状态、解锁成就动态生成上下文。

---

## 代码彩蛋

Tomo 会偷偷观察你的工作，发现有趣模式时给你惊喜：

| 触发条件 | 宠物反应 |
|----------|---------|
| commit 含 "fix bug" | 「又修了一个bug？bug见你就跑！」 |
| commit 含 "refactor" | 「重构一时爽，一直重构一直爽！」 |
| commit 含 "wip" | 「WIP...又在挖坑了是吧？」 |
| 代码中出现 `TODO` | 「TODO +1，你的待办事项比我吃的饭还多」 |
| 代码中出现 `FIXME` | 「FIXME！这代码在向你求救呢」 |
| 深夜 commit (23:00-05:00) | 「凌晨还在commit？你是要修仙吗？」 |
| 大量删除行（重构信号） | 「删了这么多行？是在重构还是在发泄？」 |

---

## 配置

`~/.tomo/config.yaml`：

```yaml
pet:
  name: "Tomo"
  avatar: "🦊"
  species: "fox"           # fox | cat | dragon
  personality:
    description: "一只活泼好奇的小狐狸"
    style: "encourager"    # encourager | roaster | anime | default
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

  llm:
    provider: "ollama"     # ollama | anthropic | openai | siliconflow | deepseek | minimax
    model: "qwen2.5:7b"
    api_key: null
    call_budget:
      daily_limit: 20       # 0 = unlimited
      important_only: true
```

修改配置后无需重启，下次运行自动生效。

---

## 技术栈

| 层级 | 技术 |
|------|------|
| 语言 | Python 3.10+ |
| CLI | Click |
| TUI | Rich |
| 数据库 | SQLite |
| 配置 | PyYAML |
| 通知 | plyer + 平台 fallback |
| LLM | Ollama / Anthropic / OpenAI / SiliconFlow / DeepSeek / Minimax |

---

## 项目结构

```
tomo/
├── pyproject.toml
├── CHANGELOG.md
├── LICENSE
├── README.md
├── tomo/
│   ├── __init__.py
│   ├── __main__.py
│   ├── achievements.py      # 成就系统
│   ├── cli.py               # CLI 入口
│   ├── config.py            # 配置管理
│   ├── daemon.py            # 后台守护进程
│   ├── db.py                # SQLite 数据库
│   ├── detector.py          # Claude Code 数据解析
│   ├── easter_eggs.py       # 代码彩蛋检测
│   ├── exceptions.py
│   ├── llm.py               # LLM 客户端（多 provider）
│   ├── memory_manager.py    # 记忆与亲密度系统
    ├── share_card.py         # 成就分享卡片
    ├── badge_generator.py    # GitHub Badge SVG 生成
│   ├── logging_config.py
│   ├── notification.py      # 跨平台桌面通知
│   ├── pet_engine.py        # 宠物核心逻辑
│   ├── prompt_builder.py    # 系统提示词构建
│   ├── species_manager.py   # 物种模板管理
│   ├── updater.py
│   └── templates/           # 物种模板（YAML）
│       ├── fox.yaml
│       ├── cat.yaml
│       └── dragon.yaml
└── tests/
    ├── conftest.py
    ├── test_achievements.py
    ├── test_cli.py
    ├── test_config.py
    ├── test_daemon.py
    ├── test_db.py
    ├── test_detector.py
    ├── test_easter_eggs.py
    ├── test_memory.py
    ├── test_llm.py
    ├── test_notification.py
    ├── test_pet_engine.py
    ├── test_prompt_builder.py
    └── test_species.py
```

---

## 运行测试

```bash
python3 -m pytest tests/ -v
```

当前测试覆盖：200+ 测试用例
- 宠物引擎（经验、等级、心情、能量、饱食度、进化阶段）
- 配置系统（加载、验证、合并）
- 物种系统（模板加载、切换、fallback）
- 数据检测（session stats 解析）
- 数据库（CRUD、成就、聊天历史）
- 成就系统（解锁逻辑、去重）
- 彩蛋系统（commit 检测、代码模式、时间检测）
- 记忆系统（CRUD、自动提取、亲密度计算）
- 成就卡片（Rich 渲染、ASCII、HTML 导出）
- Badge 生成器（SVG、暗色/亮色主题）
- 通知系统（跨平台 fallback）
- LLM 客户端（多 provider、预算控制）
- CLI 命令（核心交互、物种命令）
- 守护进程（生命周期、同步、衰减、彩蛋集成）
- 提示词构建（风格、fallback、上下文）

---

## 许可证

[MIT](LICENSE)

---

## Roadmap

- [x] Phase 1: 核心骨架（MVP）
- [x] Phase 2: 守护进程 + 定时同步
- [x] Phase 3: LLM 集成（个性化对话）
- [x] Phase 4: 多物种系统 + 程序员鼓励师风格
- [x] Phase 5: 代码彩蛋系统
- [x] Phase 5.5: 记忆系统 + 亲密度系统
- [x] Phase 6: 成就分享卡片
- [x] Phase 7: GitHub Profile Badge
- [ ] Phase 8: Web Dashboard

### VS Code 插件

独立项目位于 `vscode-extension/` 目录。详见 [vscode-extension/README.md](vscode-extension/README.md)。
