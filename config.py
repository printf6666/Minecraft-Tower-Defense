from enum import Enum

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


class TowerType(Enum):
    PHYSICAL = 0
    PRODUCTION = 1
    ICE = 2
    TELEPORT = 3
    FLAME = 4
    TRIDENT = 5
    WIND = 6
    POISON = 7
    BOMB = 8
    WITHER = 9


class BombSubType(Enum):
    SNOW = 0
    ICE = 1
    FLAME = 2
    POISON = 3
    WITHER_TNT = 4


class EnemyType(Enum):
    NORMAL = 0
    FAST = 1
    TANK = 2
    ELITE = 3
    BOSS = 4
    ARMORED = 5
    SLIME = 6
    SLIMELING = 7
    GOLD_ARMORED = 8
    GHOST = 9
    DIAMOND_ARMORED = 10
    ENDLESS_ARMORED = 11


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


WEATHER_CONFIG = {
    Weather.EXTREME_HEAT: {"name": "酷暑", "temp": 40, "desc": "酷暑：温度较高，火焰伤害提升", "color": (255, 69, 0)},
    Weather.SUNNY: {"name": "晴天", "temp": 30, "desc": "晴天：温度适中", "color": (255, 255, 255)},
    Weather.CLOUDY: {"name": "多云", "temp": 20, "desc": "多云：温度较低", "color": (180, 180, 180)},
    Weather.RAINY: {"name": "雨天", "temp": 10, "desc": "雨天：温度较低，敌人行动变慢", "color": (100, 150, 255)},
    Weather.SNOWY: {"name": "雪天", "temp": 0, "desc": "雪天：温度骤降，敌人冻结时间延长", "color": (150, 200, 255)},
    Weather.THUNDERSTORM: {"name": "雷暴", "temp": 15, "desc": "雷暴：温度较低，闪电将会劈下", "color": (255, 215, 0)},
    Weather.ACID_RAIN: {"name": "酸雨", "temp": 5, "desc": "酸雨：敌人中毒，炮塔等级-1，中毒伤害翻倍", "color": (0, 255, 0)},
    Weather.TAILWIND: {"name": "顺风", "temp": 25, "desc": "顺风：敌人移速+50%，炮塔射程+50%", "color": (152, 255, 152)},
    Weather.HEADWIND: {"name": "逆风", "temp": 25, "desc": "逆风：敌人移速-50%，炮塔射程-50%", "color": (152, 255, 152)},
    Weather.SCORCHING_SUN: {"name": "烈日", "temp": 50, "desc": "烈日：温度极高，敌人全体燃烧", "color": (255, 200, 0)},
    Weather.FOG: {"name": "迷雾", "temp": 15, "desc": "迷雾：视野遮挡", "color": (180, 180, 180)},
    Weather.EXTREME_COLD: {"name": "极寒", "temp": -20, "desc": "极寒：冻结时间翻倍，敌人移速-50%", "color": (100, 200, 255)},
    Weather.MAGNETIC_STORM: {"name": "磁暴", "temp": 20, "desc": "磁暴：闪电伤害翻倍，传送失效，金属敌人破甲", "color": (0, 255, 255)},
    Weather.FIRE_RAIN: {"name": "火雨", "temp": 100, "desc": "火雨：敌人持续燃烧，无法冻结", "color": (255, 69, 0)},
}

ENEMY_TYPES = {
    "NORMAL": {"image": "normal.png", "speed": 2, "health": 100, "reward": 10},
    "FAST": {"image": "fast.png", "speed": 3.5, "health": 100, "reward": 15},
    "TANK": {"image": "tank.png", "speed": 1.5, "health": 300, "reward": 30},
    "ELITE": {"image": "elite.png", "speed": 2.5, "health": 200, "reward": 40},
    "BOSS": {"image": "boss.png", "speed": 2, "health": 800, "reward": 100},
    "ARMORED": {"image": "armored.png", "speed": 1.2, "health": 250, "reward": 35},
    "SLIME": {"image": "slime.png", "speed": 2.0, "health": 180, "reward": 25},
    "SLIMELING": {"image": "slime.png", "speed": 3.0, "health": 90, "reward": 10},
    "GOLD_ARMORED": {"image": "gold_armored.png", "speed": 1.2, "health": 250, "reward": 35},
    "GHOST": {"image": "ghost.png", "speed": 3, "health": 100, "reward": 25},
    "DIAMOND_ARMORED": {"image": "diamond_armored.png", "speed": 1.2, "health": 300, "reward": 40},
    "ENDLESS_ARMORED": {"image": "endless_armored.png", "speed": 1.2, "health": 300, "reward": 50},
}
