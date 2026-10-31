from enum import Enum
import pygame

class TowerType(Enum):
    SHIELD = 0
    PHYSICAL = 1
    PRODUCTION = 2
    ICE = 3
    TELEPORT = 4
    FLAME = 5
    TRIDENT = 6
    WIND = 7
    POISON = 8
    BOMB = 9
    TIME = 10

TOWER_DATA = [
    (TowerType.PHYSICAL,   "物理", 100,  pygame.K_1),
    (TowerType.PRODUCTION, "金矿", 50,   pygame.K_2),
    (TowerType.ICE,        "冰系", 150,  pygame.K_3),
    (TowerType.TELEPORT,   "传送", 300,  pygame.K_4),
    (TowerType.FLAME,      "火系", 200,  pygame.K_5),
    (TowerType.TRIDENT,    "三叉", 400,  pygame.K_6),
    (TowerType.WIND,       "风系", 250,  pygame.K_7),
    (TowerType.POISON,     "毒系", 175,  pygame.K_8),
    (TowerType.BOMB,       "TNT", 500,  pygame.K_9),
    (TowerType.SHIELD,     "盾塔", 225,  pygame.K_0),
    (TowerType.TIME,       "时间", 125,  pygame.K_MINUS)
    ]

SCREEN_WIDTH = 2560
SCREEN_HEIGHT = 1600
TILE_SIZE = 128
GRID_WIDTH = 16
GRID_HEIGHT = 10

INFO_BORDER_X = 2048
INFO_BORDER_Y = 512
INFO_BORDER_SIZE = 512
INFO_BORDER_WIDTH = 3
INFO_BORDER_COLOR = (255, 255, 255)
INFO_PADDING = 20

RESTART_BTN_X = INFO_BORDER_X
RESTART_BTN_Y = INFO_BORDER_Y + INFO_BORDER_SIZE + 20
RESTART_BTN_WIDTH = 256
RESTART_BTN_HEIGHT = 60
RESTART_BTN_COLOR = (80, 80, 80)

EXIT_BTN_X = RESTART_BTN_X + RESTART_BTN_WIDTH
EXIT_BTN_Y = RESTART_BTN_Y
EXIT_BTN_WIDTH = SCREEN_WIDTH - EXIT_BTN_X
EXIT_BTN_HEIGHT = 60
EXIT_BTN_COLOR = (120, 30, 30)

# 「重新开始」二次确认的有效帧数（60fps 下约 3 秒）。
# 主菜单右下角曾有一块 512x60 的隐形热区，点一下就无声删档；
# 即便修掉热区，游戏内误点「重新开始」仍然是不可撤销的丢档操作，
# 所以要求连点两次、且两次间隔不能超过这个窗口。
CONFIRM_RESET_FRAMES = 180

# 右上角提示面板（最终BOSS「指令覆写」提示用）
TOP_PANEL_X = 2050
TOP_PANEL_Y = 10
TOP_PANEL_WIDTH = 460
TOP_PANEL_HEIGHT = 60

# 局内「伤害统计」按钮（右侧操作说明下方、底部炮塔栏上方）
STATS_BTN_X = INFO_BORDER_X
STATS_BTN_Y = SCREEN_HEIGHT - 128 - 80
STATS_BTN_WIDTH = INFO_BORDER_SIZE
STATS_BTN_HEIGHT = 54
STATS_BTN_COLOR = (52, 52, 74)
STATS_BTN_BORDER = (150, 150, 210)

WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
RED = (255, 0, 0)
GREEN = (0, 255, 0)
BLUE = (0, 0, 255)
YELLOW = (255, 255, 0)
GRAY = (100, 100, 100)
LIGHT_BLUE = (100, 100, 255)
ICE_BLUE = (150, 200, 255)
BROWN = (139, 69, 19)
GOLD = (255, 215, 0)
ORANGE = (255, 165, 0)
ELECTRIC_PURPLE = (178, 0, 255)
PURPLE = (128, 0, 128)
TELEPORT_PURPLE = (138, 43, 226)
MINT = (152, 255, 152)


class GameState(Enum):
    MENU = 0
    PLAYING = 1
    WAVE_PREPARATION = 2
    GAME_OVER = 3
    VICTORY = 4
    PAUSED = 5
    SHOP = 6

class Enchantment(Enum):
    BALANCED = 0
    PHYSICAL = 1
    ICE = 2
    FLAME = 3
    TRIDENT = 4
    WIND = 5
    POISON = 6
    BOMB = 7
    DENSE = 8
    WIND_BURST = 9
    POISON_CONTRACT = 10
    BURN = 11
    BLAZE_POWDER = 12
    FROZEN_DEEP = 13
    DRAGON_LEGEND = 14
    ENDLESS_GREED = 15
    RAIN_FIRE = 16
    WITHER_ROSE = 17
    LAVA = 18
    TELESCOPE = 19
    # 火矢已删除：枚举值 20 保留只为旧存档反序列化不炸，读档时会被过滤掉
    FIRE_ARROW = 20
    PULSE_SHIELD = 21
    RESONANCE_STORM = 22
    EMBER_REBIRTH = 23
    WAX = 24
    INFINITY_GAUNTLET = 25
    UNSTABLE_CRYSTAL = 26
    POWER_V = 27
    LANTERN = 28
    MASTERPIECE = 29

ENCHANTMENT_DATA = {
    Enchantment.BALANCED: {"name": "均衡强化", "desc": "所有伤害+5%", "cost": 100},
    Enchantment.PHYSICAL: {"name": "物理强化", "desc": "物理伤害+15%", "cost": 100},
    Enchantment.ICE: {"name": "冰系强化", "desc": "冰系伤害+20%", "cost": 100},
    Enchantment.FLAME: {"name": "火系强化", "desc": "火系伤害+20%", "cost": 100},
    Enchantment.TRIDENT: {"name": "电系强化", "desc": "电系伤害+20%", "cost": 100},
    Enchantment.WIND: {"name": "风系强化", "desc": "风系伤害+20%", "cost": 100},
    Enchantment.POISON: {"name": "毒系强化", "desc": "毒系伤害+20%", "cost": 100},
    Enchantment.BOMB: {"name": "爆炸强化", "desc": "爆炸伤害+20%", "cost": 100},
    Enchantment.DENSE: {"name": "致密V", "desc": "重锤获得距离增伤，伤害+5/px", "cost": 300},
    Enchantment.WIND_BURST: {"name": "风爆", "desc": "蓄风印记爆炸伤害固定为5000点", "cost": 200},
    Enchantment.POISON_CONTRACT: {"name": "试毒合约", "desc": "同时存在剧毒环刃与九头蛇毒箭时，中毒敌人被击败有10%概率爆炸，对周围敌人造成(基础毒伤+中毒层数)×18的伤害并击晕5秒，基础毒伤永久+1", "cost": 400},
    Enchantment.BURN: {"name": "高温燃烧", "desc": "燃烧伤害翻倍", "cost": 200},
    Enchantment.BLAZE_POWDER: {"name": "烈焰粉", "desc": "敌人永远燃烧，燃烧伤害+30%", "cost": 400},
    Enchantment.FROZEN_DEEP: {"name": "冰冻三尺", "desc": "同时存在冰霜炸弹与冰墙塔时，冰霜炸弹冻结时长+0.5秒，冰墙存在时间翻倍", "cost": 400},
    Enchantment.DRAGON_LEGEND: {"name": "龙族传说", "desc": "同时存在冰龙塔、火龙塔、电龙塔时，龙伤害与百分比真实伤害翻倍，且龙移动速度+75%", "cost": 1600},
    Enchantment.ENDLESS_GREED: {"name": "无尽贪婪", "desc": "集齐七种无尽炮塔后，其子弹5%概率爆炸，造成1%最大生命伤害并获得500金币", "cost": 1600},
    Enchantment.RAIN_FIRE: {"name": "水火相容", "desc": "雨天/雷暴/酸雨可以点燃敌人", "cost": 200},
    Enchantment.WITHER_ROSE: {"name": "凋零玫瑰", "desc": "同时拥有凋零之首与凋零核弹时，凋零debuff额外附加0.1%最大生命，凋零核弹伤害额外附加0.8%最大生命", "cost": 1600},
    Enchantment.LAVA: {"name": "岩浆桶", "desc": "每5秒提高1温度，每波开始时重置", "cost": 200},
    Enchantment.TELESCOPE: {"name": "望远镜", "desc": "所有炮塔射程增加1格", "cost": 200},
    Enchantment.PULSE_SHIELD: {"name": "脉冲护盾", "desc": "护盾被击碎后进入脉冲状态8秒，期间免疫所有伤害", "cost": 800},
    Enchantment.RESONANCE_STORM: {"name": "共振风暴", "desc": "同时存在雷神之锤和雷盾时，雷神之锤每攻击140次，所有雷盾反击一次并引爆所有蓄风印记", "cost": 1600},
    Enchantment.EMBER_REBIRTH: {"name": "余烬重生", "desc": "同时存在满级龙息塔与8座满级核弹塔时，点击龙息塔按Q花费5万金币献祭：塔消失、全场核弹立即冷却齐射，巨型陨石从天而降、着地时对全场敌人造成1000000007伤害。献祭花费逐次翻倍", "cost": 3200},
    Enchantment.WAX: {"name": "蜜脾", "desc": "所有炮塔涂蜡，酸雨将无法破坏炮塔及护盾。酸雨开始后每0.5秒从终点扇形召唤5只蜜蜂，共召唤10次，蜜蜂随后寻敌，撞击敌人后死亡并造成其1%最大生命的毒系伤害", "cost": 400},
    Enchantment.INFINITY_GAUNTLET: {"name": "无限手套", "desc": "鼠标位置将始终附着无限手套，鼠标点击敌人可对其造成各种伤害，伤害 = 攻击力 * 波数 ** 2 * (1 + 对应元素强化 + 均衡强化)", "cost": 1600},
    Enchantment.UNSTABLE_CRYSTAL: {"name": "不稳定水晶", "desc": "TNT类炮塔子弹爆炸有10%概率在周围道路格生成不稳定水晶，敌人碰到后受到其1%最大生命伤害并引发爆炸；核弹/凋零核弹爆炸时全场每个道路格各有10%概率生成", "cost": 1600},
    Enchantment.POWER_V: {"name": "力量V", "desc": "物理伤害+150%；地狱升华之弩对BOSS的百分比伤害提升至6%", "cost": 400},
    Enchantment.LANTERN: {"name": "灯火通明", "desc": "场上存在3座满级星焰提灯时：燃烧伤害*1.5，火系伤害+80%，并永久驱散全场迷雾", "cost": 1000},
    Enchantment.MASTERPIECE: {"name": "臻品呈现", "desc": "同时存在寒冰盾与神锅时：全局冰系伤害+240%；神锅每攻击140次释放大招，对全场敌人造成61803+500*|温度|伤害，并使其永久获得冰系破甲、冰冻4秒", "cost": 1600},
}

GAUNTLET_ATTACKS = [
    (TowerType.PHYSICAL, 20, 0.80, WHITE),
    (TowerType.FLAME, 40, 0.02, ORANGE),
    (TowerType.POISON, 30, 0.16, GREEN),
    (TowerType.ICE, 20, 0.01, ICE_BLUE),
    (TowerType.WIND, 20, 0.01, MINT),
    (TowerType.TRIDENT, 30, 0.02, ELECTRIC_PURPLE),
]

ENCHANTMENT_ORDER = [
    Enchantment.BALANCED, Enchantment.PHYSICAL, Enchantment.ICE, Enchantment.FLAME, Enchantment.TRIDENT,
    Enchantment.WIND, Enchantment.POISON, Enchantment.BOMB, Enchantment.DENSE, Enchantment.WIND_BURST,
    Enchantment.POISON_CONTRACT, Enchantment.BURN, Enchantment.BLAZE_POWDER, Enchantment.FROZEN_DEEP,
    Enchantment.DRAGON_LEGEND, Enchantment.ENDLESS_GREED, Enchantment.RAIN_FIRE, Enchantment.WITHER_ROSE,
    # 火矢已删除：ENCHANTMENT_ORDER 里原第 21 位（TELESCOPE 之后）暂时空缺，后续放新附魔
    Enchantment.LAVA, Enchantment.TELESCOPE, Enchantment.PULSE_SHIELD,
    Enchantment.RESONANCE_STORM,
    Enchantment.EMBER_REBIRTH,
    Enchantment.WAX,
    Enchantment.INFINITY_GAUNTLET,
    Enchantment.UNSTABLE_CRYSTAL,
    Enchantment.POWER_V,
    Enchantment.LANTERN,
    Enchantment.MASTERPIECE,
]

NON_REPEATABLE_ENCHANTMENTS = {Enchantment.DENSE, Enchantment.WIND_BURST}

# 主菜单「图鉴」按钮
CODEX_BTN_X = 900
CODEX_BTN_Y = 930
CODEX_BTN_WIDTH = 760
CODEX_BTN_HEIGHT = 80
CODEX_BTN_COLOR = (46, 92, 150)

ENCHANT_BOX_WIDTH = 512
ENCHANT_BOX_HEIGHT = 432
ENCHANT_BOX_Y = INFO_BORDER_Y - ENCHANT_BOX_HEIGHT
ENCHANT_ICON_SIZE = 72
ENCHANT_ICON_GAP = 8
ENCHANT_ICONS_PER_ROW = 6
class BombSubType(Enum):
    SNOW = 1
    ICE = 2
    FLAME = 3
    POISON = 4
    WITHER_TNT = 5

# ==========================================================================================
#  冰冻核弹（爆炸塔三阶分支 3，贴图 9-3-3）
#  全屏【爆炸系】伤害：(3000 + 16*|温度|) * (等级-10) * 增伤，抗性由 take_damage 结算；
#  额外 0.6%*(等级-10) 最大生命真实伤害；全场冰冻 4s；额外降温 40°C 持续 8s（不改天气）
# ==========================================================================================
ICE_NUKE_FIRE_RATE = 40 * 60        # 攻击间隔 40 秒（核弹/凋零核弹为 35 秒）
ICE_NUKE_BASE_DAMAGE = 3000         # 基础项，× (等级 - 10) × 增伤
ICE_NUKE_TEMP_SCALE = 16            # 每点 |温度| 追加的伤害（高温低温都增伤）
ICE_NUKE_PERCENT = 0.006            # × (等级 - 10) 最大生命，真实伤害
ICE_NUKE_FREEZE_FRAMES = 4 * 60     # 全场冰冻 4 秒
ICE_NUKE_TEMP_DROP = 40             # 临时气候修正：额外降温 40 度
ICE_NUKE_TEMP_FRAMES = 8 * 60       # 降温持续 8 秒

EMERALD_PER_WAVE_BY_LEVEL = {11: 1, 12: 2, 13: 3, 14: 4, 15: 5}

# ==========================================================================================
#  星焰提灯 —— 火系（FLAME）第 3 分支，Lv11 起解锁
#  伤害 = (1600 + 温度 × 2) × (等级 - 10)，以自身为中心释放环形冲击波，命中范围内全部敌人
# ==========================================================================================
LANTERN_RANGE_TILES = {11: 2.50, 12: 2.75, 13: 3.00, 14: 3.25, 15: 3.50}
LANTERN_FIRE_RATE = 120          # 攻击间隔 2 秒（60 FPS）
LANTERN_BASE_DAMAGE = 1600
LANTERN_TEMP_MULT = 2
LANTERN_BURN_FRAMES = 4 * 60     # 燃烧 4 秒
LANTERN_DAMAGE_COLOR = ORANGE    # 冲击波飘字（橙色，与火系一致）
LANTERN_ENCHANT_TOWERS = 3       # 「灯火通明」需要的满级提灯数量
LANTERN_BURN_MULT = 1.5          # 灯火通明：全局燃烧伤害倍率（乘算）
LANTERN_FIRE_BONUS = 80          # 灯火通明：火系伤害加成（加算，百分点）


# ==========================================================================================
#  神锅 —— 冰系（ICE）第 4 分支，Lv11 起解锁
#  射程全屏，攻击向全场随机 1 名敌人发射一枚冰系四芒星，单体结算。
#  伤害 = 基础值 + 系数 * |温度|（温度越低越强，和冰系降温度的思路一致）。
#  命中后施加永久「冰系破甲」：目标冰系抗性 -100 个百分点（走抗性乘区），
#  这一条计入 take_damage 的增伤乘区，与抗性乘区分开算。
# ==========================================================================================
# ==========================================================================================
#  卧龙 —— 三叉戟塔（6）三阶分支 3，Lv11 起解锁
#  攻击与 6-3-1 / 6-3-2 相同（金币 1% 加伤 + 整列闪电）。
#  自身无敌；靠「攻击」和「挨打」攒能量，满 100 在道路上放一座八卦阵。
# ==========================================================================================
# ==========================================================================================
#  波次敌人数曲线
#  原先是 5 + 波数*2 一路线性涨，95 波时基础 200 只 + 幽灵 51 只 = 251 只同屏，
#  帧率直接崩。改成：25 波之前保持原样，之后每波只 +0.8，并给基础数 / 幽灵数各设上限。
# ==========================================================================================
WAVE_ENEMY_BASE = 5               # 起手数量
WAVE_ENEMY_LINEAR = 2             # 25 波前每波 +2
WAVE_ENEMY_TURN_WAVE = 25         # 从第几波开始收敛
WAVE_ENEMY_LATE_STEP = 0.8        # 收敛后每波 +0.8
WAVE_ENEMY_CAP = 88               # 基础数量上限
WAVE_GHOST_CAP = 18               # 幽灵数量上限（原公式 波数//2+4，95 波能到 51 只）
WAVE_GHOST_CAP_LATE = 24          # 「亡灵军团」纪元（130-139 波）幽灵上限临时放宽

# ==========================================================================================
#  敌人血量膨胀曲线
#  100 波前：1.2^波数（原公式，保持不变）。
#  101 波起：每波只膨胀 1.02 倍，锚定在 1.2^100 上 —— 49 波累计只涨 2.69 倍，
#  否则按 1.2 走到 150 波会是 1.2^150 ≈ 7.5e11 倍，小怪比 BOSS 还肉。
#  101-149 波的压力靠「群系纪元」（见 EPOCH_* 表）而不是血量提供。
# ==========================================================================================
HP_INFLATION_BASE_RATE = 1.2
HP_INFLATION_TURN_WAVE = 100      # 从 101 波开始降速
HP_INFLATION_LATE_RATE = 1.02


def enemy_health_multiplier(wave):
    """普通敌人血量倍率：≤100 波 1.2^w；>100 波 1.2^100 × 1.02^(w-100)。"""
    if wave <= HP_INFLATION_TURN_WAVE:
        return HP_INFLATION_BASE_RATE ** wave
    return ((HP_INFLATION_BASE_RATE ** HP_INFLATION_TURN_WAVE)
            * (HP_INFLATION_LATE_RATE ** (wave - HP_INFLATION_TURN_WAVE)))

CROUCH_DRAGON_BRANCH = 3
CD_ENERGY_PER_ATTACK = 1          # 自身每次攻击 +1
CD_ENERGY_PER_HIT = 50            # 周围 8 格的塔被攻击（含破盾）+50
CD_ENERGY_PER_SELF_HIT = 100      # 卧龙自己被攻击 +100
CD_ENERGY_HIT_CD = 60             # 挨打加能量的冷却（帧）：防止 BOSS 贴身光环把能量刷爆
CD_ENERGY_FULL = 100              # 满 100 放一座八卦阵
# 八卦阵伤害 = (CD_BAGUA_BASE + CD_BAGUA_TEMP * |温度|) * (等级 - 10)
#              * (1 + 电系加成 + 均衡加成) * (1 - 敌人抗性)
# 最后一乘由 take_damage 统一结算，所以这里只算到抗性之前。
CD_BAGUA_BASE = 2500              # 固定基础
CD_BAGUA_TEMP = 64                # 每 1 度温度的加成
CD_BAGUA_TICK = 60                # 同一个敌人每秒最多吃 1 次
CD_BAGUA_DURATION = int(12.5 * 60)   # 八卦阵存在 12.5 秒
CD_BAGUA_SPIN = 0.45             # 太极自转速度（度/帧），约 27°/秒
BAGUA_SIZE = TILE_SIZE * 2         # 八卦阵贴图边长 = 256
BAGUA_ALPHA = 64                   # 八卦阵透明度 75%（= 不透明度 25%，255 * 0.25）
CD_BAGUA_RADIUS = TILE_SIZE        # 判定半径 = 128（直径 256，与贴图一致）

# 冰霜炸弹（冰系三阶分支 1）：AOE 伤害 = 基础攻击力 + 系数 * |温度|
ICE_BOMB_TEMP_MULT = {11: 3, 12: 6, 13: 9, 14: 12, 15: 15}
# 每道冰墙降低的温度
ICE_WALL_TEMP_DROP = 10

HOLY_POT_BRANCH = 4
HOLY_POT_DAMAGE_BASE = {11: 100, 12: 200, 13: 300, 14: 400, 15: 500}
HOLY_POT_DAMAGE_TEMP = {11: 2, 12: 4, 13: 6, 14: 8, 15: 10}
HOLY_POT_FIRE_RATE = 60          # 攻击间隔 1 秒（60 FPS）
HOLY_POT_BOLT_SPEED = 26         # 四芒星飞行速度（像素/帧）
HOLY_POT_BOLT_SIZE = 96          # 四芒星绘制边长（32 像素素材的 3 倍整数放大）
HOLY_POT_BOLT_SPIN = 7.0         # 四芒星自转速度（度/帧）
ICE_BROKEN_RESIST_DOWN = 1.0     # 冰系破甲：冰系抗性 -100 个百分点（走抗性乘区）

# 「臻品呈现」附魔
MASTERPIECE_ICE_BONUS = 240      # 冰系伤害 +240%（加算，百分点）
RESONANCE_ATTACKS = 140          # 雷神之锤每攻击 N 次触发一次共振风暴
MASTERPIECE_ATTACKS = 140        # 神锅每攻击 N 次释放大招
MASTERPIECE_DAMAGE = 61803       # 大招基础伤害
MASTERPIECE_TEMP_MULT = 500      # 大招温度系数：伤害 = 61803 + 500 * |温度|
MASTERPIECE_FREEZE_FRAMES = 4 * 60   # 大招冰冻 4 秒
ULTIMATE_VIDEO_ZOOM = 1.15       # 大招动画放大倍数（>1 = 比全屏更大，裁掉右下角 UID）
ULTIMATE_VIDEO_FPS = 30


# ==========================================================================================
#  三龙（冰 / 火 / 电）的额外真实伤害
#  龙每次撞到敌人，除了原本的「倍率 × |温度|」伤害，再按目标最大生命的百分比结算一次。
#  这一部分走 take_damage(ignore_armor=True)：不吃抗性、增伤乘区、冰系破甲、
#  元素附魔加成等任何增/减伤，是纯真实伤害。
#  龙族传说（DRAGON_LEGEND）会把这一百分比也一起翻倍。
# ==========================================================================================
DRAGON_HP_PCT = {"ice": 0.01, "fire": 0.02, "electric": 0.03}
DRAGON_LEGEND_PCT_MULT = 2
DRAGON_TRUE_DAMAGE_COLOR = (255, 245, 200)   # 真实伤害飘字（暖白，和元素色区分开）
DRAGON_SUMMON_CHANCE = 0.05                  # 冰 / 火 / 电三龙的召唤概率统一 5%


# ==========================================================================================
#  雷神之锤 —— 风系（WIND）第 2 分支，Lv11 起解锁
#  子弹命中时在命中点劈一道雷（resonance_storm 素材），造成小范围 AOE。
#  注意：贴图从长条闪电改成 282x282 的爆裂后，判定也跟着从「整列」改成圆形范围，
#  不然视觉上是小爆裂、实际却打一列，看着很怪。
# ==========================================================================================
WIND_STORM_DAMAGE = {11: 2000, 12: 4000, 13: 6000, 14: 8000, 15: 10000}
WIND_STORM_RADIUS = 127          # 落雷 AOE 半径 = 贴图冲击光环实测半宽（127px）
WIND_STORM_VISUAL_EVERY = 2      # 每 N 次命中才播一次特效（每次都放会掉帧）


class EnemyType(Enum):
    NORMAL = 0
    FAST = 1
    TANK = 2
    ELITE = 3
    WITHER = 4
    IRON_ARMORED = 5
    SLIME = 6
    SLIMELING = 7
    GOLD_ARMORED = 8
    GHOST = 9
    DIAMOND_ARMORED = 10
    NETHERITE_ARMORED = 11
    MAGMA_CUBE = 12
    MAGMA_CUBE_SMALL = 13
    HEROBRINE = 14
    BLAZE = 15
    CREEPER = 16
    CHARGED_CREEPER = 17
    SPIDER = 18
    FINAL_BOSS = 19
    WORLD_SEED = 20      # 第 150 波真·最终 BOSS：原初·阿尔法（世界种子）
    END_CRYSTAL = 21     # 阿尔法第 3 阶段召唤的末影水晶（可攻击，站着回层）


# ==========================================================================================
#  抗性（原「护甲减伤」）与抗性降低（原「破甲」）
#  统一公式：最终伤害 = 基础伤害区 × (1 + 增伤乘区) × (1 - 敌人抗性)
#  - 抗性可以为负：非盔甲怪被「抗性降低」后抗性 = -20%，相当于受伤 ×1.2
#  - 抗性降低只是把抗性减 20 个百分点，不再把盔甲怪的抗性直接抹平成 -20%
# ==========================================================================================
# 烈焰人专属抗性：火抗 500%（实际在 take_damage 里直接短路成免疫）
BLAZE_FIRE_RESIST = 5.0
BLAZE_ICE_RESIST = -1.0            # 初始冰抗 -100%（冰伤 ×2）
BLAZE_ICE_RESIST_BROKEN = -2.0     # 冰系破甲后 -200%（冰伤 ×3）

ARMOR_RESISTANCE = {
    EnemyType.IRON_ARMORED: 0.60,
    EnemyType.GOLD_ARMORED: 0.70,
    EnemyType.DIAMOND_ARMORED: 0.80,
    EnemyType.NETHERITE_ARMORED: 0.90,
}
# 远古守卫者（精英怪）：出场 ELITE_LOCK_DELAY 帧后，随机锁定一座炮塔
# 护盾可以挡下（破盾但不锁定）；卧龙免疫，不会被选中
ELITE_LOCK_DELAY = 3 * 60
ELITE_LOCK_FRAMES = 15 * 60

BROKEN_RESIST_DOWN = 0.20         # 「抗性降低」debuff：全抗 -20 个百分点

# 最终 BOSS 的「指令-魅惑 /effect @e[type=Tower] charm」
# 随机魅惑 2 座炮塔，攻击全部变成等量治疗；护盾可挡，卧龙免疫
BOSS_CHARM_TOWERS = 2
BOSS_CHARM_FRAMES = 12 * 60

# ==========================================================================================
#  阿尔法的「群系侵蚀-圣火 /effect @e[type=Tower] sacred_fire」（第 2 阶段下界技能）
#  - 随机一座炮塔附着圣火：每次攻击有 40% 概率落空（MISS，仍消耗冷却）；
#  - 每隔 SACRED_FIRE_TICK_FRAMES：炮塔等级 -1（最低降到 1 级，不删除），
#    并向上下左右四格的炮塔蔓延；
#  - 护盾可以挡下「附着 / 蔓延」（破盾不被点燃）；已经着火的塔再套盾无济于事；
#  - 卧龙免疫；脉冲护盾期间免疫；
#  - 圣火没有时限：奥米伽式的「转阶段净化」——阿尔法进入下一阶段（世界重生成）时全部熄灭，
#    波次推进（select_weather）与 BOSS 死亡时同样清空。
# ==========================================================================================
SACRED_FIRE_MISS_CHANCE = 0.4
SACRED_FIRE_TICK_FRAMES = 16 * 60
SACRED_FIRE_TARGETS = 2            # 每次施放附着的炮塔数量


class Weather(Enum):
    EXTREME_HEAT = 0
    SUNNY = 1
    CLOUDY = 2
    RAINY = 3
    SNOWY = 4
    THUNDERSTORM = 5
    ACID_RAIN = 6
    TAILWIND = 7
    HEADWIND = 8
    SCORCHING_SUN = 9
    FOG = 10
    EXTREME_COLD = 11
    MAGNETIC_STORM = 12
    FIRE_RAIN = 13
    AURORA = 14
    ENDLESS_NIGHT = 15


WEATHER_CONFIG = {
    Weather.ACID_RAIN: {"name": "酸雨", "temp": 5, "desc": "酸雨：敌人中毒，炮塔等级-1，中毒层数翻倍", "color": (0, 255, 0)},
    Weather.EXTREME_HEAT: {"name": "酷暑", "temp": 40, "desc": "酷暑：温度较高，火焰伤害提升", "color": (255, 69, 0)},
    Weather.SUNNY: {"name": "晴天", "temp": 30, "desc": "晴天：温度适中", "color": (255, 255, 255)},
    Weather.CLOUDY: {"name": "多云", "temp": 20, "desc": "多云：温度较低", "color": (180, 180, 180)},
    Weather.RAINY: {"name": "雨天", "temp": 10, "desc": "雨天：温度较低，无法点燃", "color": (100, 150, 255)},
    Weather.SNOWY: {"name": "雪天", "temp": 0, "desc": "雪天：温度骤降", "color": (150, 200, 255)},
    Weather.THUNDERSTORM: {"name": "雷暴", "temp": 15, "desc": "雷暴：温度较低，闪电将会劈下", "color": (255, 215, 0)},
    Weather.TAILWIND: {"name": "顺风", "temp": 25, "desc": "顺风：敌人移速+50%，炮塔射程+50%", "color": (152, 255, 152)},
    Weather.HEADWIND: {"name": "逆风", "temp": 25, "desc": "逆风：敌人移速-50%，炮塔射程-50%", "color": (152, 255, 152)},
    Weather.SCORCHING_SUN: {"name": "烈日", "temp": 50, "desc": "烈日：温度极高，敌人全体燃烧", "color": (255, 200, 0)},
    Weather.FOG: {"name": "迷雾", "temp": 15, "desc": "迷雾：视野遮挡", "color": (180, 180, 180)},
    Weather.EXTREME_COLD: {"name": "极寒", "temp": -20, "desc": "极寒：温度极低", "color": (100, 200, 255)},
    Weather.MAGNETIC_STORM: {"name": "磁暴", "temp": 20, "desc": "磁暴：闪电伤害翻倍，传送失效，金属敌人抗性降低", "color": (0, 255, 255)},
    Weather.FIRE_RAIN: {"name": "火雨", "temp": 100, "desc": "火雨：敌人持续燃烧，无法冻结", "color": (255, 69, 0)},
    Weather.AURORA: {"name": "极光", "temp": -10, "desc": "极光：温度较低，炮塔攻速随零下温度提升", "color": (0, 255, 255)},
    Weather.ENDLESS_NIGHT: {"name": "永夜", "temp": 12, "desc": "永夜：黑暗降临，最终Boss战", "color": (148, 0, 211)},
}


# ==========================================================================================
#  101-149 波「群系纪元」：按波段改写随机怪池权重（零新敌人，只调构成）。
#  没覆盖到的波段走 select_enemy_type 的默认概率瀑布。
#  120-129 波「天灾」不改怪池，只改天气池（EPOCH_WEATHER_POOLS）。
# ==========================================================================================
EPOCH_ENEMY_POOLS = {
    # 110-119 合金洪流：盔甲系为主，考验破甲 / 磁暴
    (110, 119): [
        (EnemyType.IRON_ARMORED, 22), (EnemyType.GOLD_ARMORED, 18),
        (EnemyType.DIAMOND_ARMORED, 18), (EnemyType.NETHERITE_ARMORED, 14),
        (EnemyType.TANK, 10), (EnemyType.NORMAL, 8), (EnemyType.FAST, 10),
    ],
    # 130-139 亡灵军团：凋零混编，幽灵上限临时放宽
    (130, 139): [
        (EnemyType.WITHER, 8), (EnemyType.GOLD_ARMORED, 14), (EnemyType.IRON_ARMORED, 14),
        (EnemyType.NETHERITE_ARMORED, 12), (EnemyType.NORMAL, 16), (EnemyType.FAST, 14),
        (EnemyType.SLIME, 10), (EnemyType.MAGMA_CUBE, 8), (EnemyType.TANK, 4),
    ],
}

# 「天灾」纪元（120-129 波）的天气池：只在恶劣天气里抽
EPOCH_WEATHER_WAVE_BAND = (120, 129)
EPOCH_WEATHER_POOLS = [
    Weather.ACID_RAIN, Weather.FIRE_RAIN, Weather.MAGNETIC_STORM,
    Weather.FOG, Weather.HEADWIND, Weather.EXTREME_HEAT, Weather.EXTREME_COLD,
]

ENEMY_TYPES = {
    "NORMAL": {"image": "normal.png", "speed": 2, "health": 100, "reward": 10},
    "FAST": {"image": "fast.png", "speed": 3, "health": 100, "reward": 15},
    "TANK": {"image": "tank.png", "speed": 1.5, "health": 300, "reward": 30},
    "ELITE": {"image": "elite.png", "speed": 2.5, "health": 200, "reward": 40},
    "WITHER": {"image": "wither.png", "speed": 2, "health": 800, "reward": 100},
    "HEROBRINE": {"image": "herobrine.png", "speed": 3, "health": 5000000, "reward": 500},
    "IRON_ARMORED": {"image": "iron_armored.png", "speed": 1.2, "health": 250, "reward": 35},
    "SLIME": {"image": "slime.png", "speed": 2, "health": 180, "reward": 25},
    "SLIMELING": {"image": "slime.png", "speed": 3, "health": 90, "reward": 10},
    "GOLD_ARMORED": {"image": "gold_armored.png", "speed": 1.2, "health": 250, "reward": 35},
    "GHOST": {"image": "ghost.png", "speed": 3, "health": 100, "reward": 25},
    "DIAMOND_ARMORED": {"image": "diamond_armored.png", "speed": 1.2, "health": 300, "reward": 40},
    "NETHERITE_ARMORED": {"image": "netherite_armored.png", "speed": 1.2, "health": 300, "reward": 50},
    "MAGMA_CUBE": {"image": "magma_cube.png", "speed": 2.0, "health": 180, "reward": 25},
    "MAGMA_CUBE_SMALL": {"image": "magma_cube.png", "speed": 3.0, "health": 90, "reward": 10},
    # 烈焰人：飞行 + 免疫一切火系伤害（火抗 500%，连飘字都没有）
    # 冰抗 -100%，被冰系破甲后 -200%
    "BLAZE": {"image": "blaze.png", "speed": 2.2, "health": 200, "reward": 40},
    "CREEPER": {"image": "creeper.png", "speed": 2, "health": 100, "reward": 20},
    "CHARGED_CREEPER": {"image": "charged_creeper.png", "speed": 2, "health": 100, "reward": 20},
    "SPIDER": {"image": "spider.png", "speed": 4, "health": 100, "reward": 20},
    "FINAL_BOSS": {"image": "command_block.png", "speed": 2, "health": 200000000, "reward": 0},
    # 阿尔法本体 / 末影水晶的血量都在各自类里按层重设，这里只占位（贴图 + 图鉴用）
    "WORLD_SEED": {"image": "world_seed.png", "speed": 2, "health": 1_500_000_000, "reward": 0},
    "END_CRYSTAL": {"image": "end_crystal.png", "speed": 0, "health": 3_000_000_000, "reward": 0},
}


# ==========================================================================================
#  第 100 波最终 BOSS —— 终焉·奥米伽 (OMEGA)
# ==========================================================================================
#  BOSS 一共 FINAL_BOSS_LAYERS 层血，每层 FINAL_BOSS_LAYER_HEALTH 点。
#  100 × 200,000,000 = 20,000,000,000（200 亿）
#  如需保持 144 亿总血量，把 FINAL_BOSS_LAYER_HEALTH 改成 144_000_000 即可。
# ==========================================================================================
FINAL_BOSS_NAME = "终焉·奥米伽"
FINAL_BOSS_EN_NAME = "OMEGA"
FINAL_BOSS_TITLE = "原初命令方块"
HEROBRINE_WAVE = 50              # 第 50 波：Herobrine
OMEGA_WAVE = 100                 # 第 100 波：终焉·奥米伽（中途大 Boss）
FINAL_BOSS_WAVE = 150            # 第 150 波：原初·阿尔法（真·最终 BOSS），也是总波数
BOSS_ONLY_WAVES = (HEROBRINE_WAVE, OMEGA_WAVE, FINAL_BOSS_WAVE)   # 只出 BOSS、不出小怪的波
FINAL_BOSS_LAYERS = 100
FINAL_BOSS_LAYER_HEALTH = 200_000_000
FINAL_BOSS_TOTAL_HEALTH = FINAL_BOSS_LAYERS * FINAL_BOSS_LAYER_HEALTH
FINAL_BOSS_LAYERS_PER_PHASE = FINAL_BOSS_LAYERS // 4   # 100 层 -> 每阶段 25 层

# ==========================================================================================
#  中毒（每 1.25 秒一跳）：纯平坦伤害，永久持续、无限叠层，不做百分比
#  跳伤 = (基础毒伤 + 中毒层数) * (1 + 毒系伤害加成)
#  试毒合约：中毒敌人被击败有 POISON_CONTRACT_TRIGGER_CHANCE 概率触发
#  爆炸 = (基础毒伤 + 触发者层数) * POISON_CONTRACT_BURST_MULT * (1 + 毒系伤害加成)
# ==========================================================================================
# 原本是 6.0（跳伤 ×6）；按新公式改为 1.0。要恢复原来的手感，把它改回 6.0 即可。
POISON_CONTRACT_TRIGGER_CHANCE = 0.10
POISON_CONTRACT_BURST_MULT = 18

# BOSS 核心画面尺寸（比最初版本放大 50%：256 -> 384）
FINAL_BOSS_CORE_SIZE = 384
# 余烬重生的陨石（1,000,000,007）只打穿当前这一层，溢出伤害不再带到下一层
FINAL_BOSS_METEOR_DAMAGE = 1000000007
# 不稳定水晶的绘制尺寸
UNSTABLE_CRYSTAL_SIZE = TILE_SIZE
# 最终 BOSS 同屏伤害飘字上限（超出时移除最旧的，避免糊成一团）
BOSS_DAMAGE_TEXT_LIMIT = 12

FINAL_BOSS_PHASE_NAMES = [
    "编译 COMPILE",
    "覆写 OVERWRITE",
    "执行 EXECUTE",
    "终焉 OMEGA",
]

# 阶段主色：外壳裂开得越多，颜色越危险
FINAL_BOSS_PHASE_COLORS = [
    (120, 80, 255),
    (190, 60, 240),
    (255, 70, 190),
    (255, 60, 40),
]

# BOSS 召唤物的固定血量（不套用 1.2^波数，否则第100波小怪会比BOSS还肉）
FINAL_BOSS_MINION_HEALTH = {
    EnemyType.NORMAL: 60_000_000,
    EnemyType.FAST: 45_000_000,
    EnemyType.NETHERITE_ARMORED: 120_000_000,
    EnemyType.CREEPER: 40_000_000,
    EnemyType.GHOST: 55_000_000,
    EnemyType.WITHER: 150_000_000,
}

# 各阶段召唤物池
FINAL_BOSS_SUMMON_POOL = {
    1: [EnemyType.NORMAL, EnemyType.FAST, EnemyType.CREEPER],
    2: [EnemyType.NETHERITE_ARMORED, EnemyType.CREEPER, EnemyType.FAST],
    3: [EnemyType.GHOST, EnemyType.NETHERITE_ARMORED, EnemyType.WITHER],
    4: [EnemyType.GHOST, EnemyType.WITHER, EnemyType.NETHERITE_ARMORED],
}

# 战斗场地范围（像素，限制 BOSS 核心的活动区域）
FINAL_BOSS_ARENA_LEFT = 280
FINAL_BOSS_ARENA_RIGHT = GRID_WIDTH * TILE_SIZE - 280
FINAL_BOSS_ARENA_TOP = 300
FINAL_BOSS_ARENA_BOTTOM = (1 + GRID_HEIGHT) * TILE_SIZE - 260


# ==========================================================================================
#  第 150 波真·最终 BOSS —— 原初·阿尔法 (ALPHA)，世界种子
# ==========================================================================================
#  你在第 100 波删掉了那条命令，但世界不是命令写出来的 —— 是从基岩最底下
#  那颗种子里长出来的。阿尔法觉得这个世界「生成得不好」，打算重新生成一遍。
#
#  结构：320 层 = 5 阶段 × 64 层（64 = MC 的一组），每阶段对应一个维度，
#  从主世界一路「重新生成」到虚空。复用奥米伽的层血 / 技能 / 播报管线。
#
#  总血量 = 320 × 1,500,000,000 = 480,000,000,000（4800 亿）= 24 × 奥米伽。
#  单层 max_health = 15 亿：龙的 1-3% 真伤（1500-4500 万/次）、地狱射线 5% 层血
#  （力量V：6%）
#  （7500 万）、凋零玫瑰 0.1%（150 万/跳）全部按层自动缩放，无需改动。
# ==========================================================================================
ALPHA_BOSS_NAME = "原初·阿尔法"
ALPHA_BOSS_EN_NAME = "ALPHA"
ALPHA_BOSS_TITLE = "世界种子"
ALPHA_LAYERS = 320
ALPHA_LAYER_HEALTH = 1_500_000_000
ALPHA_TOTAL_HEALTH = ALPHA_LAYERS * ALPHA_LAYER_HEALTH
ALPHA_LAYERS_PER_PHASE = 64
ALPHA_CORE_SIZE = 448

ALPHA_PHASE_NAMES = [
    "主世界 OVERWORLD",
    "下界 NETHER",
    "末地 END",
    "深暗之域 DEEP DARK",
    "虚空 THE VOID",
]

# 阶段主色：草绿 → 赤红 → 末地黄 → 幽匿青 → 虚空紫
ALPHA_PHASE_COLORS = [
    (96, 210, 110),
    (235, 90, 45),
    (232, 220, 150),
    (0, 190, 175),
    (170, 70, 235),
]

# 移动 / 施法间隔（帧）。最后 16 层狂暴再整体 ×0.7（见 ALPHA_BERSERK_LAYERS）
ALPHA_MOVE_INTERVAL = {1: 150, 2: 120, 3: 95, 4: 85, 5: 65}
ALPHA_CAST_COOLDOWN = {1: 235, 2: 195, 3: 165, 4: 140, 5: 110}

# 召唤物固定血量（约为奥米伽的 8 倍，不套波数膨胀；进阶段再 ×(1+0.2*(phase-1))）
ALPHA_MINION_HEALTH = {
    EnemyType.NORMAL: 500_000_000,
    EnemyType.FAST: 400_000_000,
    EnemyType.CREEPER: 350_000_000,
    EnemyType.MAGMA_CUBE: 450_000_000,
    EnemyType.BLAZE: 500_000_000,
    EnemyType.NETHERITE_ARMORED: 1_100_000_000,
    EnemyType.GHOST: 500_000_000,
    EnemyType.WITHER: 1_300_000_000,
}

# 各阶段召唤物池
ALPHA_SUMMON_POOL = {
    1: [EnemyType.NORMAL, EnemyType.FAST, EnemyType.CREEPER],
    2: [EnemyType.MAGMA_CUBE, EnemyType.BLAZE, EnemyType.NETHERITE_ARMORED, EnemyType.CREEPER],
    3: [EnemyType.GHOST, EnemyType.NETHERITE_ARMORED, EnemyType.WITHER],
    4: [EnemyType.WITHER, EnemyType.NETHERITE_ARMORED, EnemyType.GHOST],
    5: [EnemyType.GHOST, EnemyType.WITHER, EnemyType.NETHERITE_ARMORED, EnemyType.BLAZE],
}

# P2 下界：群系侵蚀 —— 温度每 45 帧向 +80 回落一格（冰塔照常往回拉，形成拉锯）
ALPHA_NETHER_TEMP = 80
ALPHA_NETHER_PULL_INTERVAL = 45

# P4 深暗之域：幽匿护甲 —— 受到的「直接伤害」×0.4；
# DoT（dot=True）与 ignore_armor 的百分比真伤不减免
ALPHA_SCULK_ARMOR_MULT = 0.4
# P4 灵波：3 秒预警后震荡全场，无视护盾锁定全部炮塔 6 秒（脉冲免疫、卧龙免疫）
ALPHA_SONIC_WARN_FRAMES = 3 * 60
ALPHA_SONIC_LOCK_FRAMES = 6 * 60

# P5 虚空：/stop 停服读条（奥米伽世界重载的强化版），狂暴层数线
ALPHA_STOP_CAST_FRAMES = 15 * 60
ALPHA_BERSERK_LAYERS = 16

# P3 末地：末影水晶（可攻击的特殊敌人）。每颗每 ALPHA_END_CRYSTAL_HEAL_FRAMES
# 为阿尔法回复一层血（先补满当前层，再重生成一层，上限 320）。
ALPHA_END_CRYSTAL_HEALTH = 3_000_000_000
ALPHA_END_CRYSTAL_HEAL_FRAMES = 10 * 60
ALPHA_END_CRYSTAL_PER_CAST = 2
ALPHA_END_CRYSTAL_CAP = 3

# P3 彩蛋：幻影·Herobrine 沿路走来（把 50 波的鬼故事重讲一遍）
ALPHA_PHANTOM_LAYERS = 3
ALPHA_PHANTOM_SPEED = 1.2

# 群系改写：阿尔法转阶段时地形随群系更替（见 game._build_background 的 terrain 参数）
#   overworld 主世界（地形不变）/ nether 下界 / end 末地 / night 永夜（黑曜石系黑夜配色）
ALPHA_PHASE_TERRAIN = {1: "overworld", 2: "nether", 3: "end", 4: "night", 5: "night"}
# 转阶段播报里追加的地形说明（None = 不追加）
ALPHA_PHASE_TERRAIN_DESC = {
    2: "石头化为下界岩 · 道路铺上萤石 · 金矿变成下界金矿石",
    3: "石头化为末地石 · 道路铺上黑曜石 · 金矿变成末地金矿石",
    4: "永夜降临",
    5: "永夜深处",
}

# 余烬重生的陨石对阿尔法依旧只打穿 1 层（吃火系加成后单发 50-70 亿 > 15 亿，无需调整）
