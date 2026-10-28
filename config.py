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
    Enchantment.FIRE_ARROW: {"name": "火矢", "desc": "箭矢伤害*2，附带燃烧4秒", "cost": 200},
    Enchantment.PULSE_SHIELD: {"name": "脉冲护盾", "desc": "护盾被击碎后进入脉冲状态8秒，期间免疫所有伤害", "cost": 800},
    Enchantment.RESONANCE_STORM: {"name": "共振风暴", "desc": "同时存在雷神之锤和雷盾时，雷神之锤每攻击120次，所有雷盾反击一次并引爆所有蓄风印记", "cost": 1600},
    Enchantment.EMBER_REBIRTH: {"name": "余烬重生", "desc": "同时存在满级龙息塔与8座满级核弹塔时，点击龙息塔按Q花费5万金币献祭：塔消失、全场核弹立即冷却齐射，巨型陨石从天而降、着地时对全场敌人造成1000000007伤害。献祭花费逐次翻倍", "cost": 3200},
    Enchantment.WAX: {"name": "蜜脾", "desc": "所有炮塔涂蜡，酸雨将无法破坏炮塔及护盾。酸雨开始后每0.5秒从终点扇形召唤5只蜜蜂，共召唤10次，蜜蜂随后寻敌，撞击敌人后死亡并造成其1%最大生命的毒系伤害", "cost": 400},
    Enchantment.INFINITY_GAUNTLET: {"name": "无限手套", "desc": "鼠标位置将始终附着无限手套，鼠标点击敌人可对其造成各种伤害，伤害 = 攻击力 * 波数 ** 2 * (1 + 对应元素强化 + 均衡强化)", "cost": 1600},
    Enchantment.UNSTABLE_CRYSTAL: {"name": "不稳定水晶", "desc": "TNT类炮塔子弹爆炸有10%概率在周围道路格生成不稳定水晶，敌人碰到后受到其1%最大生命伤害并引发爆炸；核弹/凋零核弹爆炸时全场每个道路格各有10%概率生成", "cost": 1600},
    Enchantment.POWER_V: {"name": "力量V", "desc": "箭矢伤害+125%", "cost": 300},
    Enchantment.LANTERN: {"name": "灯火通明", "desc": "场上存在3座满级星焰提灯时：燃烧伤害*1.5，火系伤害+80%，并永久驱散全场迷雾", "cost": 1000},
    Enchantment.MASTERPIECE: {"name": "臻品呈现", "desc": "冰系伤害+240%。神锅每攻击120次释放大招：播放「臻品呈现」动画，对全场敌人造成61803+500*|温度|伤害，并使其获得永久冰系破甲、冰冻4秒", "cost": 1600},
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
    Enchantment.LAVA, Enchantment.TELESCOPE, Enchantment.FIRE_ARROW, Enchantment.PULSE_SHIELD,
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
#  命中后施加永久「冰系破甲」：目标受到的冰系伤害 +100%，
#  该增伤与护甲减伤 / 破甲增伤在 take_damage 里属于同一个乘区。
# ==========================================================================================
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
ICE_BROKEN_MULT = 2.0            # 冰系破甲：受到冰系伤害 +100%（与护甲同乘区）

# 「臻品呈现」附魔
MASTERPIECE_ICE_BONUS = 240      # 冰系伤害 +240%（加算，百分点）
MASTERPIECE_ATTACKS = 120        # 神锅每攻击 N 次释放大招
MASTERPIECE_DAMAGE = 61803       # 大招基础伤害
MASTERPIECE_TEMP_MULT = 500      # 大招温度系数：伤害 = 61803 + 500 * |温度|
MASTERPIECE_FREEZE_FRAMES = 4 * 60   # 大招冰冻 4 秒
ULTIMATE_VIDEO_ZOOM = 1.15       # 大招动画放大倍数（>1 = 比全屏更大，裁掉右下角 UID）
ULTIMATE_VIDEO_FPS = 30


# ==========================================================================================
#  三龙（冰 / 火 / 电）的额外真实伤害
#  龙每次撞到敌人，除了原本的「倍率 × |温度|」伤害，再按目标最大生命的百分比结算一次。
#  这一部分走 take_damage(ignore_armor=True)：不吃护甲减免、破甲增伤、冰系破甲、
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
    CREEPER = 16
    CHARGED_CREEPER = 17
    SPIDER = 18
    FINAL_BOSS = 19


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
    Weather.RAINY: {"name": "雨天", "temp": 10, "desc": "雨天：温度较低，敌人移速-50%，无法点燃", "color": (100, 150, 255)},
    Weather.SNOWY: {"name": "雪天", "temp": 0, "desc": "雪天：温度骤降", "color": (150, 200, 255)},
    Weather.THUNDERSTORM: {"name": "雷暴", "temp": 15, "desc": "雷暴：温度较低，闪电将会劈下", "color": (255, 215, 0)},
    Weather.TAILWIND: {"name": "顺风", "temp": 25, "desc": "顺风：敌人移速+50%，炮塔射程+50%", "color": (152, 255, 152)},
    Weather.HEADWIND: {"name": "逆风", "temp": 25, "desc": "逆风：敌人移速-50%，炮塔射程-50%", "color": (152, 255, 152)},
    Weather.SCORCHING_SUN: {"name": "烈日", "temp": 50, "desc": "烈日：温度极高，敌人全体燃烧", "color": (255, 200, 0)},
    Weather.FOG: {"name": "迷雾", "temp": 15, "desc": "迷雾：视野遮挡", "color": (180, 180, 180)},
    Weather.EXTREME_COLD: {"name": "极寒", "temp": -20, "desc": "极寒：温度极低，敌人移速-50%", "color": (100, 200, 255)},
    Weather.MAGNETIC_STORM: {"name": "磁暴", "temp": 20, "desc": "磁暴：闪电伤害翻倍，传送失效，金属敌人破甲", "color": (0, 255, 255)},
    Weather.FIRE_RAIN: {"name": "火雨", "temp": 100, "desc": "火雨：敌人持续燃烧，无法冻结", "color": (255, 69, 0)},
    Weather.AURORA: {"name": "极光", "temp": -10, "desc": "极光：温度较低，炮塔攻速随零下温度提升", "color": (0, 255, 255)},
    Weather.ENDLESS_NIGHT: {"name": "永夜", "temp": 12, "desc": "永夜：黑暗降临，最终Boss战", "color": (148, 0, 211)},
}

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
    "CREEPER": {"image": "creeper.png", "speed": 2, "health": 100, "reward": 20},
    "CHARGED_CREEPER": {"image": "charged_creeper.png", "speed": 2, "health": 100, "reward": 20},
    "SPIDER": {"image": "spider.png", "speed": 4, "health": 100, "reward": 20},
    "FINAL_BOSS": {"image": "command_block.png", "speed": 2, "health": 200000000, "reward": 0},
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
FINAL_BOSS_WAVE = 100
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
