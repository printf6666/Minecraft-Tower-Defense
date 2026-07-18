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
    (TowerType.SHIELD,     "盾塔", 275,  pygame.K_0),
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

class BombSubType(Enum):
    SNOW = 1
    ICE = 2
    FLAME = 3
    POISON = 4
    WITHER_TNT = 5



class EnemyType(Enum):
    NORMAL = 0
    FAST = 1
    TANK = 2
    ELITE = 3
    BOSS = 4
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
    Weather.EXTREME_HEAT: {"name": "酷暑", "temp": 40, "desc": "酷暑：温度较高，火焰伤害提升", "color": (255, 69, 0)},
    Weather.SUNNY: {"name": "晴天", "temp": 30, "desc": "晴天：温度适中", "color": (255, 255, 255)},
    Weather.CLOUDY: {"name": "多云", "temp": 20, "desc": "多云：温度较低", "color": (180, 180, 180)},
    Weather.RAINY: {"name": "雨天", "temp": 10, "desc": "雨天：温度较低，敌人移速-50%，无法点燃", "color": (100, 150, 255)},
    Weather.SNOWY: {"name": "雪天", "temp": 0, "desc": "雪天：温度骤降", "color": (150, 200, 255)},
    Weather.THUNDERSTORM: {"name": "雷暴", "temp": 15, "desc": "雷暴：温度较低，闪电将会劈下", "color": (255, 215, 0)},
    Weather.ACID_RAIN: {"name": "酸雨", "temp": 5, "desc": "酸雨：敌人中毒，炮塔等级-1，中毒伤害翻倍", "color": (0, 255, 0)},
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
    "FAST": {"image": "fast.png", "speed": 3.5, "health": 100, "reward": 15},
    "TANK": {"image": "tank.png", "speed": 1.5, "health": 300, "reward": 30},
    "ELITE": {"image": "elite.png", "speed": 2.5, "health": 200, "reward": 40},
    "BOSS": {"image": "boss.png", "speed": 2, "health": 800, "reward": 100},
    "HEROBRINE": {"image": "herobrine.png", "speed": 3, "health": 5000000, "reward": 1600},
    "IRON_ARMORED": {"image": "iron_armored.png", "speed": 1.2, "health": 250, "reward": 35},
    "SLIME": {"image": "slime.png", "speed": 2.0, "health": 180, "reward": 25},
    "SLIMELING": {"image": "slime.png", "speed": 3.0, "health": 90, "reward": 10},
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
}
