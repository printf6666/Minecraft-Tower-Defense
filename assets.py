import pygame
import sys
import os
from config import TowerType

ASSET_CACHE = {}


def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)


def load_image(path, size=None):
    key = (path, size)
    if key not in ASSET_CACHE:
        img = pygame.image.load(resource_path(path)).convert_alpha()
        if size:
            img = pygame.transform.smoothscale(img, size)
        ASSET_CACHE[key] = img
    return ASSET_CACHE[key]


font_large = None
font_medium = None
font_small = None
font_tower_level = None
font_damage = None

tower_icons = []

tnt_explosion_frames = []
mushroom_cloud_frames = []

icon0 = None
icon1 = None
icon2 = None
icon3 = None
icon4 = None
icon5 = None
icon6 = None
icon7 = None
icon8 = None
icon9 = None
icon10 = None

gold_img = None
heart_img = None

BUFF_SIZE = 32
buff_icons = {}
shield_img = None

white_lightning_frames = []
golden_lightning_frames = []

white_lightning_h_frames = []
golden_lightning_h_frames = []

bgm_files = []
bgm_index = -1

rain_cache = {}
acid_rain_cache = {}
snow_cache = {}
fire_cache = {}

stone_img = None
dirt_img = None
start_img = None
house_img = None
gold_ore_img = None
blackstone_img = None
soul_sand_img = None
gilded_blackstone_img = None
command_block_img = None

ice_dragon_img = None
fire_dragon_img = None
electric_dragon_img = None

explode_sound = None
level_up_sound = None
teleport_sound = None


def init_assets():
    global font_large, font_medium, font_small, font_tower_level, font_damage
    global icon0, icon1, icon2, icon3, icon4, icon5, icon6, icon7, icon8, icon9, icon10, tower_icons, buff_icons
    global gold_img, heart_img, clock_img
    global white_lightning_frames, golden_lightning_frames
    global white_lightning_h_frames, golden_lightning_h_frames
    global bgm_files, bgm_index
    global stone_img, dirt_img, start_img, house_img, gold_ore_img
    global tnt_explosion_frames, mushroom_cloud_frames, contaminated_img
    global explode_sound, level_up_sound


    font_large = pygame.font.Font(resource_path("font/Minecraft.ttf"), 60)
    font_medium = pygame.font.Font(resource_path("font/Minecraft.ttf"), 48)
    font_small = pygame.font.Font(resource_path("font/Minecraft.ttf"), 36)
    font_tower_level = pygame.font.Font(resource_path("font/Minecraft.ttf"), 28)
    font_damage = pygame.font.Font(resource_path("font/Minecraft.ttf"), 36)


    icon_size = 100
    tower_icons.clear()
    for ttype in TowerType:
        try:
            tower_icons.append(load_image(f"tower/{ttype.value}-1.png", (icon_size, icon_size)))
        except:
            tower_icons.append(pygame.Surface((icon_size, icon_size)))
    icon0, icon1, icon2, icon3, icon4, icon5, icon6, icon7, icon8, icon9, icon10 = tower_icons

    global tnt_explosion_frames
    tnt_explosion_frames.clear()
    for i in range(1, 6):
        try:
            tnt_explosion_frames.append(load_image(f"tower/tnt{i}.png", (350, 350)))
        except:
            tnt_explosion_frames.append(pygame.Surface((350, 350)))


    global mushroom_cloud_frames
    mushroom_cloud_frames.clear()
    try:
        sheet = load_image("tower/mushroom_cloud.png")
        fw = sheet.get_width() // 5
        fh = sheet.get_height() // 2
        for row in range(2):
            for col in range(5):
                frame = sheet.subsurface((col * fw, row * fh, fw, fh))
                frame = pygame.transform.smoothscale(frame, (800, 1000))
                mushroom_cloud_frames.append(frame)
    except:
        pass

    gold_img = load_image("tower/2-1.png", (64, 64))
    heart_img = load_image("tower/heart.png", (128, 128))

    buff_icons["burn"] = load_image("debuff/burn.png", (BUFF_SIZE, BUFF_SIZE))
    buff_icons["slow"] = load_image("debuff/slow.png", (BUFF_SIZE, BUFF_SIZE))
    buff_icons["broken"] = load_image("debuff/broken.png", (BUFF_SIZE, BUFF_SIZE))
    buff_icons["poison"] = load_image("debuff/poison.png", (BUFF_SIZE, BUFF_SIZE))
    buff_icons["wind"] = load_image("debuff/wind.png", (BUFF_SIZE, BUFF_SIZE))
    buff_icons["speed"] = load_image("debuff/speed.png", (BUFF_SIZE, BUFF_SIZE))
    buff_icons["wither"] = load_image("debuff/wither.png", (BUFF_SIZE, BUFF_SIZE))
    buff_icons["soul_burn"] = load_image("debuff/soul_burn.png", (BUFF_SIZE, BUFF_SIZE))
    global shield_img
    shield_img = load_image("tower/shield.png", (128, 128))

    try:
        sheet = load_image("tower/white_lightning.png")
    except:
        sheet = None
    if sheet:
        frame_w = sheet.get_width() // 5
        frame_h = sheet.get_height()
        for i in range(5):
            frame = sheet.subsurface((i * frame_w, 0, frame_w, frame_h))
            frame = pygame.transform.smoothscale(frame, (128, 1280))
            white_lightning_frames.append(frame)
        for i in range(5):
            raw = sheet.subsurface((i * frame_w, 0, frame_w, frame_h))
            h_raw = pygame.transform.rotate(raw, -90)
            h_frame = pygame.transform.smoothscale(h_raw, (2048, 128))
            white_lightning_h_frames.append(h_frame)

    try:
        sheet = load_image("tower/golden_lightning.png")
    except:
        sheet = None
    if sheet:
        frame_w = sheet.get_width() // 5
        frame_h = sheet.get_height()
        for i in range(5):
            frame = sheet.subsurface((i * frame_w, 0, frame_w, frame_h))
            frame = pygame.transform.smoothscale(frame, (128, 1280))
            golden_lightning_frames.append(frame)
        for i in range(5):
            raw = sheet.subsurface((i * frame_w, 0, frame_w, frame_h))
            h_raw = pygame.transform.rotate(raw, -90)
            h_frame = pygame.transform.smoothscale(h_raw, (2048, 128))
            golden_lightning_h_frames.append(h_frame)

    global bgm_files, bgm_index
    bgm_dir = resource_path("bgm")
    if os.path.isdir(bgm_dir):
        for f in os.listdir(bgm_dir):
            if f.lower().endswith(('.mp3', '.ogg', '.wav')):
                bgm_files.append(f"bgm/{f}")
    bgm_index = -1

    global explode_sound, level_up_sound, teleport_sound
    try:
        explode_sound = pygame.mixer.Sound(resource_path("sound/explode.mp3"))
    except:
        explode_sound = None
    try:
        level_up_sound = pygame.mixer.Sound(resource_path("sound/level_up.mp3"))
    except:
        level_up_sound = None
    try:
        teleport_sound = pygame.mixer.Sound(resource_path("sound/teleport.mp3"))
    except:
        teleport_sound = None

    ts = (128, 128)
    stone_img = load_image("tower/stone.png", ts)
    dirt_img = load_image("tower/dirt.png", ts)
    start_img = load_image("tower/start.png", ts)
    house_img = load_image("tower/house.png", ts)
    try:
        gold_ore_img = load_image("tower/gold_ore.png", ts)
    except:
        gold_ore_img = pygame.Surface(ts)
        gold_ore_img.fill((255, 200, 0))

    global blackstone_img, soul_sand_img, gilded_blackstone_img
    try:
        blackstone_img = load_image("tower/blackstone.png", ts)
    except:
        blackstone_img = pygame.Surface(ts)
        blackstone_img.fill((45, 45, 45))
    try:
        soul_sand_img = load_image("tower/soul_sand.png", ts)
    except:
        soul_sand_img = pygame.Surface(ts)
        soul_sand_img.fill((139, 90, 43))
    try:
        gilded_blackstone_img = load_image("tower/gilded_blackstone.png", ts)
    except:
        gilded_blackstone_img = pygame.Surface(ts)
        gilded_blackstone_img.fill((45, 45, 45))
        pygame.draw.rect(gilded_blackstone_img, (255, 215, 0), (40, 40, 48, 48))

    global command_block_img
    try:
        command_block_img = load_image("enemy/command_block.png", ts)
    except:
        command_block_img = pygame.Surface(ts)
        command_block_img.fill((0, 0, 139))

    global ice_dragon_img, fire_dragon_img, electric_dragon_img
    try:
        ice_dragon_img = load_image("tower/ice_dragon.png", (256, 256))
    except:
        ice_dragon_img = pygame.Surface((256, 256))
        ice_dragon_img.fill((100, 150, 255))
    try:
        fire_dragon_img = load_image("tower/fire_dragon.png", (256, 256))
    except:
        fire_dragon_img = pygame.Surface((256, 256))
        fire_dragon_img.fill((255, 100, 0))
    try:
        electric_dragon_img = load_image("tower/electric_dragon.png", (256, 256))
    except:
        electric_dragon_img = pygame.Surface((256, 256))
        electric_dragon_img.fill((255, 255, 0))
