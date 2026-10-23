# 我的世界塔防战（Minecraft Tower Defense）

一款用 Python + pygame 写的像素风塔防。12 种炮塔、三阶进化树、36 种附魔、动态天气与温度系统、100 波敌人，以及一个四阶段最终 BOSS。

**非商业同人作品，免费下载，无内购无广告。**

---

## 下载

[**⬇ 下载 MCTD-v1.0.0-win64.exe**](https://github.com/printf6666/Minecraft-Tower-Defense/releases/latest)

> 国内访问 GitHub 慢的话，可以用蓝奏云镜像：**（待填）**

解压后双击即玩，免安装。

### 系统要求

| 项目 | 要求 |
|---|---|
| 系统 | Windows 10 / 11，64 位 |
| 显卡 | 支持 OpenGL 2.0 及以上 |
| 分辨率 | 游戏按 **2560×1600** 设计。1080p 屏幕会自动等比缩放，上下留黑边，属正常现象 |
| 硬盘 | 约 50 MB |

### 关于杀毒软件误报

打包用的是 PyInstaller，**没有购买代码签名证书**，所以 Windows Defender / 360 有一定概率报「未知程序」。这不是病毒 —— 你可以：

- 把 exe 加入信任
- 或者直接用源码跑：`pip install pygame`，然后 `python main.py`
- 校验文件哈希（SHA256 见 Release 页面）

---

## 截图

> （待补：主菜单 / 中后期战场 / 图鉴 / 最终 BOSS）

---

## 怎么玩

| 操作 | 说明 |
|---|---|
| `0`~`9`、`X` | 选择要建造的炮塔 |
| 左键 | 在空地上建造；点已有炮塔可查看信息 |
| `U` | 升级选中的炮塔 |
| `E` | 连升 5 级 |
| `R` | 切换炮塔分支（Lv6、Lv11 两个节点） |
| `S` | 出售选中的炮塔 |
| `C` | 打开图鉴 |
| `TAB` | 伤害统计 |
| `ESC` | 暂停 |

**新手建议**：先看「图鉴（`C`）→ 炮塔」页的进化树，了解每条分支的定位再花钱。金币主要来自击杀和「金矿」塔，前期别把钱全砸在一座塔上。

---

## 关于这个项目

- **技术栈**：Python 3 + pygame 2.6，无第三方引擎
- **代码量**：约 9300 行 Python
- **设计文档**：[docs/DESIGN.md](docs/DESIGN.md) —— 包含 12 塔尔数值表、天气/温度机制、附魔清单、最终 BOSS 的四阶段设计与完整实现映射

## 授权

- **代码**（`.py`）：MIT，见 [LICENSE](LICENSE)
- **美术与音频素材**：版权归 **Mojang Studios / C418** 所有，本项目仅为非商业同人使用，**不适用 MIT 协议**，详见 [NOTICE.md](NOTICE.md)

本项目与 Mojang / Microsoft 无任何关联，未获其授权或背书。

---

## 反馈

发现 bug 或有建议，欢迎提 [Issue](https://github.com/printf6666/Minecraft-Tower-Defense/issues)。如果遇到闪退，存档目录下的 `crash.log` 会记录详细堆栈，附上它我能更快定位。