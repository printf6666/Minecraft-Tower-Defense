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

FORECAST_BTN_X = 2050
FORECAST_BTN_Y = 10
FORECAST_BTN_WIDTH = 460
FORECAST_BTN_HEIGHT = 60
FORECAST_BTN_COLOR = (60, 60, 60)
FORECAST_BTN_COLOR_DISABLED = (40, 40, 40)

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

ENCHANTMENT_DATA = {
    Enchantment.BALANCED: {"name": "均衡强化", "desc": "所有伤害+5%", "cost": 100},
    Enchantment.PHYSICAL: {"name": "物理强化", "desc": "物理伤害+15%", "cost": 100},
    Enchantment.ICE: {"name": "冰系强化", "desc": "冰系伤害+20%", "cost": 100},
    Enchantment.FLAME: {"name": "火系强化", "desc": "火系伤害+20%", "cost": 100},
    Enchantment.TRIDENT: {"name": "电系强化", "desc": "电系伤害+20%", "cost": 100},
    Enchantment.WIND: {"name": "风系强化", "desc": "风系伤害+20%", "cost": 100},
    Enchantment.POISON: {"name": "毒系强化", "desc": "毒系伤害+20%", "cost": 100},
    Enchantment.BOMB: {"name": "爆炸强化", "desc": "爆炸伤害+20%", "cost": 100},
    Enchantment.DENSE: {"name": "致密", "desc": "重锤获得距离增伤，伤害+2/px", "cost": 200},
    Enchantment.WIND_BURST: {"name": "风爆", "desc": "蓄风印记爆炸伤害固定为5000点", "cost": 200},
    Enchantment.POISON_CONTRACT: {"name": "试毒合约", "desc": "中毒的敌人被击败时有10%概率使全局中毒基础伤害永久提高1点", "cost": 400},
    Enchantment.BURN: {"name": "高温燃烧", "desc": "燃烧伤害翻倍", "cost": 200},
    Enchantment.BLAZE_POWDER: {"name": "烈焰粉", "desc": "敌人永远燃烧，燃烧伤害+30%", "cost": 400},
    Enchantment.FROZEN_DEEP: {"name": "冰冻三尺", "desc": "同时存在冰霜炸弹与冰墙塔时，冰霜炸弹冻结时长+0.5秒，冰墙存在时间翻倍", "cost": 400},
    Enchantment.DRAGON_LEGEND: {"name": "龙族传说", "desc": "同时存在冰龙塔、火龙塔、电龙塔时，龙伤害翻倍且移动速度+75%", "cost": 600},
    Enchantment.ENDLESS_GREED: {"name": "无尽贪婪", "desc": "集齐七件无尽炮塔后，其子弹5%概率爆炸，造成1%最大生命伤害并获得500金币", "cost": 1600},
    Enchantment.RAIN_FIRE: {"name": "水火相容", "desc": "雨天/雷暴/酸雨可以点燃敌人", "cost": 200},
    Enchantment.WITHER_ROSE: {"name": "凋零玫瑰", "desc": "凋零核弹伤害额外附加0.8%最大生命", "cost": 1600},
    Enchantment.LAVA: {"name": "岩浆桶", "desc": "每5秒提高1温度，每波开始时重置", "cost": 200},
    Enchantment.TELESCOPE: {"name": "望远镜", "desc": "所有炮塔基础射程增加1格", "cost": 200},
    Enchantment.FIRE_ARROW: {"name": "火矢", "desc": "箭矢伤害*2，附带燃烧4秒", "cost": 200},
    Enchantment.PULSE_SHIELD: {"name": "脉冲护盾", "desc": "护盾被击碎后进入脉冲状态8秒，期间免疫所有伤害", "cost": 800},
}

ENCHANTMENT_ORDER = [
    Enchantment.BALANCED, Enchantment.PHYSICAL, Enchantment.ICE, Enchantment.FLAME, Enchantment.TRIDENT,
    Enchantment.WIND, Enchantment.POISON, Enchantment.BOMB, Enchantment.DENSE, Enchantment.WIND_BURST,
    Enchantment.POISON_CONTRACT, Enchantment.BURN, Enchantment.BLAZE_POWDER, Enchantment.FROZEN_DEEP,
    Enchantment.DRAGON_LEGEND, Enchantment.ENDLESS_GREED, Enchantment.RAIN_FIRE, Enchantment.WITHER_ROSE,
    Enchantment.LAVA, Enchantment.TELESCOPE, Enchantment.FIRE_ARROW, Enchantment.PULSE_SHIELD,
]

NON_REPEATABLE_ENCHANTMENTS = {Enchantment.DENSE, Enchantment.WIND_BURST}

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

EMERALD_PER_WAVE_BY_LEVEL = {11: 1, 12: 1, 13: 2, 14: 2, 15: 3}



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
    NAUTILUS = 12
    IRON_NAUTILUS = 13
    GOLD_NAUTILUS = 14
    DIAMOND_NAUTILUS = 15
    NETHERITE_NAUTILUS = 16
    MAGMA_CUBE = 17
    MAGMA_CUBE_SMALL = 18
    HEROBRINE = 19
    LICH = 20
    CREEPER = 21
    CHARGED_CREEPER = 22
    SPIDER = 23


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
    "NAUTILUS": {"image": "nautilus.png", "speed": 2, "health": 100, "reward": 10},
    "IRON_NAUTILUS": {"image": "iron_nautilus.png", "speed": 1.2, "health": 250, "reward": 35},
    "GOLD_NAUTILUS": {"image": "gold_nautilus.png", "speed": 1.2, "health": 250, "reward": 35},
    "DIAMOND_NAUTILUS": {"image": "diamond_nautilus.png", "speed": 1.2, "health": 300, "reward": 40},
    "NETHERITE_NAUTILUS": {"image": "netherite_nautilus.png", "speed": 1.2, "health": 300, "reward": 50},
    "MAGMA_CUBE": {"image": "magma_cube.png", "speed": 2.0, "health": 180, "reward": 25},
    "MAGMA_CUBE_SMALL": {"image": "magma_cube.png", "speed": 3.0, "health": 90, "reward": 10},
    "LICH": {"image": "lich.png", "speed": 3, "health": 500, "reward": 40},
    "CREEPER": {"image": "creeper.png", "speed": 2, "health": 100, "reward": 20},
    "CHARGED_CREEPER": {"image": "charged_creeper.png", "speed": 2, "health": 100, "reward": 20},
    "SPIDER": {"image": "spider.png", "speed": 4, "health": 100, "reward": 20},
}
