"""图鉴系统：炮塔进化树 / 敌人档案 / 附魔总览。

版式参考「炮塔图鉴模拟.pdf」，但因内容量远超一屏，做了两处改动：
  - 第 1 列固定为阶级标签（一阶 / 二阶 / 三阶），不随横滚移动
  - 第 2~12 列为 11 座炮塔的进化树，画布宽度按各塔的分支数量动态计算，
    超出屏幕时横向滚动（滚轮 / 拖拽 / 方向键 / 底部滚动条）
  - 方块 = 一个进化节点，点击后在最底下的长方形框里显示详细信息
"""

import pygame

import assets
from config import (TOWER_DATA, TowerType, ENCHANTMENT_DATA, ENCHANTMENT_ORDER,
                    ENEMY_TYPES, EnemyType, SCREEN_WIDTH, SCREEN_HEIGHT,
                    FINAL_BOSS_LAYERS, FINAL_BOSS_LAYER_HEALTH, FINAL_BOSS_NAME)

# ---------------------------------------------------------------- 配色
BG = (16, 18, 24)
GRID_BG = (22, 25, 32)
PANEL_BG = (30, 34, 44)
PANEL_BORDER = (108, 138, 186)
NODE_BG = (44, 50, 64)
NODE_BG_HOVER = (64, 76, 100)
NODE_BORDER = (96, 112, 140)
SELECT = (255, 214, 92)
LINE_COLOR = (70, 86, 114)
TEXT = (232, 236, 244)
TEXT_DIM = (146, 156, 176)
TEXT_WARN = (255, 176, 92)
ACCENT = (120, 200, 255)

# ---------------------------------------------------------------- 版式
HEADER_H = 124
TREE_X = 100                      # 阶级标签列宽度，也是横滚区域左边界
TREE_TOP = HEADER_H + 6
TREE_BOTTOM = 1192
VIEW_W = SCREEN_WIDTH - TREE_X
VIEW_H = TREE_BOTTOM - TREE_TOP

ROW_CY = (200, 540, 880)          # 三阶在画布内的中心 y
NODE = 96
NODE_LABEL_SIZE = 24              # 节点下方名字字号（6 字名 144px）
PITCH = 156                       # 同列相邻节点的水平间距（容得下 6 字名）
COL_GAP = 48                      # 塔家族之间的间距
HEADER_CY = 92                    # 画布内的塔名标题 y

INFO_RECT = pygame.Rect(40, 1202, SCREEN_WIDTH - 80, 358)

ROW_LABELS = ("一阶", "二阶", "三阶")
ROW_SUBS = ("Lv 1-5", "Lv 6-10", "Lv 11-15")

_FONTS = {}


def _font(size):
    if size not in _FONTS:
        _FONTS[size] = pygame.font.Font(assets.resource_path("Minecraft.ttf"), size)
    return _FONTS[size]


def _wrap(font, text, max_w):
    """按像素宽度逐字折行（中文按字断开，保留手动换行）。"""
    lines, cur = [], ""
    for ch in text:
        if ch == "\n":
            lines.append(cur)
            cur = ""
            continue
        if cur and font.size(cur + ch)[0] > max_w:
            lines.append(cur)
            cur = ch
        else:
            cur += ch
    if cur:
        lines.append(cur)
    return lines


def _aspect_image_surface(surf, max_w, max_h):
    """按原始宽高比等比缩放到 max_w x max_h 以内，绝不拉伸。"""
    w, h = surf.get_size()
    if w <= 0 or h <= 0:
        return surf
    sc = min(max_w / w, max_h / h)
    return pygame.transform.smoothscale(surf, (max(1, int(w * sc)), max(1, int(h * sc))))


def _aspect_image(path, max_w, max_h, align="fit"):
    """从文件读原图再等比缩放。

    align="height" 时优先锁高（游戏中所有敌人都按同一高度显示，图鉴要一致）；
    宽度超限才退回按宽度约束。无论哪种都绝不拉伸。
    """
    try:
        raw = assets.load_image(path)
    except Exception:
        return None
    w, h = raw.get_size()
    if w <= 0 or h <= 0:
        return raw
    if align == "height":
        sc = max_h / h
        if w * sc > max_w:
            sc = max_w / w
    else:
        sc = min(max_w / w, max_h / h)
    return pygame.transform.smoothscale(raw, (max(1, int(w * sc)), max(1, int(h * sc))))


# ======================================================================
#  炮塔进化树数据   slot = 同层内的横向序号（支持小数用于居中）
# ======================================================================
TOWER_TREES = {
    TowerType.PHYSICAL: {
        "nodes": [
            {"key": "p1", "stage": 0, "slot": 0.0, "img": "tower/1-1-1.png",
             "name": "箭塔", "tag": "基础", "cost": 100,
             "lines": ["最便宜的物理输出，开局首选。",
                       "伤害 20 → 80，攻击间隔 1.0s → 0.7s。",
                       "射程 3 格，每升 1 级 +0.5 格。"]},
            {"key": "p2", "stage": 1, "slot": 0.0, "img": "tower/1-2-1.png",
             "name": "黄金箭塔", "tag": "二阶", "cost": -1,
             "lines": ["从这一阶开始，把【当前金币的 1%】作为额外伤害加成。",
                       "伤害 95 → 155，射程每级 +0.5 格。",
                       "金币越多越强，适合经济流后手补伤害。"]},
            {"key": "p3a", "stage": 2, "slot": 0.0, "img": "tower/1-3-1.png",
             "name": "时空撕裂之矢", "tag": "分支一 - 破甲", "cost": -1,
             "lines": ["金币 1% 伤害加成。",
                       "破甲：命中后敌人受到的所有伤害永久 +20%。",
                       "攻速 0.5s，射程每级 +0.5 格。",
                       "能给全队增伤，配合核弹 / 陨石收益极高。"]},
            {"key": "p3b", "stage": 2, "slot": 1.0, "img": "tower/1-3-2.png",
             "name": "天堂陨落长弓", "tag": "分支二 - 散射", "cost": -1,
             "lines": ["金币 1% 伤害加成。",
                       "12 方向散射，一次覆盖大半个屏幕。",
                       "攻速 0.5s，清小怪效率极高。"]},
            {"key": "p3c", "stage": 2, "slot": 2.0, "img": "tower/1-3-3.png",
             "name": "地狱升华之弩", "tag": "分支三 - 斩首", "cost": -1,
             "lines": ["发射黑色射线，随机秒杀一个敌人。",
                       "对 BOSS 改为造成 5% 最大生命伤害。",
                       "攻击间隔 (19 - Lv) 秒，满级 4s 一次。"]},
        ],
        "edges": [("p1", "p2"), ("p2", "p3a"), ("p2", "p3b"), ("p2", "p3c")],
    },
    TowerType.PRODUCTION: {
        "nodes": [
            {"key": "g1", "stage": 0, "slot": 0.0, "img": "tower/2-1-1.png",
             "name": "金矿", "tag": "基础 - 经济", "cost": 50,
             "lines": ["全局金币产量 +1/秒。",
                       "放在金矿石上时产出 +100%。",
                       "本身不攻击，不吃任何伤害类附魔。"]},
            {"key": "g2", "stage": 1, "slot": 0.0, "img": "tower/2-2-1.png",
             "name": "下界合金矿", "tag": "二阶", "cost": -1,
             "lines": ["每波额外产出 5 * 当前波数 的金币。",
                       "产量继续随等级提升。",
                       "放在金矿石上时产出 +100%。"]},
            {"key": "g3", "stage": 2, "slot": 0.0, "img": "tower/2-3-1.png",
             "name": "绿宝石块", "tag": "三阶 - 终态", "cost": -1,
             "lines": ["每波额外获得绿宝石，满级每波 3 颗。",
                       "绿宝石是购买附魔的唯一货币。",
                       "越早铺满级绿宝石块，后期附魔越齐全。"]},
        ],
        "edges": [("g1", "g2"), ("g2", "g3")],
    },
    TowerType.ICE: {
        "nodes": [
            {"key": "i1", "stage": 0, "slot": 0.0, "img": "tower/3-1-1.png",
             "name": "雪球", "tag": "基础 - 减速", "cost": 150,
             "lines": ["命中减速 50%。",
                       "伤害 5 → 25，射程 1.5 格起。",
                       "升级会降低全场温度。"]},
            {"key": "i2", "stage": 1, "slot": 0.0, "img": "tower/3-2-1.png",
             "name": "冰球", "tag": "二阶", "cost": -1,
             "lines": ["命中减速 50%，伤害 30 → 50。",
                       "Lv6 起冻结时间额外 +0.1s/级。",
                       "冻结与减速是本系唯一的控场手段。"]},
            {"key": "i3a", "stage": 2, "slot": 0.0, "img": "tower/3-3-1.png",
             "name": "冰霜炸弹", "tag": "分支一 - 爆发", "cost": -1,
             "lines": ["群体冰冻1.1 ~ 1.5s，并减速 50%，攻速 0.5s。",
                       "对冻结目标额外 +300% * (Lv-10) 温度伤害。",
                       "与冰墙组合成「冰冻三尺」附魔。"]},
            {"key": "i3b", "stage": 2, "slot": 1.0, "img": "tower/3-3-2.png",
             "name": "唤龙冰晶石", "tag": "分支二 - 召唤", "cost": -1,
             "lines": ["2% 概率召唤冰龙。",
                       "冰龙伤害 = 30 ~ 150 倍温度，并冰冻 3s。",
                       "与火龙塔、电龙塔组成「龙族传说」。"]},
            {"key": "i3c", "stage": 2, "slot": 2.0, "img": "tower/3-3-3.png",
             "name": "冰墙", "tag": "分支三 - 阻挡", "cost": -1,
             "lines": ["子弹经过的道路格 4% 生成冰墙，持续 2 ~ 4s。",
                       "冰墙阻挡地面怪物，苦力怕自爆会炸掉冰墙。",
                       "每道冰墙降低 5 度温度。"]},
        ],
        "edges": [("i1", "i2"), ("i2", "i3a"), ("i2", "i3b"), ("i2", "i3c")],
    },
    TowerType.TELEPORT: {
        "nodes": [
            {"key": "t1a", "stage": 0, "slot": 0.0, "img": "tower/4-1-1.png",
             "name": "末影珍珠", "tag": "基础 - 传送", "cost": 300,
             "lines": ["瞬移概率 1% → 5%。",
                       "伤害 5 → 25，把敌人往后传送一段距离。",
                       "任何等级都能按 R 在两个形态间切换。"]},
            {"key": "t1b", "stage": 0, "slot": 1.0, "img": "tower/4-1-2.png",
             "name": "幸运四叶草", "tag": "基础 - 随机", "cost": 300,
             "lines": ["每次命中造成 0 ~ 2 倍伤害的随机伤害。",
                       "伤害 100 → 500，攻速 1.0s → 0.7s。",
                       "下限很低、上限很高，赌狗专用。"]},
            {"key": "t2a", "stage": 1, "slot": 0.0, "img": "tower/4-2-1.png",
             "name": "末影之眼", "tag": "二阶", "cost": -1,
             "lines": ["瞬移概率继续 +1%/级。",
                       "Lv6 起获得秒杀概率，每级 +1%。",
                       "伤害 30 → 50。"]},
            {"key": "t2b", "stage": 1, "slot": 1.0, "img": "tower/4-2-2.png",
             "name": "毒马铃薯", "tag": "二阶", "cost": -1,
             "lines": ["2% 概率施加 600 ~ 1000 层中毒。",
                       "随机伤害 0 ~ 2 倍，攻速 1.0s → 0.7s。",
                       "转型当毒系叠层工具也很能打。"]},
            {"key": "t3a", "stage": 2, "slot": 0.0, "img": "tower/4-3-1.png",
             "name": "终望珍珠", "tag": "分支一 - 秒杀", "cost": -1,
             "lines": ["额外百分比伤害 (Lv-10) * 0.4%。",
                       "秒杀 / 瞬移概率进一步提升。",
                       "范围伤害 1100 → 1500。"]},
            {"key": "t3b", "stage": 2, "slot": 1.0, "img": "tower/4-3-2.png",
             "name": "无尽催化剂", "tag": "分支二 - 混乱", "cost": -1,
             "lines": ["八方向散射。",
                       "必定施加一个随机永久 debuff（中毒 / 凋零 / 破甲等）。",
                       "随机伤害 0 ~ 2 倍，攻速 0.7s → 0.5s。"]},
        ],
        "edges": [("t1a", "t2a"), ("t2a", "t3a"),
                  ("t1b", "t2b"), ("t2b", "t3b")],
    },
    TowerType.FLAME: {
        "nodes": [
            {"key": "f1", "stage": 0, "slot": 0.0, "img": "tower/5-1-1.png",
             "name": "火焰弹", "tag": "基础 - 点燃", "cost": 200,
             "lines": ["命中点燃：每秒造成等于当前温度的燃烧伤害。",
                       "伤害 20 → 80，射程 1.5 格起。",
                       "升级会提高全场温度，火系越铺越强。"]},
            {"key": "f2", "stage": 1, "slot": 0.0, "img": "tower/5-2-1.png",
             "name": "火球", "tag": "二阶", "cost": -1,
             "lines": ["燃烧持续 4 秒。",
                       "Lv6 起击晕时间 +0.1s/级。",
                       "伤害 95 → 155。"]},
            {"key": "f3a", "stage": 2, "slot": 0.0, "img": "tower/5-3-1.png",
             "name": "龙息", "tag": "分支一 - 持续", "cost": -1,
             "lines": ["龙息：每秒 (Lv-10) * 10 倍温度伤害。",
                       "击晕 0.6 ~ 1.0s，攻速 0.5s。",
                       "「余烬重生」只认龙息塔，满级可按 Q 献祭换陨石。"]},
            {"key": "f3b", "stage": 2, "slot": 1.0, "img": "tower/5-3-2.png",
             "name": "唤龙火晶石", "tag": "分支二 - 召唤", "cost": -1,
             "lines": ["5% 概率召唤火龙。",
                       "火龙伤害 = 36 ~ 180 倍温度，并附加燃烧。",
                       "击晕 0.6 ~ 1.0s。"]},
            {"key": "f3c", "stage": 2, "slot": 2.0, "img": "tower/5-3-3.png",
             "name": "星焰提灯", "tag": "分支三 - 范围", "cost": -1,
             "lines": ["冲击波打范围内全体敌人，没有弹道。",
                       "伤害 = (1600 + 温度*2) * (Lv-10)，受火系加成。",
                       "附加 4 秒燃烧（不吃任何加成），间隔 2s。",
                       "射程 2.5 ~ 3.5 格，并驱散迷雾。",
                       "3 座满级可触发「灯火通明」。"]},
        ],
        "edges": [("f1", "f2"), ("f2", "f3a"), ("f2", "f3b"), ("f2", "f3c")],
    },
    TowerType.TRIDENT: {
        "nodes": [
            {"key": "r1", "stage": 0, "slot": 0.0, "img": "tower/6-1-1.png",
             "name": "三叉戟", "tag": "基础 - 电系", "cost": 400,
             "lines": ["伤害 20 → 100，闪电伤害 50 → 250。",
                       "射程 2 格起。",
                       "升级会提高全场温度。"]},
            {"key": "r2", "stage": 1, "slot": 0.0, "img": "tower/6-2-1.png",
             "name": "黄金三叉戟", "tag": "二阶", "cost": -1,
             "lines": ["把当前金币的 1% 作为伤害加成。",
                       "伤害 120 → 180，闪电 300 → 500。",
                       "闪电会跳向附近第二个目标。"]},
            {"key": "r3a", "stage": 2, "slot": 0.0, "img": "tower/6-3-1.png",
             "name": "海渊裂空之戟", "tag": "分支一 - 十字闪电", "cost": -1,
             "lines": ["每次攻击施放十字闪电。",
                       "金币 1% 伤害加成，攻速 0.5s。",
                       "覆盖十字范围，适合直线走廊。"]},
            {"key": "r3b", "stage": 2, "slot": 1.0, "img": "tower/6-3-2.png",
             "name": "唤龙电晶石", "tag": "分支二 - 召唤", "cost": -1,
             "lines": ["5% 概率召唤电龙。",
                       "电龙伤害 = 50 ~ 250 倍温度，并麻痹 1s。",
                       "金币 1% 伤害加成。"]},
        ],
        "edges": [("r1", "r2"), ("r2", "r3a"), ("r2", "r3b")],
    },
    TowerType.WIND: {
        "nodes": [
            {"key": "w1", "stage": 0, "slot": 0.0, "img": "tower/7-1-1.png",
             "name": "风弹", "tag": "基础 - 击退", "cost": 250,
             "lines": ["命中击退 12 → 60 像素。",
                       "伤害 5 → 25。",
                       "把人往回推，等于延长所有塔的输出时间。"]},
            {"key": "w2", "stage": 1, "slot": 0.0, "img": "tower/7-2-1.png",
             "name": "重锤", "tag": "二阶", "cost": -1,
             "lines": ["击退 84 → 132 像素。",
                       "Lv6 起附带蓄风印记，印记可被引爆。",
                       "伤害 120 → 200。"]},
            {"key": "w3a", "stage": 2, "slot": 0.0, "img": "tower/7-3-1.png",
             "name": "山崩地裂之锤", "tag": "分支一 - 距离增伤", "cost": -1,
             "lines": ["伤害 275 + 8 ~ 16 / 像素飞行距离。",
                       "最大距离命中额外造成 25% 当前生命伤害。",
                       "击退 204 → 252 像素。",
                       "「致密V」再给 +5/px。"]},
            {"key": "w3b", "stage": 2, "slot": 1.0, "img": "tower/7-3-2.png",
             "name": "雷神之锤", "tag": "分支二 - 落雷", "cost": -1,
             "lines": ["子弹命中时释放竖向闪电。",
                       "闪电伤害 2000 → 10000。",
                       "与雷盾组成「共振风暴」。"]},
        ],
        "edges": [("w1", "w2"), ("w2", "w3a"), ("w2", "w3b")],
    },
    TowerType.POISON: {
        "nodes": [
            {"key": "o1a", "stage": 0, "slot": 0.0, "img": "tower/8-1-1.png",
             "name": "毒箭", "tag": "基础 - 叠毒", "cost": 175,
             "lines": ["单体叠毒，每级 +1 层。",
                       "伤害 20 → 80。",
                       "中毒永久持续、无限叠层，只吃毒系加成。"]},
            {"key": "o1b", "stage": 0, "slot": 1.0, "img": "tower/8-1-2.png",
             "name": "凋零箭", "tag": "基础 - 凋零", "cost": 175,
             "lines": ["命中施加凋零 5s。",
                       "伤害 20 → 80。",
                       "凋零按最大生命结算，专门克制高血量。",
                       "任何等级都能按 R 在两条路线间切换。"]},
            {"key": "o2a", "stage": 1, "slot": 0.0, "img": "tower/8-2-1.png",
             "name": "剧毒药水", "tag": "二阶 - 范围", "cost": -1,
             "lines": ["范围叠毒，每级 +1 层。",
                       "范围伤害 95 → 155。",
                       "一次命中给一片敌人叠毒。"]},
            {"key": "o2b", "stage": 1, "slot": 1.0, "img": "tower/8-2-2.png",
             "name": "凋零药水", "tag": "二阶 - 范围", "cost": -1,
             "lines": ["范围凋零 5s。",
                       "范围伤害 95 → 155。"]},
            {"key": "o3a", "stage": 2, "slot": 0.0, "img": "tower/8-3-1.png",
             "name": "剧毒环刃", "tag": "分支一 - 群叠", "cost": -1,
             "lines": ["范围中毒，Lv * 4 层 / 次。",
                       "范围伤害 180 → 240，攻速 0.5s。",
                       "与九头蛇毒箭组成「试毒合约」。"]},
            {"key": "o3b", "stage": 2, "slot": 1.0, "img": "tower/8-3-3.png",
             "name": "九头蛇毒箭", "tag": "分支二 - 主输出", "cost": -1,
             "lines": ["单体中毒，Lv * 9 层 / 次。",
                       "单体伤害 180 → 240，攻速 0.5s。",
                       "叠毒效率全塔最高。"]},
            {"key": "o3c", "stage": 2, "slot": 2.0, "img": "tower/8-3-2.png",
             "name": "凋零之首", "tag": "分支三 - 凋零", "cost": -1,
             "lines": ["范围凋零 12s。",
                       "范围伤害 180 → 240，攻速 0.5s。",
                       "与凋零核弹组成「凋零玫瑰」。"]},
        ],
        "edges": [("o1a", "o2a"), ("o1b", "o2b"),
                  ("o2a", "o3a"), ("o2a", "o3b"), ("o2b", "o3b"),
                  ("o2b", "o3c")],
    },
    TowerType.BOMB: {
        "nodes": [
            {"key": "b1", "stage": 0, "slot": 2.0, "img": "tower/9-1-1.png",
             "name": "TNT", "tag": "基础 - 爆炸", "cost": 500,
             "lines": ["范围爆炸伤害 100 → 500。",
                       "射程 2.2 格，攻速 2s。",
                       "升级会降低全场温度。"]},
            {"key": "b2a", "stage": 1, "slot": 0.0, "img": "tower/9-2-1.png",
             "name": "雪TNT", "tag": "二阶 - 减速", "cost": -1,
             "lines": ["范围减速 50%，持续 12s。", "伤害 600 → 1000。"]},
            {"key": "b2b", "stage": 1, "slot": 1.0, "img": "tower/9-2-2.png",
             "name": "冰TNT", "tag": "二阶 - 冰冻", "cost": -1,
             "lines": ["范围冰冻 Lv * 0.1 秒。", "伤害 600 → 1000。"]},
            {"key": "b2c", "stage": 1, "slot": 2.0, "img": "tower/9-2-3.png",
             "name": "火焰TNT", "tag": "二阶 - 燃烧", "cost": -1,
             "lines": ["范围燃烧 8s。", "伤害 600 → 1000。"]},
            {"key": "b2d", "stage": 1, "slot": 3.0, "img": "tower/9-2-4.png",
             "name": "毒TNT", "tag": "二阶 - 中毒", "cost": -1,
             "lines": ["范围中毒 Lv * 2 层。", "伤害 600 → 1000。"]},
            {"key": "b2e", "stage": 1, "slot": 4.0, "img": "tower/9-2-5.png",
             "name": "凋零TNT", "tag": "二阶 - 凋零", "cost": -1,
             "lines": ["范围凋零 5s。", "伤害 600 → 1000。"]},
            {"key": "b3a", "stage": 2, "slot": 1.0, "img": "tower/9-3-1.png",
             "name": "核弹", "tag": "三阶 - 全屏", "cost": -1,
             "lines": ["全屏伤害 (40000 + 400*温度) * (Lv-10)。",
                       "击晕 2s，附加中毒 Lv*10 层。",
                       "攻击间隔 35s"]},
            {"key": "b3b", "stage": 2, "slot": 3.0, "img": "tower/9-3-2.png",
             "name": "凋零核弹", "tag": "三阶 - 全屏", "cost": -1,
             "lines": ["全屏 (Lv-10)*2% 最大生命 + (Lv-10)*2000 固定伤害。",
                       "击晕 2s，凋零 10s。",
                       "攻击间隔 35s","与凋零之首组成「凋零玫瑰」。"]},
        ],
        # 5 个二阶分支 -> 2 个三阶终态是完整的二部图，逐条连线必然交叉，
        # 所以用"汇流母线"表示：所有二阶先并入中间的水平母线，再由母线分出到两个终态。
        "edges": [("b1", "b2a"), ("b1", "b2b"), ("b1", "b2c"),
                  ("b1", "b2d"), ("b1", "b2e")],
        "bus": {"from": ["b2a", "b2b", "b2c", "b2d", "b2e"],
                "to": ["b3a", "b3b"]},
    },
    TowerType.SHIELD: {
        "nodes": [
            {"key": "s1", "stage": 0, "slot": 0.0, "img": "tower/0-1-1.png",
             "name": "盾牌", "tag": "基础 - 护盾", "cost": 450,
             "lines": ["每 90s 给 3x3 范围内随机 1 座塔施加护盾。",
                       "护盾可挡一次苦力怕自爆。",
                       "本身不攻击，属于纯辅助。"]},
            {"key": "s2", "stage": 1, "slot": 0.0, "img": "tower/0-2-1.png",
             "name": "铁壁盾", "tag": "二阶", "cost": -1,
             "lines": ["每 60s 给 5x5 范围内随机 3 座塔施加护盾。",
                       "护盾覆盖率显著提升。"]},
            {"key": "s3a", "stage": 2, "slot": 0.0, "img": "tower/0-3-1.png",
             "name": "贪婪盾", "tag": "分支一 - 经济", "cost": -1,
             "lines": ["护盾破碎时对敌造成当前金币1%的伤害。",
                       "护盾破碎时获得 (Lv-10) * 1000 金币。",
                       "经济流的隐形收入来源。"]},
            {"key": "s3b", "stage": 2, "slot": 1.0, "img": "tower/0-3-2.png",
             "name": "寒冰盾", "tag": "分支二 - 冰爆", "cost": -1,
             "lines": ["护盾破碎时全屏 (Lv-10) * 3000 伤害。",
                       "并使所有敌人冰冻 3 秒。"]},
            {"key": "s3c", "stage": 2, "slot": 2.0, "img": "tower/0-3-3.png",
             "name": "雷盾", "tag": "分支三 - 雷爆", "cost": -1,
             "lines": ["护盾破碎时全屏 (Lv-10) * 2500 伤害。",
                       "击晕全场 1 秒并永久燃烧。",
                       "与雷神之锤组成「共振风暴」。"]},
        ],
        "edges": [("s1", "s2"), ("s2", "s3a"), ("s2", "s3b"), ("s2", "s3c")],
    },
    TowerType.TIME: {
        "nodes": [
            {"key": "c1", "stage": 0, "slot": 0.0, "img": "tower/10-1-1.png",
             "name": "时钟", "tag": "基础 - 攻速", "cost": 125,
             "lines": ["周围 3x3 范围攻速加成 Lv%。",
                       "本身不攻击，纯光环。"]},
            {"key": "c2", "stage": 1, "slot": 0.0, "img": "tower/10-2-1.png",
             "name": "加速火把", "tag": "二阶", "cost": -1,
             "lines": ["范围扩大到 5x5。",
                       "攻速加成继续随等级提升。"]},
            {"key": "c3", "stage": 2, "slot": 0.0, "img": "tower/10-3-1.png",
             "name": "时间洪流怀表", "tag": "三阶 - 终态", "cost": -1,
             "lines": ["范围扩大到 7x7，满级攻速加成 15%。",
                       "是核弹 / 凋零核弹 35s 间隔的重要补充。"]},
        ],
        "edges": [("c1", "c2"), ("c2", "c3")],
    },
    TowerType.SWORD: {
        "nodes": [
            {"key": "v1", "stage": 0, "slot": 0.0, "img": "tower/11-1-1.png",
             "name": "铁剑", "tag": "基础", "cost": 750,
             "lines": ["召唤剑身放大后持续旋转（有敌人就一直转），整圆范围伤害。",
                       "伤害 80 起，射程恒定 2.5 格，攻击间隔 1.0s。",
                       "每升 1 级 +30 伤害 / -2 帧间隔。",
                       "连击：每命中一名敌人 +1 层，伤害 x1.01^层数（999 层封顶），2.5s 没命中清零。"]},
            {"key": "v2a", "stage": 1, "slot": 0.0, "img": "tower/11-2-1.png",
             "name": "星怒", "tag": "二阶 - 星怒", "cost": -1,
             "lines": ["挥砍时额外从天而降一颗星星。",
                       "星星落在离终点最近的敌人身上，造成 80% 挥砍伤害。",
                       "范围 1 格，适合清理成群的小怪。"]},
            {"key": "v2b", "stage": 1, "slot": 1.0, "img": "tower/11-2-2.png",
             "name": "炽铁剑", "tag": "二阶 - 燃烧", "cost": -1,
             "lines": ["命中使敌人燃烧 15 秒。",
                       "每跳伤害 = 挥砍伤害的 15%。",
                       "环境温度 <= 0 或雨天时无法点燃（沿用火系机制）。"]},
            {"key": "v2c", "stage": 1, "slot": 2.0, "img": "tower/11-2-3.png",
             "name": "草剑", "tag": "二阶 - 中毒", "cost": -1,
             "lines": ["命中使敌人叠加中毒层数。",
                       "层数 = 200 + 40 x (等级 - 6)，Lv10 时 360 层。",
                       "和毒系塔的中毒共享同一套结算。"]},
            {"key": "v3a", "stage": 2, "slot": 1.0, "img": "tower/11-3-1.png",
             "name": "泰拉刃", "tag": "三阶 - 剑气", "cost": -1,
             "lines": ["挥砍时向离终点最近的敌人发射剑气。",
                       "剑气无限穿透、无衰减，对经过的每个敌人各结算一次。",
                       "剑气伤害 350 起，每级 +60。",
                       "三阶起全场索敌：敌人不进 2.5 格也会攻击。",
                       "剑气每穿透一名敌人同样叠加连击。"]},
            {"key": "v3b", "stage": 2, "slot": 2.0, "img": "tower/11-3-2.png",
             "name": "狂星之怒", "tag": "三阶 - 星雨", "cost": -1,
             "lines": ["从地图右上角一次射出 10 颗星星。",
                       "星星自动转向锁定离终点最近的敌人。",
                       "单颗伤害 180 起，每级 +30。",
                       "三阶起全场索敌：敌人不进 2.5 格也会攻击。",
                       "每颗星命中同样叠加连击。"]},
        ],
        # 二阶 3 个分支 -> 三阶 2 个终态是完整的二部图（任意二阶都能升任一三阶），
        # 逐条连线必然交叉，所以和 TNT 一样用汇流母线画。
        "edges": [("v1", "v2a"), ("v1", "v2b"), ("v1", "v2c")],
        "bus": {"from": ["v2a", "v2b", "v2c"], "to": ["v3a", "v3b"]},
    },
}


# ======================================================================
#  敌人档案
# ======================================================================
ENEMY_INFO = {
    EnemyType.NORMAL: ("普通僵尸", "基础单位", ["速度 2，基础血量 100，击杀 10 金币。",
                                          "血量随波数按 1.2^波数 增长。"]),
    EnemyType.FAST: ("骷髅射手", "高速", ["速度 3，血量 100，击杀 15 金币。",
                                   "血少但跑得快，是最容易漏掉的一类。",
                                   "白天会被阳光点燃，但在本作里不受影响。"]),
    EnemyType.TANK: ("劫掠兽", "高血", ["速度 1.5，血量 300，击杀 30 金币。",
                                  "移动慢但很肉，适合用燃烧 / 中毒磨。",
                                  "冲击时会撞开路上的障碍。"]),
    EnemyType.ELITE: ("远古守卫者", "高血", ["速度 2.5，血量 200，击杀 40 金币。",
                                     "性价比很高的击杀目标。",
                                     "会发射激光，但本作里只保留高血量设定。"]),
    EnemyType.WITHER: ("凋零", "穿墙", ["速度 2，血量 800，击杀 100 金币。",
                                    "无视路径，直接朝终点直线飞行。"]),
    EnemyType.IRON_ARMORED: ("铁甲", "减伤 60%", ["速度 1.2，血量 250，击杀 35 金币。",
                                             "未破甲时受到的所有伤害 *0.4。",
                                             "磁暴天气会直接破甲，破甲后受伤 *1.2。"]),
    EnemyType.SLIME: ("史莱姆", "分裂", ["速度 2，血量 180，击杀 25 金币。",
                                     "死亡时在原地分裂出 3 只小史莱姆。"]),
    EnemyType.SLIMELING: ("小史莱姆", "分裂产物", ["速度 3，血量 90，击杀 10 金币。",
                                            "体型只有一半，是史莱姆的残片。"]),
    EnemyType.GOLD_ARMORED: ("金甲", "减伤 70%", ["速度 1.2，血量 250，击杀 35 金币。",
                                             "未破甲时受到的所有伤害 *0.3。"]),
    EnemyType.GHOST: ("恼鬼", "穿墙", ["速度 3，血量 100，击杀 25 金币。",
                                "无视路径，直接朝终点直线飞行。",
                                "无法被地形阻挡，只能用高射速硬清。"]),
    EnemyType.DIAMOND_ARMORED: ("钻石甲", "减伤 80%", ["速度 1.2，血量 300，击杀 40 金币。",
                                                 "未破甲时受到的所有伤害 *0.2。"]),
    EnemyType.NETHERITE_ARMORED: ("下界合金甲", "减伤 90%", ["速度 1.2，血量 300，击杀 50 金币。",
                                                       "未破甲时受到的所有伤害 *0.1。",
                                                       "百分比伤害无视护甲，是对付它的正解。"]),
    EnemyType.MAGMA_CUBE: ("岩浆怪", "免疫点燃", ["速度 2.0，血量 180，击杀 25 金币。",
                                            "完全免疫燃烧与酷暑 / 火雨的点燃。",
                                            "死亡时分裂出 3 只小岩浆怪。"]),
    EnemyType.MAGMA_CUBE_SMALL: ("小岩浆怪", "免疫点燃", ["速度 3.0，血量 90，击杀 10 金币。",
                                                  "同样免疫燃烧。"]),
    EnemyType.HEROBRINE: ("Herobrine", "18 层血", ["血量固定 5,000,000，共 18 层。",
                                               "每破一层召唤援军：史莱姆+岩浆怪 / 下界合金甲 / 恼鬼+凋零。",
                                               "击杀 500 金币。"]),
    EnemyType.CREEPER: ("苦力怕", "自爆", ["速度 2，血量 100 * 1.2^波数，击杀 20 金币。",
                                      "900 帧后自爆，摧毁 3x3 内的炮塔。",
                                      "被闪电击中会变成高压苦力怕，倒计时减半。"]),
    EnemyType.CHARGED_CREEPER: ("高压苦力怕", "自爆", ["爆炸范围扩大到 5x5。",
                                                "倒计时只有普通苦力怕的一半。",
                                                "护盾可以挡下这一次自爆。"]),
    EnemyType.SPIDER: ("蜘蛛", "极速", ["速度 4，血量 100，击杀 20 金币。",
                                    "全场最快的普通单位。"]),
    EnemyType.FINAL_BOSS: (FINAL_BOSS_NAME, "最终 BOSS",
                           [f"第 100 波登场，共 {FINAL_BOSS_LAYERS} 层血。",
                            f"每层 {FINAL_BOSS_LAYER_HEALTH:,} 点，血量条只显示当前层。",
                            "会召唤小怪、释放多种指令技能并周期性「指令覆写」。"]),
}

ENEMY_ORDER = [
    EnemyType.NORMAL, EnemyType.FAST, EnemyType.SPIDER, EnemyType.TANK,
    EnemyType.ELITE, EnemyType.CREEPER, EnemyType.CHARGED_CREEPER,
    EnemyType.SLIME, EnemyType.SLIMELING, EnemyType.MAGMA_CUBE,
    EnemyType.MAGMA_CUBE_SMALL, EnemyType.GHOST, EnemyType.WITHER,
    EnemyType.IRON_ARMORED, EnemyType.GOLD_ARMORED, EnemyType.DIAMOND_ARMORED,
    EnemyType.NETHERITE_ARMORED, EnemyType.HEROBRINE, EnemyType.FINAL_BOSS,
]


# ======================================================================
#  图鉴主体
# ======================================================================
class Codex:
    TAB_TOWER, TAB_ENEMY, TAB_ENCHANT = 0, 1, 2
    TAB_NAMES = ("炮塔进化", "敌人档案", "附魔总览")

    def __init__(self, game):
        self.game = game
        self.open = False
        self.tab = self.TAB_TOWER
        self.scroll_x = 0.0
        self.scroll_y = 0.0
        self.max_scroll_x = 0.0
        self.max_scroll_y = 0.0
        self.selected = None            # (tab, key)
        self.hover = None
        self._dragging = False
        self._drag_last = 0
        self.columns = []               # 炮塔列：{ttype, name, key_label, cost, width, x, nodes}
        self.canvas_w = 0
        self._build_tower_canvas()
        self._update_scroll_limits()

    # ------------------------------------------------------------ 画布构建
    def _build_tower_canvas(self):
        self.columns = []
        x = 0
        for ttype, name, cost, key in TOWER_DATA:
            tree = TOWER_TREES.get(ttype)
            if not tree:
                continue
            span = max(n["slot"] for n in tree["nodes"]) + 1
            width = span * PITCH
            col = {"ttype": ttype, "name": name, "cost": cost,
                   "key_label": self._key_label(key), "width": width,
                   "x": x, "nodes": []}
            for n in tree["nodes"]:
                node = dict(n)
                node["cx"] = x + PITCH / 2 + n["slot"] * PITCH
                node["cy"] = ROW_CY[n["stage"]]
                col["nodes"].append(node)
            col["edges"] = tree["edges"]
            # bus 必须一起带过去，否则 _draw_tower_tree 里的 col.get("bus")
            # 永远拿到 None，TNT 的二阶->三阶会整段缺失
            col["bus"] = tree.get("bus")
            self.columns.append(col)
            x += width + COL_GAP
        self.canvas_w = max(0, x - COL_GAP)

    @staticmethod
    def _key_label(key):
        return {pygame.K_MINUS: "-"}.get(key, pygame.key.name(key).upper())

    def _node_by_key(self, key):
        for col in self.columns:
            for n in col["nodes"]:
                if n["key"] == key:
                    return col, n
        return None, None

    # ------------------------------------------------------------ 开关
    def toggle(self):
        self.open = not self.open
        if self.open:
            self.scroll_x = self.scroll_y = 0.0
            self.selected = (self.tab, self._default_key())
            pygame.mouse.set_visible(True)

    def close(self):
        self.open = False
        self._dragging = False

    def _default_key(self):
        if self.tab == self.TAB_TOWER:
            return self.columns[0]["nodes"][0]["key"]
        if self.tab == self.TAB_ENEMY:
            return ENEMY_ORDER[0]
        return ENCHANTMENT_ORDER[0]

    # ------------------------------------------------------------ 布局
    def tab_rects(self):
        rects = []
        w, h, gap = 250, 66, 16
        total = len(self.TAB_NAMES) * w + (len(self.TAB_NAMES) - 1) * gap
        x = (SCREEN_WIDTH - total) // 2
        for i in range(len(self.TAB_NAMES)):
            rects.append(pygame.Rect(x + i * (w + gap), 30, w, h))
        return rects

    def close_rect(self):
        return pygame.Rect(SCREEN_WIDTH - 106, 30, 66, 66)

    def scrollbar_rect(self):
        return pygame.Rect(TREE_X + 20, TREE_BOTTOM - 12, VIEW_W - 40, 12)

    def _vertical_only(self):
        return self.tab != self.TAB_TOWER

    def _update_scroll_limits(self):
        if self.tab == self.TAB_TOWER:
            self.max_scroll_x = max(0.0, self.canvas_w - VIEW_W)
            self.max_scroll_y = 0.0
        else:
            # 敌人 / 附魔页已优化为一屏放完，不再需要竖直滚动
            self.max_scroll_x = 0.0
            self.max_scroll_y = 0.0
        self.scroll_x = min(max(0.0, self.scroll_x), self.max_scroll_x)
        self.scroll_y = min(max(0.0, self.scroll_y), self.max_scroll_y)

    def _grid_metrics(self):
        """敌人 / 附魔页都是「图标 + 名称」的紧凑网格，一屏排满。

        返回 (rows, cols, cell_w, cell_h, gap)。
        """
        if self.tab == self.TAB_ENEMY:
            return 4, 5, 470, 244, 20       # 5 列 x 4 行，装 19 种敌人
        return 5, 6, 396, 196, 16           # 6 列 x 5 行，共 30 格装 29 个

    def node_rects(self):
        """返回 [(rect, kind, payload, selected)]，屏幕坐标。"""
        out = []
        if self.tab == self.TAB_TOWER:
            sel = self.selected[1] if self.selected and self.selected[0] == self.tab else None
            for col in self.columns:
                for n in col["nodes"]:
                    cx = n["cx"] - self.scroll_x
                    screen_x = TREE_X + cx
                    if screen_x + NODE < TREE_X - 20 or screen_x > SCREEN_WIDTH + 20:
                        continue
                    r = pygame.Rect(0, 0, NODE, NODE)
                    r.center = (int(screen_x), int(TREE_TOP + n["cy"]))
                    out.append((r, "tower", (col, n), n["key"] == sel))
        else:
            rows, cols, cw, ch, gap = self._grid_metrics()
            items = ENEMY_ORDER if self.tab == self.TAB_ENEMY else ENCHANTMENT_ORDER
            grid_w = cols * cw + (cols - 1) * gap
            grid_h = rows * ch + (rows - 1) * gap
            x0 = (SCREEN_WIDTH - grid_w) // 2
            y0 = TREE_TOP + (VIEW_H - grid_h) // 2
            sel = self.selected[1] if self.selected and self.selected[0] == self.tab else None
            for i, item in enumerate(items):
                c, r_i = i % cols, i // cols
                x = x0 + c * (cw + gap)
                y = y0 + r_i * (ch + gap)
                rect = pygame.Rect(x, y, cw, ch)
                out.append((rect, "cell", item, item == sel))
        return out

    def hit_test(self, pos):
        for rect, kind, payload, _ in self.node_rects():
            if rect.collidepoint(pos):
                return kind, payload
        return None, None

    # ------------------------------------------------------------ 事件
    def handle_event(self, event):
        self._update_scroll_limits()

        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_ESCAPE, pygame.K_c):
                self.close()
                return True
            if event.key == pygame.K_TAB:
                self.tab = (self.tab + 1) % 3
                self.scroll_x = self.scroll_y = 0.0
                self.selected = (self.tab, self._default_key())
                self._update_scroll_limits()
                return True
            if event.key in (pygame.K_LEFT, pygame.K_RIGHT, pygame.K_UP, pygame.K_DOWN):
                step = 120
                if self._vertical_only():
                    self.scroll_y += (-step if event.key == pygame.K_UP else step)
                elif event.key == pygame.K_LEFT:
                    self.scroll_x -= step
                elif event.key == pygame.K_RIGHT:
                    self.scroll_x += step
                self._update_scroll_limits()
                return True
            if event.key == pygame.K_PAGEDOWN:
                self.scroll_x += VIEW_W * 0.8
                self.scroll_y += VIEW_H * 0.8
                self._update_scroll_limits()
                return True
            if event.key == pygame.K_PAGEUP:
                self.scroll_x -= VIEW_W * 0.8
                self.scroll_y -= VIEW_H * 0.8
                self._update_scroll_limits()
                return True
            return True

        if event.type == pygame.MOUSEWHEEL:
            # 炮塔页：滚轮直接横滚；其他页：竖滚
            if self._vertical_only():
                self.scroll_y -= event.y * 90
                if event.x:
                    self.scroll_y -= event.x * 90
            else:
                dx = event.x if event.x else event.y
                self.scroll_x -= dx * 110
            self._update_scroll_limits()
            return True

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mx, my = event.pos
            for i, r in enumerate(self.tab_rects()):
                if r.collidepoint(mx, my):
                    if self.tab != i:
                        self.tab = i
                        self.scroll_x = self.scroll_y = 0.0
                        self.selected = (i, self._default_key())
                        self._update_scroll_limits()
                    return True
            if self.close_rect().collidepoint(mx, my):
                self.close()
                return True
            kind, payload = self.hit_test((mx, my))
            if kind is not None:
                if kind == "tower":
                    self.selected = (self.tab, payload[1]["key"])
                else:
                    self.selected = (self.tab, payload)
                return True
            # 空白处开始拖拽
            self._dragging = True
            self._drag_last = mx if not self._vertical_only() else my
            return True

        if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self._dragging = False
            return True

        if event.type == pygame.MOUSEMOTION:
            if self._dragging:
                if self._vertical_only():
                    self.scroll_y -= (event.pos[1] - self._drag_last)
                    self._drag_last = event.pos[1]
                else:
                    self.scroll_x -= (event.pos[0] - self._drag_last)
                    self._drag_last = event.pos[0]
                self._update_scroll_limits()
            else:
                kind, payload = self.hit_test(event.pos)
                self.hover = payload if kind else None
            return True

        if event.type == pygame.MOUSEBUTTONDOWN and event.button in (4, 5):
            return True

        return True

    # ------------------------------------------------------------ 绘制
    def draw(self, screen):
        self._update_scroll_limits()
        screen.fill(BG)
        self._draw_header(screen)
        self._draw_view(screen)
        self._draw_info(screen)

    def _draw_header(self, screen):
        title = _font(52).render("图鉴", True, TEXT)
        screen.blit(title, (56, 34))
        sub = _font(24).render("CODEX", True, TEXT_DIM)
        screen.blit(sub, (60 + title.get_width(), 58))

        for i, (r, name) in enumerate(zip(self.tab_rects(), self.TAB_NAMES)):
            active = (i == self.tab)
            pygame.draw.rect(screen, (58, 70, 96) if active else (34, 38, 50), r)
            pygame.draw.rect(screen, SELECT if active else (74, 84, 104), r, 3)
            f = _font(32)
            t = f.render(name, True, TEXT if active else TEXT_DIM)
            screen.blit(t, (r.centerx - t.get_width() // 2, r.centery - t.get_height() // 2))

        hint_text = ("C / ESC 关闭   TAB 切页   滚轮 / 拖拽 / 方向键 左右滚动"
                     if self.tab == self.TAB_TOWER
                     else "C / ESC 关闭   TAB 切页   点击图标查看详情")
        hint = _font(24).render(hint_text, True, TEXT_DIM)
        screen.blit(hint, (SCREEN_WIDTH - hint.get_width() - 140, 48))

        r = self.close_rect()
        pygame.draw.rect(screen, (70, 32, 40), r)
        pygame.draw.rect(screen, (200, 90, 100), r, 2)
        pygame.draw.line(screen, TEXT, (r.x + 20, r.y + 20), (r.right - 20, r.bottom - 20), 4)
        pygame.draw.line(screen, TEXT, (r.right - 20, r.y + 20), (r.x + 20, r.bottom - 20), 4)

        pygame.draw.line(screen, (60, 68, 84), (0, HEADER_H), (SCREEN_WIDTH, HEADER_H), 2)

    def _draw_view(self, screen):
        if self.tab == self.TAB_TOWER:
            self._draw_tower_tree(screen)
        else:
            self._draw_grid(screen)
        self._draw_scrollbar(screen)

    # ---------------------------------------------------- 炮塔树
    def _draw_tower_tree(self, screen):
        # 固定阶级标签列
        pygame.draw.rect(screen, (24, 28, 38), (0, TREE_TOP, TREE_X, VIEW_H))
        pygame.draw.line(screen, (60, 68, 84), (TREE_X - 1, TREE_TOP), (TREE_X - 1, TREE_BOTTOM), 2)
        for i, cy in enumerate(ROW_CY):
            y = TREE_TOP + cy
            box = pygame.Rect(6, y - 66, TREE_X - 16, 132)
            pygame.draw.rect(screen, (36, 42, 58), box)
            pygame.draw.rect(screen, (88, 104, 132), box, 2)
            for j, txt in enumerate((ROW_LABELS[i], ROW_SUBS[i])):
                f = _font(30 if j == 0 else 20)
                s = f.render(txt, True, TEXT if j == 0 else TEXT_DIM)
                screen.blit(s, (box.centerx - s.get_width() // 2, box.y + 34 + j * 42))

        # 裁剪到视口
        clip = pygame.Rect(TREE_X, TREE_TOP, VIEW_W, VIEW_H)
        screen.set_clip(clip)

        # 先画连线（颜色固定，不跟随选中状态高亮）
        for col in self.columns:
            by_key = {n["key"]: n for n in col["nodes"]}
            for a, b in col["edges"]:
                na, nb = by_key.get(a), by_key.get(b)
                if not na or not nb:
                    continue
                ax = TREE_X + na["cx"] - self.scroll_x
                ay = TREE_TOP + na["cy"] + NODE // 2
                bx = TREE_X + nb["cx"] - self.scroll_x
                by = TREE_TOP + nb["cy"] - NODE // 2
                if max(ax, bx) < TREE_X - 60 or min(ax, bx) > SCREEN_WIDTH + 60:
                    continue
                mid = (ay + by) // 2
                pygame.draw.line(screen, LINE_COLOR, (ax, ay), (ax, mid), 2)
                pygame.draw.line(screen, LINE_COLOR, (ax, mid), (bx, mid), 2)
                pygame.draw.line(screen, LINE_COLOR, (bx, mid), (bx, by), 2)

            # 汇流母线：多对多分支（TNT 的 5 -> 2）用它画，避免连线交叉
            bus = col.get("bus")
            if bus:
                bk = {n["key"]: n for n in col["nodes"]}
                src = [bk[k] for k in bus["from"] if k in bk]
                dst = [bk[k] for k in bus["to"] if k in bk]
                if src and dst:
                    xs = [TREE_X + n["cx"] - self.scroll_x for n in src + dst]
                    left, right = min(xs), max(xs)
                    y_src = TREE_TOP + max(n["cy"] for n in src) + NODE // 2
                    y_dst = TREE_TOP + min(n["cy"] for n in dst) - NODE // 2
                    y_bus = (y_src + y_dst) // 2
                    # 每个源节点向下接入母线
                    for n in src:
                        sx = TREE_X + n["cx"] - self.scroll_x
                        if sx < TREE_X - 60 or sx > SCREEN_WIDTH + 60:
                            continue
                        pygame.draw.line(screen, LINE_COLOR, (sx, y_src), (sx, y_bus), 2)
                    # 母线本体
                    pygame.draw.line(screen, LINE_COLOR, (left, y_bus), (right, y_bus), 2)
                    # 母线分到每个终点
                    for n in dst:
                        dx = TREE_X + n["cx"] - self.scroll_x
                        if dx < TREE_X - 60 or dx > SCREEN_WIDTH + 60:
                            continue
                        pygame.draw.line(screen, LINE_COLOR, (dx, y_bus), (dx, y_dst), 2)

        # 列标题
        for col in self.columns:
            cx = TREE_X + col["x"] + col["width"] / 2 - self.scroll_x
            if cx < TREE_X - 200 or cx > SCREEN_WIDTH + 200:
                continue
            name = _font(34).render(col["name"], True, TEXT)
            screen.blit(name, (cx - name.get_width() // 2, TREE_TOP + HEADER_CY - 20))
            key = _font(20).render(f"[{col['key_label']}]  {col['cost']} 金", True, TEXT_DIM)
            screen.blit(key, (cx - key.get_width() // 2, TREE_TOP + HEADER_CY + 22))

        # 节点
        for rect, kind, (col, node), is_sel in self.node_rects():
            self._draw_tower_node(screen, rect, node, is_sel)

        screen.set_clip(None)

    def _draw_tower_node(self, screen, rect, node, is_sel):
        hovered = (self.hover is node)
        bg = NODE_BG_HOVER if hovered else NODE_BG
        pygame.draw.rect(screen, bg, rect)
        pygame.draw.rect(screen, SELECT if is_sel else NODE_BORDER, rect, 4 if is_sel else 2)
        try:
            icon = assets.load_image(node["img"], (NODE - 16, NODE - 16))
            screen.blit(icon, (rect.x + 8, rect.y + 8))
        except Exception:
            pygame.draw.rect(screen, (70, 70, 70), rect.inflate(-16, -16))

        # 名字一直用 NODE_LABEL_SIZE，只有在真的放不下时才降一档；
        # PITCH 已按最长的 6 字名（156px）预留，正常不会触发。
        size = NODE_LABEL_SIZE
        label = _font(size).render(node["name"], True, TEXT if is_sel else TEXT_DIM)
        while label.get_width() > PITCH - 8 and size > 18:
            size -= 2
            label = _font(size).render(node["name"], True, TEXT if is_sel else TEXT_DIM)
        screen.blit(label, (rect.centerx - label.get_width() // 2, rect.bottom + 10))

    # ---------------------------------------------------- 网格（敌人 / 附魔）
    def _draw_grid(self, screen):
        clip = pygame.Rect(0, TREE_TOP, SCREEN_WIDTH, VIEW_H)
        screen.set_clip(clip)
        for rect, kind, item, is_sel in self.node_rects():
            hovered = (item == self.hover)
            pygame.draw.rect(screen, NODE_BG_HOVER if hovered else NODE_BG, rect)
            pygame.draw.rect(screen, SELECT if is_sel else NODE_BORDER, rect, 4 if is_sel else 2)
            if self.tab == self.TAB_ENEMY:
                self._draw_enemy_cell(screen, rect, item, is_sel)
            else:
                self._draw_enchant_cell(screen, rect, item, is_sel)
        screen.set_clip(None)

    def _draw_enemy_cell(self, screen, rect, etype, is_sel):
        """图标按原始宽高比缩放（不能拉成正方形，否则骷髅/劫掠兽全变胖）。"""
        name, tag, _ = ENEMY_INFO.get(etype, (etype.name, "", []))
        img_path = "enemy/" + ENEMY_TYPES[etype.name]["image"]

        box = pygame.Rect(0, 0, rect.width - 40, rect.height - 78)
        box.midtop = (rect.centerx, rect.y + 16)
        pygame.draw.rect(screen, (22, 26, 34), box)
        img = _aspect_image(img_path, box.width - 16, box.height - 16, align="height")
        if img:
            screen.blit(img, (box.centerx - img.get_width() // 2,
                              box.centery - img.get_height() // 2))
        else:
            pygame.draw.rect(screen, (60, 60, 60), box.inflate(-16, -16))

        f1 = _font(30)
        label = f1.render(name, True, SELECT if is_sel else TEXT)
        if label.get_width() > rect.width - 20:
            label = _font(25).render(name, True, SELECT if is_sel else TEXT)
        screen.blit(label, (rect.centerx - label.get_width() // 2, box.bottom + 10))

        f2 = _font(21)
        sub = f2.render(tag, True, ACCENT)
        screen.blit(sub, (rect.centerx - sub.get_width() // 2, box.bottom + 48))

    def _draw_enchant_cell(self, screen, rect, ench, is_sel):
        """附魔页只显示图标 + 名称（名称在图标下方），详情点击后看底部信息框。"""
        data = ENCHANTMENT_DATA[ench]
        icon = assets.enchantment_icons_raw.get(ench)
        box = pygame.Rect(0, 0, rect.width - 30, rect.height - 74)
        box.midtop = (rect.centerx, rect.y + 14)
        pygame.draw.rect(screen, (22, 26, 34), box)
        if icon:
            img = _aspect_image_surface(icon, box.width - 18, box.height - 18)
            screen.blit(img, (box.centerx - img.get_width() // 2,
                              box.centery - img.get_height() // 2))
        else:
            pygame.draw.rect(screen, (70, 70, 70), box.inflate(-18, -18))

        size = 26 if len(data["name"]) <= 5 else 22
        label = _font(size).render(data["name"], True, SELECT if is_sel else TEXT)
        if label.get_width() > rect.width - 12:
            label = _font(19).render(data["name"], True, SELECT if is_sel else TEXT)
        screen.blit(label, (rect.centerx - label.get_width() // 2, box.bottom + 12))

    # ---------------------------------------------------- 滚动条
    def _draw_scrollbar(self, screen):
        # 敌人 / 附魔页已是一屏排满，不需要滚动条
        if self._vertical_only():
            return

        bar = self.scrollbar_rect()
        pygame.draw.rect(screen, (34, 40, 52), bar)
        total = self.canvas_w
        if total <= 0:
            return
        frac = VIEW_W / total
        w = max(80, int(bar.width * frac))
        x = bar.x + int((bar.width - w) * (self.scroll_x / self.max_scroll_x)) if self.max_scroll_x > 0 else bar.x
        pygame.draw.rect(screen, (120, 154, 208), (x, bar.y, w, bar.height))
        # 视口内的塔名提示
        tip = _font(20).render(
            f"画布 {int(total)}px / 视口 {VIEW_W}px    ← 左右滚动查看全部 11 座炮塔 →",
            True, (110, 122, 146))
        screen.blit(tip, (TREE_X + 24, TREE_BOTTOM - 46))

    # ---------------------------------------------------- 底部信息框
    def _draw_info(self, screen):
        pygame.draw.rect(screen, PANEL_BG, INFO_RECT)
        pygame.draw.rect(screen, PANEL_BORDER, INFO_RECT, 3)

        if not self.selected:
            return
        tab, key = self.selected
        if tab == self.TAB_TOWER:
            self._info_tower(screen, key)
        elif tab == self.TAB_ENEMY:
            self._info_enemy(screen, key)
        else:
            self._info_enchant(screen, key)

    def _info_head(self, screen, icon_surface, title, tag, extra):
        box = pygame.Rect(INFO_RECT.x + 24, INFO_RECT.y + 24, 130, 130)
        pygame.draw.rect(screen, (22, 26, 34), box)
        pygame.draw.rect(screen, (86, 100, 128), box, 2)
        if icon_surface:
            img = _aspect_image_surface(icon_surface, box.width - 12, box.height - 12)
            screen.blit(img, (box.centerx - img.get_width() // 2,
                              box.centery - img.get_height() // 2))

        tx = box.right + 26
        # 长名字（如 Herobrine / 终焉-奥米伽）自动降字号，避免压到右侧描述区
        size = 44
        t = _font(size).render(title, True, TEXT)
        while t.get_width() > 320 and size > 26:
            size -= 2
            t = _font(size).render(title, True, TEXT)
        screen.blit(t, (tx, INFO_RECT.y + 30))
        if tag:
            s = _font(24).render(tag, True, SELECT)
            screen.blit(s, (tx, INFO_RECT.y + 86))
        if extra:
            s = _font(22).render(extra, True, TEXT_DIM)
            screen.blit(s, (tx, INFO_RECT.y + 122))
        return tx

    def _info_tower(self, screen, key):
        col, node = self._node_by_key(key)
        if not node:
            return
        head_icon = None
        try:
            head_icon = assets.load_image(node["img"])
        except Exception:
            pass
        stage = ROW_LABELS[node["stage"]]
        extra = f"{stage}   {col['name']}"
        if col["cost"] > 0:
            extra += f"   建造 {col['cost']} 金"
        self._info_head(screen, head_icon, node["name"], node["tag"], extra)

        # 描述：右下区域折行排布（两栏）
        body_x = INFO_RECT.x + 480
        body_w = INFO_RECT.right - 40 - body_x
        f = _font(26)
        lines = []
        for ln in node["lines"]:
            lines.extend(_wrap(f, ln, body_w // 2 - 30))
        half = (len(lines) + 1) // 2
        col1, col2 = lines[:half], lines[half:]
        for i, ln in enumerate(col1):
            screen.blit(f.render(ln, True, TEXT), (body_x, INFO_RECT.y + 34 + i * 38))
        for i, ln in enumerate(col2):
            screen.blit(f.render(ln, True, TEXT), (body_x + body_w // 2, INFO_RECT.y + 34 + i * 38))

        tip = _font(20).render("点击方块查看其他节点", True, (108, 118, 140))
        screen.blit(tip, (INFO_RECT.right - tip.get_width() - 26, INFO_RECT.bottom - 34))

    def _info_enemy(self, screen, etype):
        name, tag, lines = ENEMY_INFO.get(etype, (etype.name, "", []))
        img = None
        try:
            img = assets.load_image("enemy/" + ENEMY_TYPES[etype.name]["image"])
        except Exception:
            pass
        cfg = ENEMY_TYPES[etype.name]
        extra = f"血量 {cfg['health']:,}   速度 {cfg['speed']}   赏金 {cfg['reward']}"
        self._info_head(screen, img, name, tag, extra)

        body_x = INFO_RECT.x + 480
        f = _font(27)
        y = INFO_RECT.y + 34
        drawn = 0
        for ln in lines:
            for row in _wrap(f, ln, INFO_RECT.right - 40 - body_x):
                if drawn >= 6:
                    break
                screen.blit(f.render(row, True, TEXT), (body_x, y + drawn * 40))
                drawn += 1
        tip = _font(20).render("血量随波数 *1.2^波数 增长" if etype not in (
            EnemyType.HEROBRINE, EnemyType.FINAL_BOSS) else "固定血量，不随波数增长",
            True, (108, 118, 140))
        screen.blit(tip, (INFO_RECT.right - tip.get_width() - 26, INFO_RECT.bottom - 34))

    def _info_enchant(self, screen, ench):
        data = ENCHANTMENT_DATA[ench]
        img = assets.enchantment_icons_raw.get(ench)
        self._info_head(screen, img, data["name"], f"价格 {data['cost']} 绿宝石", "")
        body_x = INFO_RECT.x + 480
        f = _font(27)
        y = INFO_RECT.y + 40
        for i, row in enumerate(_wrap(f, data["desc"], INFO_RECT.right - 40 - body_x)):
            if i >= 6:
                break
            screen.blit(f.render(row, True, TEXT), (body_x, y + i * 40))