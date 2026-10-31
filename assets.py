import pygame
import sys
import os
from config import (TowerType, Enchantment, ENCHANT_ICON_SIZE, TILE_SIZE,
                    BAGUA_SIZE, BAGUA_ALPHA)

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
mushroom_cloud_wither_frames = []   # 凋零核弹配色
mushroom_cloud_ice_frames = []      # 冰冻核弹配色
endless_greed_frames = []
ice_explosion_frames = []
# 共振风暴序列：raw 是原尺寸（282x282），雷神之锤命中爆裂直接用它、不缩放；
# frames 是放大 4 倍的版本，给全屏规模的共振风暴用。
resonance_storm_raw_frames = []
resonance_storm_frames = []

gold_img = None
emerald_img = None

enchantment_icons = {}
enchantment_icons_raw = {}
trader_img = None
ember_meteor_img = None

BUFF_SIZE = 32
buff_icons = {}
bagua_img = None
bagua_img_fx = None
charm_img = None        # 魅惑标记：粉色半透明底 + 空心爱心（预渲染，直接 blit）
lock_img = None         # 锁定标记：紫色半透明底 + 紫色 X（预渲染，直接 blit）
sacred_fire_img = None  # 圣火标记：橙色半透明底 + 火焰标志（阿尔法下界技能，预渲染）
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
netherrack_img = None       # 阿尔法 P2 下界：石头
glowstone_img = None        # 阿尔法 P2 下界：道路
nether_gold_ore_img = None  # 阿尔法 P2 下界：金矿石
end_stone_img = None        # 阿尔法 P3 末地：石头
end_gold_ore_img = None     # 阿尔法 P3 末地：金矿石
obsidian_img = None         # 阿尔法 P3 末地：道路
command_block_img = None
world_seed_img = None   # 阿尔法核心贴图（程序化 BOSS 外观 + 图鉴用）
ice_wall_img = None
bee_img = None
unstable_crystal_img = None
ice_star_img = None          # 神锅的冰系四芒星子弹

ice_dragon_img = None
fire_dragon_img = None
electric_dragon_img = None

explode_sound = None
level_up_sound = None
teleport_sound = None
trader_accept_sound = None
# 音效扩容（命名约定见 docs/音效接线清单 或工作日志）：
# 缺文件时保持 None，audio.play_sound / play_sound_cool 会静默跳过，
# 补素材后无需再改任何代码。
click_sound = None              # 通用按钮 / 选塔
place_sound = None              # 放置炮塔
sell_sound = None               # 出售炮塔
buy_sound = None                # 商店购买
ultimate_sound = None           # 大招施放
game_over_sound = None          # 漏怪失败
victory_sound = None            # 通关
layer_break_sound = None        # BOSS 破层「崩解」
phase_change_sound = None       # 阿尔法转阶段「世界重生成」
fill_sound = None               # /fill 命令方块落地
execute_sound = None            # /execute 落雷
charm_sound = None              # /effect 魅惑
portal_sound = None             # 传送门召唤
reload_sound = None             # /reload 世界重载 & /stop 停服读条
sacred_fire_sound = None        # 圣火附着
thunder_sound = None            # 雷暴落雷
fireball_sound = None           # 恶魂火球
tower_destroyed_sound = None    # 炮塔被 BOSS 抹除


def init_assets():
    global font_large, font_medium, font_small, font_tower_level, font_damage
    global tower_icons, buff_icons
    global gold_img, clock_img, emerald_img
    global white_lightning_frames, golden_lightning_frames
    global white_lightning_h_frames, golden_lightning_h_frames
    global bgm_files, bgm_index
    global stone_img, dirt_img, start_img, house_img, gold_ore_img
    global tnt_explosion_frames, mushroom_cloud_frames, contaminated_img
    global ice_explosion_frames
    global explode_sound, level_up_sound


    font_large = pygame.font.Font(resource_path("Minecraft.ttf"), 60)
    font_medium = pygame.font.Font(resource_path("Minecraft.ttf"), 48)
    font_small = pygame.font.Font(resource_path("Minecraft.ttf"), 36)
    font_tower_level = pygame.font.Font(resource_path("Minecraft.ttf"), 28)
    font_damage = pygame.font.Font(resource_path("Minecraft.ttf"), 36)


    icon_size = 100
    tower_icons.clear()
    for ttype in TowerType:
        try:
            # 统一命名规则：tower/{塔序号}-{阶级}-{分支}.png，底栏取一阶分支 1
            tower_icons.append(load_image(f"tower/{ttype.value}-1-1.png", (icon_size, icon_size)))
        except:
            tower_icons.append(pygame.Surface((icon_size, icon_size)))

    global tnt_explosion_frames
    tnt_explosion_frames.clear()
    for i in range(1, 6):
        try:
            tnt_explosion_frames.append(load_image(f"fx/tnt{i}.png", (384, 384)))
        except:
            tnt_explosion_frames.append(pygame.Surface((384, 384)))

    ice_explosion_frames.clear()
    # 冰霜爆破：只用 ice_explosion00~14 共 15 帧（比原始序列少播最后 2 帧）
    for i in range(15):
        try:
            ice_explosion_frames.append(load_image(f"fx/ice_explosion{i:02d}.png"))
        except:
            pass

    global resonance_storm_frames, resonance_storm_raw_frames
    resonance_storm_frames.clear()
    resonance_storm_raw_frames.clear()
    for i in range(1, 17):
        try:
            img = load_image(f"fx/resonance_storm{i:02d}.png")
        except Exception:
            # 13~16 已从素材里删掉，加载到 12 帧就自然结束
            break
        resonance_storm_raw_frames.append(img)
        resonance_storm_frames.append(
            pygame.transform.scale(img, (img.get_width() * 4, img.get_height() * 4)))


    global mushroom_cloud_frames, endless_greed_frames
    global mushroom_cloud_wither_frames, mushroom_cloud_ice_frames

    def _load_cloud_sheet(path):
        """切 5x2 图集 -> 10 帧，最近邻放大到 800x1000。

        像素画必须用 scale（最近邻），smoothscale 会把 8x8 像素块插值糊掉。
        """
        frames = []
        try:
            sheet = load_image(path)
        except Exception:
            return frames
        fw = sheet.get_width() // 5
        fh = sheet.get_height() // 2
        for row in range(2):
            for col in range(5):
                frame = sheet.subsurface((col * fw, row * fh, fw, fh))
                frames.append(pygame.transform.scale(frame, (800, 1000)))
        return frames

    mushroom_cloud_frames.clear()
    mushroom_cloud_frames.extend(_load_cloud_sheet("fx/mushroom_cloud.png"))
    mushroom_cloud_wither_frames = _load_cloud_sheet("fx/mushroom_cloud_wither.png") \
        or list(mushroom_cloud_frames)
    mushroom_cloud_ice_frames = _load_cloud_sheet("fx/mushroom_cloud_ice.png") \
        or list(mushroom_cloud_frames)


    endless_greed_frames.clear()
    for n in range(1, 21):
        endless_greed_frames.append(load_image(f"fx/star{n:02d}.png"))

    gold_img = load_image("tower/2-1-1.png", (64, 64))
    emerald_img = load_image("tower/emerald.png", (80, 80))

    global enchantment_icons, enchantment_icons_raw, trader_img
    enchantment_icons.clear()
    enchantment_icons_raw.clear()
    for ench in Enchantment:
        try:
            enchantment_icons_raw[ench] = load_image(f"enchantment/{ench.value}.png")
        except:
            enchantment_icons_raw[ench] = None
        try:
            enchantment_icons[ench] = load_image(f"enchantment/{ench.value}.png", (ENCHANT_ICON_SIZE, ENCHANT_ICON_SIZE))
        except:
            s = pygame.Surface((ENCHANT_ICON_SIZE, ENCHANT_ICON_SIZE))
            s.fill((80, 80, 80))
            enchantment_icons[ench] = s
            enchantment_icons_raw[ench] = s
    try:
        trader_img = load_image("tower/trader.png")
    except:
        trader_img = None

    global ember_meteor_img
    try:
        ember_meteor_img = load_image("enchantment/23.png", (640, 640))
    except:
        ember_meteor_img = None

    buff_icons["burn"] = load_image("debuff/burn.png", (BUFF_SIZE, BUFF_SIZE))
    buff_icons["slow"] = load_image("debuff/slow.png", (BUFF_SIZE, BUFF_SIZE))
    buff_icons["broken"] = load_image("debuff/broken.png", (BUFF_SIZE, BUFF_SIZE))
    buff_icons["ice_broken"] = load_image("debuff/ice_broken.png", (BUFF_SIZE, BUFF_SIZE))
    buff_icons["poison"] = load_image("debuff/poison.png", (BUFF_SIZE, BUFF_SIZE))
    buff_icons["wind"] = load_image("debuff/wind.png", (BUFF_SIZE, BUFF_SIZE))
    buff_icons["speed"] = load_image("debuff/speed.png", (BUFF_SIZE, BUFF_SIZE))
    buff_icons["wither"] = load_image("debuff/wither.png", (BUFF_SIZE, BUFF_SIZE))
    # soul_burn 机制已删除，图标也已移除（曾导致启动即 FileNotFoundError）

    # 卧龙的八卦阵（太极图，已抠掉棋盘格背景）
    # 炮塔状态标记（128x128，尺寸和 TILE_SIZE 一致，所以不缩放，避免把描边磨糊）
    global charm_img, lock_img, sacred_fire_img
    try:
        charm_img = load_image("fx/charm.png")
    except Exception:
        charm_img = None
    try:
        lock_img = load_image("fx/lock.png")
    except Exception:
        lock_img = None
    try:
        sacred_fire_img = load_image("fx/sacred_fire.png")
    except Exception:
        sacred_fire_img = None

    global bagua_img, bagua_img_fx
    try:
        bagua_img = load_image("fx/bagua.png", (BAGUA_SIZE, BAGUA_SIZE))
        # 实际画到场景里的版本：预乘不透明度（需求：80%）
        bagua_img_fx = bagua_img.copy()
        bagua_img_fx.fill((255, 255, 255, BAGUA_ALPHA), special_flags=pygame.BLEND_RGBA_MULT)
    except Exception:
        bagua_img = None
        bagua_img_fx = None
    global shield_img
    shield_img = load_image("fx/shield.png", (128, 128))

    try:
        sheet = load_image("fx/white_lightning.png")
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
        sheet = load_image("fx/golden_lightning.png")
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

    global explode_sound, level_up_sound, teleport_sound, trader_accept_sound
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
    try:
        trader_accept_sound = pygame.mixer.Sound(resource_path("sound/trader_accept.ogg"))
    except:
        trader_accept_sound = None

    # 音效扩容批量挂载：缺文件自动跳过（保持 None），素材就位即自动生效
    global click_sound, place_sound, sell_sound, buy_sound, ultimate_sound
    global game_over_sound, victory_sound
    global layer_break_sound, phase_change_sound, fill_sound, execute_sound
    global charm_sound, portal_sound, reload_sound, sacred_fire_sound
    global thunder_sound, fireball_sound, tower_destroyed_sound

    def _load_snd(filename):
        # 依次尝试 .ogg / .mp3 / .wav：素材是什么格式就丢什么文件名
        base = filename.rsplit(".", 1)[0]
        for ext in (".ogg", ".mp3", ".wav"):
            try:
                return pygame.mixer.Sound(resource_path("sound/" + base + ext))
            except Exception:
                continue
        return None

    click_sound = _load_snd("click.ogg")
    place_sound = _load_snd("place.ogg")
    sell_sound = _load_snd("sell.ogg")
    buy_sound = _load_snd("buy.ogg")
    ultimate_sound = _load_snd("ultimate.ogg")
    game_over_sound = _load_snd("game_over.ogg")
    victory_sound = _load_snd("victory.ogg")
    layer_break_sound = _load_snd("layer_break.ogg")
    phase_change_sound = _load_snd("phase_change.ogg")
    fill_sound = _load_snd("fill.ogg")
    execute_sound = _load_snd("execute.ogg")
    charm_sound = _load_snd("charm.ogg")
    portal_sound = _load_snd("portal.ogg")
    reload_sound = _load_snd("reload.ogg")
    sacred_fire_sound = _load_snd("sacred_fire.ogg")
    thunder_sound = _load_snd("thunder.ogg")
    fireball_sound = _load_snd("fireball.ogg")
    tower_destroyed_sound = _load_snd("tower_destroyed.ogg")

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

    # 阿尔法群系改写地形贴图（P2 下界 / P3 末地）
    global netherrack_img, glowstone_img, nether_gold_ore_img
    global end_stone_img, end_gold_ore_img, obsidian_img
    try:
        netherrack_img = load_image("tower/netherrack.png", ts)
    except:
        netherrack_img = pygame.Surface(ts)
        netherrack_img.fill((111, 54, 52))
    try:
        glowstone_img = load_image("tower/glowstone.png", ts)
    except:
        glowstone_img = pygame.Surface(ts)
        glowstone_img.fill((144, 116, 66))
        pygame.draw.rect(glowstone_img, (246, 208, 121), (24, 24, 80, 80))
    try:
        nether_gold_ore_img = load_image("tower/nether_gold_ore.png", ts)
    except:
        nether_gold_ore_img = pygame.Surface(ts)
        nether_gold_ore_img.fill((111, 54, 52))
        pygame.draw.rect(nether_gold_ore_img, (255, 215, 0), (40, 40, 48, 48))
    try:
        end_stone_img = load_image("tower/end_stone.png", ts)
    except:
        end_stone_img = pygame.Surface(ts)
        end_stone_img.fill((221, 223, 165))
    try:
        end_gold_ore_img = load_image("tower/end_gold_ore.png", ts)
    except:
        end_gold_ore_img = pygame.Surface(ts)
        end_gold_ore_img.fill((221, 223, 165))
        pygame.draw.rect(end_gold_ore_img, (255, 215, 0), (40, 40, 48, 48))
    try:
        obsidian_img = load_image("tower/obsidian.png", ts)
    except:
        # tower/obsidian.png 暂缺时用程序生成的深紫黑底兜底，
        # 放入正式素材后自动替换
        obsidian_img = pygame.Surface(ts)
        obsidian_img.fill((15, 8, 26))
        for i in range(-128, 128, 32):
            pygame.draw.line(obsidian_img, (46, 22, 74), (i, 0), (i + 128, 128), 5)
        pygame.draw.rect(obsidian_img, (86, 44, 130), (20, 20, 88, 88), 3)

    global command_block_img
    try:
        command_block_img = load_image("enemy/command_block.png", ts)
    except:
        command_block_img = pygame.Surface(ts)
        command_block_img.fill((0, 0, 139))

    global world_seed_img
    try:
        world_seed_img = load_image("enemy/world_seed.png")
    except:
        world_seed_img = None

    global ice_wall_img
    try:
        ice_wall_img = load_image("tower/ice_wall.png", ts)
    except:
        ice_wall_img = pygame.Surface(ts)
        ice_wall_img.fill((150, 200, 255))

    global bee_img
    try:
        bee_img = load_image("tower/bee.png", (100, 100))
    except:
        bee_img = pygame.Surface((80, 80), pygame.SRCALPHA)
        pygame.draw.circle(bee_img, (255, 200, 0), (40, 40), 30)

    global unstable_crystal_img
    try:
        unstable_crystal_img = load_image("enchantment/26.png", (TILE_SIZE, TILE_SIZE))
    except:
        unstable_crystal_img = pygame.Surface((TILE_SIZE, TILE_SIZE), pygame.SRCALPHA)
        pygame.draw.rect(unstable_crystal_img, (178, 0, 255),
                         (16, 16, TILE_SIZE - 32, TILE_SIZE - 32))

    global ice_star_img
    try:
        # 素材本身就是 96x96（32 像素原稿的 3 倍整数放大），不再二次缩放，保住像素边
        ice_star_img = load_image("fx/ice_star.png")
    except:
        ice_star_img = pygame.Surface((HOLY_POT_BOLT_SIZE, HOLY_POT_BOLT_SIZE), pygame.SRCALPHA)
        pygame.draw.polygon(ice_star_img, (150, 220, 255), [
            (HOLY_POT_BOLT_SIZE // 2, 0), (HOLY_POT_BOLT_SIZE, HOLY_POT_BOLT_SIZE // 2),
            (HOLY_POT_BOLT_SIZE // 2, HOLY_POT_BOLT_SIZE), (0, HOLY_POT_BOLT_SIZE // 2)])

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
