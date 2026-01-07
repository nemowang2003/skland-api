# Skland API

一个功能强大且灵活的明日方舟（森空岛）数据看板工具。它既可以作为开箱即用的命令行工具使用，也可以作为基础库集成到你自己的项目中。

---

## 功能模块

本项目采用模块化设计，每个模块负责抓取并解析特定维度的游戏数据：

默认模块如下：

| 模块名               | 描述                                                               |
| :---                 | :---                                                               |
| `profile`            | 玩家个人信息：返回当前账号昵称。                                   |
| `update`             | 数据同步时间：森空岛后端最后一次同步游戏数据的时间。               |
| `checkin`            | 每日签到：完成森空岛自动签到。                                     |
| `online`             | 上次在线：账号最后一次在游戏内上线的时间。                         |
| `sanity`             | 理智监控：当前理智值、距离回满所需的剩余时间。                     |
| `routine`            | 周期任务：剿灭作战与保全派驻进度。                                 |
| `mission`            | 任务进度：每日任务与每周任务进度。                                 |
| `recruit`            | 公开招募：各栏位招募剩余时间、刷新次数及下一次刷新时间。           |
| `infrast_basic`      | 基建概览：无人机数量、疲劳干员提醒、正在进行的技能专精进度。       |

扩展模块如下：

| 模块名               | 描述                                                               |
| :---                 | :---                                                               |
| `infrast_assignment` | 基建审计（需配置 MAA 排班表）：排班表检查与菲亚梅塔位置/心情监控。 |

---

## 作为 CLI 工具使用

`dashboard` 命令提供了可以直接在终端查看的可视化看板

### 1. 基础用法

展示配置中所有账号的完整看板：

```bash
skland dashboard
```

### 2. 筛选特定账号

如果你配置了多个账号，可以通过 `--names` 指定仅查看其中几个：

```bash
skland dashboard --names 账号A,账号B
```

### 3. 自定义模块展示

通过 `--modules` 自由组合你关心的模块，并控制它们的展示顺序：

```bash
# 仅查看理智和公招状态
skland dashboard --modules sanity,recruit
```

---

## 作为库使用

本项目遵循 **“数据生产”** 与 **“视觉渲染”** 分离的原则。你可以将 `skland_api` 作为库导入，仅获取结构化的数据模型，而不依赖于 CLI 的渲染逻辑。

### 为什么作为库使用？

* **零渲染依赖**：数据抓取模块位于 `skland_api.modules`，它们不依赖 `rich` 或 `click` 等 UI 库。
* **强类型支持**：所有模块返回的都是 Python Dataclass，支持完善的类型推导。
* **按需集成**：你可以将获取的数据对接至你自己的程序中。

### 代码示例

```python
import asyncio

from skland_api import CharacterInfoLoader, SklandApi
from skland_api.modules.sanity import main as get_sanity


async def async_main():
    api = SklandApi()
    await api.token_from_phone_password("手机号", "密码")
    characters = await api.binding_list()
    for character in characters:
        character_info = await CharacterInfoLoader("名字，目前只有报错消息中使用", api, character).full_load()
        sanity = get_sanity(character_info, None)
        print(f"{sanity.sanity.current}/{sanity.sanity.total}")


asyncio.run(async_main())
```

---

## 安装

由于本项目目前尚未发布至 PyPI，请直接通过 GitHub 仓库进行安装。

> **SSH 方式**：如果你已配置 GitHub SSH Key，可将链接替换为：
> `git+ssh://git@github.com/nemowang2003/skland-api`

### 使用 [uv](https://github.com/astral-sh/uv) (推荐)

#### 1. 作为命令行工具使用 (全局安装)
安装包含所有 UI 渲染组件的完整版，安装后可直接使用 `skland` 命令：
```bash
uv tool install "git+https://github.com/nemowang2003/skland-api[cli]"
```

#### 2. 作为依赖库集成 (项目安装)

不引入 `rich` 和 `click` 等 CLI 相关依赖：

```bash
# 在你的项目目录下
uv add "git+https://github.com/nemowang2003/skland-api"
```

---

### 使用 pip

适用于传统的 Python 环境管理方式：

#### 安装完整版 (含 CLI)

```bash
pip install "skland-api[cli] @ git+https://github.com/nemowang2003/skland-api.git"
```

#### 安装轻量库版

```bash
pip install "git+https://github.com/nemowang2003/skland-api.git"
```
