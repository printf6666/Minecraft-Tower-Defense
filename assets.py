import pygame
import sys
import os

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

icon1 = None
icon2 = None
icon3 = None
icon4 = None
icon5 = None
icon6 = None
icon7 = None
icon8 = None

gold_img = None
heart_img = None
clock_img = None

BUFF_SIZE = 32
buff_icons = {}

white_lightning_frames = []
golden_lightning_frames = []

white_lightning_h_frames = []
golden_lightning_h_frames = []

bgm_files = []
bgm_index = -1

stone_img = None
dirt_img = None
start_img = None
house_img = None


def init_assets():
    global font_large, font_medium, font_small, font_tower_level, font_damage
    global icon1, icon2, icon3, icon4, icon5, icon6, icon7, icon8, buff_icons
    global gold_img, heart_img, clock_img
    global white_lightning_frames, golden_lightning_frames
    global white_lightning_h_frames, golden_lightning_h_frames
    global bgm_files, bgm_index
    global stone_img, dirt_img, start_img, house_img

    try:
        font_large = pygame.font.Font(resource_path("font/Minecraft.ttf"), 60)
        font_medium = pygame.font.Font(resource_path("font/Minecraft.ttf"), 48)
        font_small = pygame.font.Font(resource_path("font/Minecraft.ttf"), 36)
        font_tower_level = pygame.font.Font(resource_path("font/Minecraft.ttf"), 28)
    except:
        font_large = pygame.font.SysFont('arial', 60)
        font_medium = pygame.font.SysFont('arial', 48)
        font_small = pygame.font.SysFont('arial', 36)
        font_tower_level = pygame.font.SysFont('arial', 28)

    try:
        font_damage = pygame.font.Font(resource_path("font/Minecraft.ttf"), 36)
    except:
        font_damage = font_small

    icon_size = 80
    icon1 = load_image("tower/1.png", (icon_size, icon_size))
    icon2 = load_image("tower/2.png", (icon_size, icon_size))
    icon3 = load_image("tower/3.png", (icon_size, icon_size))
    icon4 = load_image("tower/4.png", (icon_size, icon_size))
    icon5 = load_image("tower/5.png", (icon_size, icon_size))
    icon6 = load_image("tower/6.png", (icon_size, icon_size))
    icon7 = load_image("tower/7.png", (icon_size, icon_size))
    icon8 = load_image("tower/8.png", (icon_size, icon_size))

    gold_img = load_image("tower/gold.png", (64, 64))
    heart_img = load_image("tower/heart.png", (48, 48))
    clock_img = load_image("tower/clock.png", (48, 48))

    buff_icons["burn"] = load_image("debuff/burn.png", (BUFF_SIZE, BUFF_SIZE))
    buff_icons["freeze"] = load_image("debuff/freeze.png", (BUFF_SIZE, BUFF_SIZE))
    buff_icons["slow"] = load_image("debuff/slow.png", (BUFF_SIZE, BUFF_SIZE))
    buff_icons["broken"] = load_image("debuff/broken.png", (BUFF_SIZE, BUFF_SIZE))
    buff_icons["stun"] = load_image("debuff/stun.png", (BUFF_SIZE, BUFF_SIZE))
    buff_icons["poison"] = load_image("debuff/poison.png", (BUFF_SIZE, BUFF_SIZE))
    buff_icons["wind"] = load_image("debuff/wind.png", (BUFF_SIZE, BUFF_SIZE))
    buff_icons["speed"] = load_image("debuff/speed.png", (BUFF_SIZE, BUFF_SIZE))

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

    ts = (128, 128)
    stone_img = load_image("tower/stone.png", ts)
    dirt_img = load_image("tower/dirt.png", ts)
    start_img = load_image("tower/start.png", ts)
    house_img = load_image("tower/house.png", ts)
