import pygame
import random
import math
import json
import sys
import os
import time
from types import SimpleNamespace
import assets
import audio
from config import *
from enemy import Enemy, DamageText
from tower import Tower, Bullet, BombBullet, NuclearMissile, WitherBullet, MAP_CENTER_X, MAP_CENTER_Y
from effects import WindExplosion, IceExplosion, DragonBreathPool, LightningEffect, HorizontalLightningEffect, PoisonSplash, TNTExplosion, MushroomExplosion, NuclearShockwave, WitherSplash, EndlessGreedExplosion, ResonanceStorm, Meteor, Bee, UnstableCrystal, LanternShockwave, IceStarBurst, MasterpieceShockwave, BaguaArray
from video_player import UltimateVideo
from wave_manager import WaveManager
from ui import UIManager, get_tower_info
from codex import Codex
from dragons import Dragon
import stats
from final_boss import (FinalBoss, BossShockwave, BossRune, BossPortal,
                        BossStrike, DeleteBeam)

# 伤害属性 -> 对应强化附魔所属的炮塔类型
ELEMENT_TO_TOWER_TYPE = {
    "physical": TowerType.PHYSICAL,
    "fire": TowerType.FLAME,
    "ice": TowerType.ICE,
    "electric": TowerType.TRIDENT,
    "wind": TowerType.WIND,
    "poison": TowerType.POISON,
    "explosion": TowerType.BOMB,
}

WEATHER_POOL = [
    Weather.ACID_RAIN, Weather.EXTREME_HEAT, Weather.SUNNY, Weather.CLOUDY, Weather.RAINY, Weather.SNOWY,
    Weather.THUNDERSTORM, Weather.TAILWIND, Weather.HEADWIND,
    Weather.SCORCHING_SUN, Weather.FOG, Weather.EXTREME_COLD, Weather.MAGNETIC_STORM,
    Weather.FIRE_RAIN, Weather.AURORA,
]


def resource_path(relative_path):
    base_path = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_path, relative_path)


def get_save_path():
    save_dir = os.path.join(os.path.expanduser("~"), "AppData", "LocalLow", "Escoffier", "Minecraft-Tower-Defense")
    try:
        os.makedirs(save_dir, exist_ok=True)
    except Exception:
        pass
    return os.path.join(save_dir, "save.json")


def grid_to_path(grid):
    cells = {(x, y) for y, row in enumerate(grid) for x, v in enumerate(row) if v}
    if not cells:
        return []
    neigh = {c: [(c[0]+dx, c[1]+dy) for dx, dy in ((1,0),(-1,0),(0,1),(0,-1)) if (c[0]+dx, c[1]+dy) in cells] for c in cells}
    start = (0, 0)
    end = (15, 9)
    path = [start]
    visited = {start}
    while path[-1] != end:
        cur = path[-1]
        nxt = [c for c in neigh[cur] if c not in visited]
        if not nxt:
            break
        path.append(nxt[0])
        visited.add(nxt[0])
    return [(x, y + 1) for (x, y) in path]


with open(resource_path("seed.json")) as f:
    SEED_PATHS = [grid_to_path(grid) for grid in json.load(f)["seed_paths"]]


class Game:
    def __init__(self, screen, clock):
        self.state = GameState.MENU
        self.pre_pause_state = None
        self.screen = screen
        self.clock = clock
        self.fps = 60
        self.enemies = pygame.sprite.Group()
        self.towers = pygame.sprite.Group()
        self.bullets = pygame.sprite.Group()
        self.damage_texts = pygame.sprite.Group()
        self.dragons = pygame.sprite.Group()
        self.damage_stats = stats.DamageStats()
        self.damage_element = None
        self.stats_open = False
        self.confirm_reset = 0      # 「重新开始」二次确认倒计时（帧）
        self.coins = 2500
        self.emeralds = 100
        self.wave_manager = WaveManager()
        self.selected_tower_type = None
        self.selected_tower = None
        self.show_range = False
        self.enemies_killed = 0
        self.game_time = 0
        self.gold_per_second = 0
        self.gold_per_wave = 0
        self.emerald_per_wave = 0
        self.last_global_production_time = pygame.time.get_ticks()
        self.temperature = 30
        self.lava_timer = 0
        self.weather = Weather.SUNNY
        self.weather_particles = []
        self.weather_banner_timer = 0
        self.weather_banner_text = ""
        self.pending_first_wave_weather = False
        self.TOWER_DATA = TOWER_DATA

        self.dragon_breath_pools = []
        self.lightning_effects = []
        self.wind_explosions = []
        self.endless_greed_explosions = []
        self.ice_explosions = []
        self.hell_rays = []
        self.resonance_storms = []
        self.poison_splashes = []
        self.wither_splashes = []
        self.horizontal_lightning_effects = []
        self.tnt_explosions = []
        self.creeper_explosions = []
        self.mushroom_explosions = []
        self.shockwave_effects = []
        self.thunderstorm_timer = 0
        self.resonance_counter = 0
        self.masterpiece_counter = 0     # 臻品呈现：场上所有神锅共用的攻击计数
        self.sacrifices = 0
        self.meteors = []
        self.bees = []
        self.bee_spawn_remaining = 0
        self.bee_spawn_timer = 0
        self.crystals = []
        self.lantern_shockwaves = []
        self.stars = []
        self.ice_star_bursts = []
        self.masterpiece_shockwaves = []
        self.bagua_arrays = []
        self.ultimate_video = None
        self.masterpiece_pending = False   # 视频播完才结算，标记「这一发还没落地」
        self._lantern_towers = 0

        self.fog_timer = 0
        self.fog_visible = False

        self.night_dark_timer = 0
        self.herobrine_phase = 0
        self.herobrine_spawned = False
        self.herobrine = None
        self.herobrine_summon_timer = 0
        self.herobrine_summon_queue = []
        self._init_boss_state()

        self.command_block_timer = 0
        self.command_blocks = []
        self.ice_walls = []

        self.enchantments = []
        self.poison_base_damage = 5
        self.shop_offers = []
        self.shop_offers_wave = -1

        self.path = random.choice(SEED_PATHS)
        self.start_point = self.path[0]
        self.end_point = self.path[-1]
        self.background_surface = None
        self.enemy_grid = {}
        self._build_background()

        self.ui_manager = UIManager(self)
        self.codex = Codex(self)

    def _build_background(self, night_mode=False, gold_ore_positions=None):
        gw = GRID_WIDTH * TILE_SIZE
        gh = (GRID_HEIGHT + 1) * TILE_SIZE
        self.background_surface = pygame.Surface((gw, gh))
        self.background_surface.fill(BLACK)
        path_set = set(self.path)

        if night_mode:
            stone_img = assets.blackstone_img
            dirt_img = assets.soul_sand_img
            gold_ore_img = assets.gilded_blackstone_img
        else:
            stone_img = assets.stone_img
            dirt_img = assets.dirt_img
            gold_ore_img = assets.gold_ore_img

        stone_tiles = []
        for x in range(GRID_WIDTH):
            for y in range(1, GRID_HEIGHT + 1):
                if (x, y) not in path_set and (x, y) != self.end_point:
                    stone_tiles.append((x, y))

        if gold_ore_positions is not None:
            self.gold_ore_positions = gold_ore_positions
        else:
            self.gold_ore_positions = set(random.sample(stone_tiles, min(5, len(stone_tiles))))

        for x in range(GRID_WIDTH):
            for y in range(1, GRID_HEIGHT + 1):
                if (x, y) in path_set:
                    self.background_surface.blit(dirt_img, (x * TILE_SIZE, y * TILE_SIZE))
                elif (x, y) in self.gold_ore_positions:
                    self.background_surface.blit(gold_ore_img, (x * TILE_SIZE, y * TILE_SIZE))
                else:
                    self.background_surface.blit(stone_img, (x * TILE_SIZE, y * TILE_SIZE))
        sx, sy = self.start_point
        ex, ey = self.end_point
        self.background_surface.blit(assets.start_img, (sx * TILE_SIZE, sy * TILE_SIZE))
        self.background_surface.blit(assets.house_img, (ex * TILE_SIZE, ey * TILE_SIZE))

    def _build_enemy_grid(self):
        self.enemy_grid.clear()
        for e in self.enemies:
            if e.health <= 0:
                continue
            left = e.rect.left // TILE_SIZE
            right = (e.rect.right - 1) // TILE_SIZE
            top = e.rect.top // TILE_SIZE
            bottom = (e.rect.bottom - 1) // TILE_SIZE
            if left == right and top == bottom:
                col = e.rect.centerx // TILE_SIZE
                row = e.rect.centery // TILE_SIZE
                self.enemy_grid.setdefault((col, row), []).append(e)
            else:
                # 大体型单位（例如最终BOSS）会占据多格，所有覆盖到的格子都要能被打到
                for col in range(left, right + 1):
                    for row in range(top, bottom + 1):
                        self.enemy_grid.setdefault((col, row), []).append(e)

    def quit_game(self):
        if self.state == GameState.SHOP:
            self.save_game()
        pygame.quit()
        sys.exit()

    def handle_game_click(self, mouse_x, mouse_y, grid_x, grid_y):
        """游戏内左键单击：选塔图标 / 无限手套打怪 / 选塔 / 建塔。

        从 handle_events 抽出来的，因为那里还要先处理「重新开始」「退出」
        两个按钮判定，混在一起会让 elif 分支层级变深、容易再把按钮判定
        写到 MENU 分支外面（那正是隐形热区删档 bug 的成因）。
        """
        icon_clicked = None
        for rect, ttype, key_label in self.ui_manager.get_tower_icon_rects():
            if rect.collidepoint(mouse_x, mouse_y):
                icon_clicked = ttype
                break
        if icon_clicked is not None:
            self.selected_tower = None
            self.selected_tower_type = icon_clicked
            self.show_range = False
        elif Enchantment.INFINITY_GAUNTLET in self.enchantments:
            gauntlet_hit = False
            for e in self.enemies:
                if e.health > 0 and e.rect.collidepoint(mouse_x, mouse_y):
                    self.gauntlet_attack(e)
                    gauntlet_hit = True
                    break
            if not gauntlet_hit:
                clicked_tower = self.get_tower_at(grid_x, grid_y)
                if clicked_tower:
                    self.selected_tower = clicked_tower
                    self.selected_tower_type = None
                    self.show_range = True
                else:
                    self.selected_tower = None
                    self.show_range = False
                    if self.selected_tower_type and self.can_build_tower(grid_x, grid_y):
                        self.build_tower(grid_x, grid_y, self.selected_tower_type)
        else:
            clicked_tower = self.get_tower_at(grid_x, grid_y)
            if clicked_tower:
                self.selected_tower = clicked_tower
                self.selected_tower_type = None
                self.show_range = True
            else:
                self.selected_tower = None
                self.show_range = False
                if self.selected_tower_type and self.can_build_tower(grid_x, grid_y):
                    self.build_tower(grid_x, grid_y, self.selected_tower_type)

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.quit_game()

            # 图鉴是全屏模态：打开时吞掉所有输入
            if self.codex.open:
                self.codex.handle_event(event)
                continue

            # 伤害统计弹窗是模态的：只响应关闭（X / ESC / TAB）
            if self.stats_open:
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    if self.ui_manager.get_stats_close_rect().collidepoint(pygame.mouse.get_pos()):
                        self.stats_open = False
                elif event.type == pygame.KEYDOWN and event.key in (pygame.K_ESCAPE, pygame.K_TAB):
                    self.stats_open = False
                continue

            if event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:
                    mouse_x, mouse_y = pygame.mouse.get_pos()

                    if (self.state in (GameState.PLAYING, GameState.WAVE_PREPARATION, GameState.PAUSED)
                            and self.ui_manager.get_stats_button_rect().collidepoint(mouse_x, mouse_y)):
                        self.stats_open = True
                        return

                    grid_x = mouse_x // TILE_SIZE
                    grid_y = mouse_y // TILE_SIZE

                    if self.state == GameState.MENU:
                        if 900 <= mouse_x <= 1660 and 840 <= mouse_y <= 920:
                            self.start_game()
                        elif (CODEX_BTN_X <= mouse_x <= CODEX_BTN_X + CODEX_BTN_WIDTH
                              and CODEX_BTN_Y <= mouse_y <= CODEX_BTN_Y + CODEX_BTN_HEIGHT):
                            self.codex.toggle()
                        elif 900 <= mouse_x <= 1660 and 1020 <= mouse_y <= 1100:
                            self.quit_game()

                    elif self.state in (GameState.PLAYING, GameState.WAVE_PREPARATION,
                                        GameState.PAUSED):
                        # 重新开始 / 退出按钮只在游戏内绘制（ui.py 的 draw_ui）。
                        # 判定必须放在 MENU 分支之外：曾把这两段写在这里之前 →
                        # 主菜单右下角 (2048~2560, 1044~1104) 成了看不见的热区，
                        # 玩家点一下就 reset_game() 无声删档。
                        if (RESTART_BTN_X <= mouse_x <= RESTART_BTN_X + RESTART_BTN_WIDTH and
                                RESTART_BTN_Y <= mouse_y <= RESTART_BTN_Y + RESTART_BTN_HEIGHT):
                            # 二次确认：第一下只亮提示，窗口期内再点才真重置
                            if self.confirm_reset > 0:
                                self.confirm_reset = 0
                                self.reset_game()
                            else:
                                self.confirm_reset = CONFIRM_RESET_FRAMES
                            return

                        if (EXIT_BTN_X <= mouse_x <= EXIT_BTN_X + EXIT_BTN_WIDTH and
                                EXIT_BTN_Y <= mouse_y <= EXIT_BTN_Y + EXIT_BTN_HEIGHT):
                            self.quit_game()
                            return

                        self.handle_game_click(mouse_x, mouse_y, grid_x, grid_y)

                    elif self.state == GameState.SHOP:
                        bought = False
                        for rect, ench in self.ui_manager.get_shop_slots():
                            if rect.collidepoint(mouse_x, mouse_y):
                                self.buy_enchantment(ench)
                                bought = True
                                break
                        if not bought and self.ui_manager.get_shop_continue_rect().collidepoint(mouse_x, mouse_y):
                            self.close_shop()
                        elif self.ui_manager.get_shop_refresh_rect().collidepoint(mouse_x, mouse_y):
                            self.refresh_shop()

                    elif self.state == GameState.GAME_OVER:
                        if self.ui_manager.get_gameover_restart_wave_rect().collidepoint(mouse_x, mouse_y):
                            # 本波重来不碰存档，单击即可
                            self.restart_wave()
                        elif self.ui_manager.get_gameover_restart_run_rect().collidepoint(mouse_x, mouse_y):
                            # 本局重开会覆盖存档，仍然要二次确认（文案见 draw_game_over）
                            if self.confirm_reset > 0:
                                self.confirm_reset = 0
                                self.reset_game()
                            else:
                                self.confirm_reset = CONFIRM_RESET_FRAMES

                    elif self.state == GameState.VICTORY:
                        if 900 <= mouse_x <= 1660 and 850 <= mouse_y <= 930:
                            # 通关页只有一个「重新开始」，同样二次确认
                            if self.confirm_reset > 0:
                                self.confirm_reset = 0
                                self.reset_game()
                            else:
                                self.confirm_reset = CONFIRM_RESET_FRAMES

            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_c:
                    self.codex.toggle()
                    continue
                if event.key == pygame.K_TAB and self.state in (
                        GameState.PLAYING, GameState.WAVE_PREPARATION, GameState.PAUSED,
                        GameState.VICTORY, GameState.GAME_OVER):
                    self.stats_open = True
                    continue
                for ttype, name, cost, key in TOWER_DATA:
                    if event.key == key:
                        self.selected_tower_type = ttype
                        break
                else:
                    if event.key == pygame.K_u and self.selected_tower:
                        if self.selected_tower.level < 15 and self.coins >= self.selected_tower.upgrade_cost:
                            self.coins -= self.selected_tower.upgrade_cost
                            tower = self.selected_tower
                            old_effect = self.get_bomb_temp_effect(tower) if tower.type == TowerType.BOMB else 0
                            tower.upgrade()
                            if assets.level_up_sound and tower.level in (6, 11):
                                audio.play_sound(assets.level_up_sound)
                            if tower.type in (TowerType.FLAME, TowerType.TRIDENT):
                                self.temperature += 1
                            elif tower.type == TowerType.ICE:
                                self.temperature -= 1
                            elif tower.type == TowerType.BOMB:
                                new_effect = self.get_bomb_temp_effect(tower)
                                self.temperature += (new_effect - old_effect)
                    elif event.key == pygame.K_e and self.selected_tower:
                        for _ in range(5):
                            tower = self.selected_tower
                            if tower.level >= 15 or self.coins < tower.upgrade_cost:
                                break
                            self.coins -= tower.upgrade_cost
                            old_effect = self.get_bomb_temp_effect(tower) if tower.type == TowerType.BOMB else 0
                            tower.upgrade()
                            if assets.level_up_sound and tower.level in (6, 11):
                                audio.play_sound(assets.level_up_sound)
                            if tower.type in (TowerType.FLAME, TowerType.TRIDENT):
                                self.temperature += 1
                            elif tower.type == TowerType.ICE:
                                self.temperature -= 1
                            elif tower.type == TowerType.BOMB:
                                new_effect = self.get_bomb_temp_effect(tower)
                                self.temperature += (new_effect - old_effect)
                    elif event.key == pygame.K_r and self.selected_tower and self.selected_tower.type == TowerType.BOMB:
                        tower = self.selected_tower
                        old_effect = self.get_bomb_temp_effect(tower)
                        if tower.level >= 11:
                            tower.bomb_branch = 3 - tower.bomb_branch
                            tower.update_sprite()
                        elif 6 <= tower.level < 11:
                            sub_types = [BombSubType.SNOW, BombSubType.ICE, BombSubType.FLAME, BombSubType.POISON, BombSubType.WITHER_TNT]
                            idx = sub_types.index(tower.bomb_subtype)
                            tower.bomb_subtype = sub_types[(idx + 1) % 5]
                            tower.update_sprite()
                        new_effect = self.get_bomb_temp_effect(tower)
                        self.temperature += (new_effect - old_effect)
                    elif event.key == pygame.K_r and self.selected_tower and self.selected_tower.type == TowerType.POISON:
                        max_branch = 3 if self.selected_tower.level >= 11 else 2
                        self.selected_tower.poison_branch = self.selected_tower.poison_branch % max_branch + 1
                        self.selected_tower.update_sprite()
                    elif event.key == pygame.K_r and self.selected_tower and self.selected_tower.type == TowerType.PHYSICAL and self.selected_tower.level >= 11:
                        self.selected_tower.physical_branch = self.selected_tower.physical_branch % 3 + 1
                        self.selected_tower.update_sprite()
                    elif event.key == pygame.K_r and self.selected_tower and self.selected_tower.type == TowerType.WIND and self.selected_tower.level >= 11:
                        self.selected_tower.wind_branch = 3 - self.selected_tower.wind_branch
                        self.selected_tower.update_sprite()
                    elif event.key == pygame.K_r and self.selected_tower and self.selected_tower.type == TowerType.ICE and self.selected_tower.level >= 11:
                        # 三阶四个分支：冰霜炸弹 / 唤龙冰晶石 / 冰墙 / 神锅
                        self.selected_tower.ice_branch = self.selected_tower.ice_branch % 4 + 1
                        self.selected_tower.recalculate_stats()
                        self.selected_tower.update_sprite()
                    elif event.key == pygame.K_r and self.selected_tower and self.selected_tower.type == TowerType.FLAME and self.selected_tower.level >= 11:
                        self.selected_tower.flame_branch = self.selected_tower.flame_branch % 3 + 1
                        self.selected_tower.recalculate_stats()
                        self.selected_tower.update_sprite()
                    elif event.key == pygame.K_r and self.selected_tower and self.selected_tower.type == TowerType.TRIDENT and self.selected_tower.level >= 11:
                        # 三阶三分支：海渊裂空之戟 / 唤龙电晶石 / 卧龙
                        self.selected_tower.trident_branch = self.selected_tower.trident_branch % 3 + 1
                        self.selected_tower.update_sprite()
                    elif event.key == pygame.K_r and self.selected_tower and self.selected_tower.type == TowerType.TELEPORT:
                        self.selected_tower.teleport_branch = 3 - self.selected_tower.teleport_branch
                        self.selected_tower.recalculate_stats()
                        self.selected_tower.update_sprite()
                    elif event.key == pygame.K_r and self.selected_tower and self.selected_tower.type == TowerType.SHIELD and self.selected_tower.level >= 11:
                        self.selected_tower.shield_branch = self.selected_tower.shield_branch % 3 + 1
                        self.selected_tower.update_sprite()
                    elif event.key == pygame.K_q and self.selected_tower and self.ember_rebirth_active():
                        if self.selected_tower.type == TowerType.FLAME and self.selected_tower.level == 15 and self.selected_tower.flame_branch == 1:
                            self.sacrifice_tower()
                    elif event.key == pygame.K_s and self.selected_tower:
                        cost_map = {ttype: cost for ttype, name, cost, key in TOWER_DATA}
                        sell_price = cost_map[self.selected_tower.type] * self.selected_tower.level
                        self.coins += sell_price
                        if self.selected_tower.type == TowerType.PRODUCTION:
                            level = self.selected_tower.level
                            multiplier = 2 if self.selected_tower.is_on_gold_ore else 1
                            self.gold_per_second -= level * multiplier
                            if level >= 6:
                                self.gold_per_wave -= (level - 5) * multiplier
                            if level >= 11:
                                self.emerald_per_wave -= EMERALD_PER_WAVE_BY_LEVEL.get(level, 3)
                        if self.selected_tower.type in (TowerType.FLAME, TowerType.TRIDENT):
                            self.temperature -= self.selected_tower.level
                        elif self.selected_tower.type == TowerType.ICE:
                            self.temperature += self.selected_tower.level
                        elif self.selected_tower.type == TowerType.BOMB:
                            old_temp_effect = self.get_bomb_temp_effect(self.selected_tower)
                            self.temperature -= old_temp_effect
                        elif self.selected_tower.type == TowerType.SHIELD and self.selected_tower.level >= 11:
                            if self.selected_tower.shield_branch == 2:
                                self.temperature += self.selected_tower.level
                        self.selected_tower.kill()
                        self.selected_tower = None
                    elif event.key == pygame.K_ESCAPE:
                        if self.state in (GameState.PLAYING, GameState.WAVE_PREPARATION):
                            self.pre_pause_state = self.state
                            self.state = GameState.PAUSED
                        elif self.state == GameState.PAUSED:
                            self.state = self.pre_pause_state
                            self.pre_pause_state = None
                        elif self.state == GameState.SHOP:
                            self.close_shop()
                        else:
                            self.selected_tower = None
                            self.selected_tower_type = None
                            self.show_range = False
                    elif event.key == pygame.K_F11:
                        pygame.display.toggle_fullscreen()

    def get_bomb_temp_effect(self, tower):
        if tower.level >= 11:
            if tower.bomb_branch == 1:
                return tower.level
            elif tower.bomb_branch == 2:
                return 0
        else:
            if tower.bomb_subtype == BombSubType.ICE:
                return -tower.level
            elif tower.bomb_subtype == BombSubType.FLAME:
                return tower.level
            else:
                return 0

    def destroy_ice_wall(self, wall):
        if wall in self.ice_walls:
            self.ice_walls.remove(wall)
            self.temperature += 5

    def trigger_shield_burst(self, broken_tower):
        for tower in self.towers:
            if tower.type == TowerType.SHIELD and tower.level >= 11:
                if tower.shield_branch == 1:
                    damage = int(self.coins * 0.01 * self.get_element_damage_multiplier("physical"))
                    for enemy in self.enemies:
                        enemy.take_damage(damage, color=(255, 215, 0), element="physical")
                    self.coins += (tower.level - 10) * 1000
                elif tower.shield_branch == 2:
                    damage = int((tower.level - 10) * 3000 * self.get_element_damage_multiplier("ice"))
                    for enemy in self.enemies:
                        enemy.take_damage(damage, color=(100, 150, 255), element="ice")
                        enemy.freeze_resistance = 0
                        enemy.freeze_time = max(enemy.freeze_time, 3 * 60)
                elif tower.shield_branch == 3:
                    damage = int((tower.level - 10) * 2500 * self.get_element_damage_multiplier("electric"))
                    for enemy in self.enemies:
                        enemy.take_damage(damage, color=ORANGE, element="electric")
                        enemy.stun_resistance = 0
                        enemy.stun_time = max(enemy.stun_time, 60)
                        enemy.burn_time = float('inf')
                        enemy.burn_damage = max(enemy.burn_damage, self.temperature)

    def trigger_resonance_storm(self):
        if Enchantment.RESONANCE_STORM not in self.enchantments:
            return
        has_hammer = any(t.type == TowerType.WIND and t.level >= 11 and t.wind_branch == 2 for t in self.towers)
        has_shield = any(t.type == TowerType.SHIELD and t.level >= 11 and t.shield_branch == 3 for t in self.towers)
        if not (has_hammer and has_shield):
            return
        for tower in self.towers:
            if tower.type == TowerType.SHIELD and tower.level >= 11 and tower.shield_branch == 3:
                damage = int((tower.level - 10) * 2500 * self.get_element_damage_multiplier("electric"))
                for enemy in self.enemies:
                    enemy.take_damage(damage, color=ORANGE, element="electric")
                    enemy.stun_resistance = 0
                    enemy.stun_time = max(enemy.stun_time, 60)
                    enemy.burn_time = float('inf')
                    enemy.burn_damage = max(enemy.burn_damage, self.temperature)
        for enemy in self.enemies:
            if enemy.wind_mark_tower is not None:
                t = enemy.wind_mark_tower
                dmg = 5000 if Enchantment.WIND_BURST in self.enchantments else t.damage
                dmg = int(dmg * self.get_element_damage_multiplier("wind"))
                exp = WindExplosion(enemy.rect.centerx, enemy.rect.centery,
                                    dmg, t.wind_knockback, self, element="wind")
                self.wind_explosions.append(exp)
                enemy.wind_mark_tower = None
        storm = ResonanceStorm(GRID_WIDTH * TILE_SIZE // 2, (1 + GRID_HEIGHT) * TILE_SIZE // 2)
        self.resonance_storms.append(storm)

    def ember_rebirth_active(self):
        if Enchantment.EMBER_REBIRTH not in self.enchantments:
            return False
        has_dragon = any(t.type == TowerType.FLAME and t.level == 15 and t.flame_branch == 1 for t in self.towers)
        nuclear_count = sum(1 for t in self.towers if t.type == TowerType.BOMB and t.is_nuclear and t.level == 15 and t.bomb_branch == 1)
        return has_dragon and nuclear_count >= 8

    def sacrifice_tower(self):
        t = self.selected_tower
        if t is None or not self.ember_rebirth_active():
            return False
        if not (t.type == TowerType.FLAME and t.level == 15 and t.flame_branch == 1):
            return False
        cost = 50000 * (2 ** self.sacrifices)
        if self.coins < cost:
            return False
        self.coins -= cost
        self.sacrifices += 1
        self.temperature -= t.level
        t.kill()
        self.selected_tower = None
        for tb in self.towers:
            if tb.type == TowerType.BOMB and tb.is_nuclear and tb.bomb_branch == 1:
                missile = NuclearMissile(tb.rect.centerx, tb.rect.centery,
                                         MAP_CENTER_X, MAP_CENTER_Y,
                                         tb.damage, tb.level, self, tb.bomb_branch)
                self.bullets.add(missile)
                tb.last_shot = self.game_time
                tb.ember_salvo = False
        self.meteors.append(Meteor(self))
        self.save_game()
        return True

    def add_meteor_hit(self, x, y):
        # 陨石吃火系伤害加成；打 BOSS 只打穿当前这一层，溢出伤害不带到下一层
        damage = int(FINAL_BOSS_METEOR_DAMAGE * self.get_element_damage_multiplier("fire"))
        for enemy in list(self.enemies):
            if enemy.health > 0:
                reward = enemy.take_damage(damage, color=(255, 120, 40), scale=1.6, element="fire")
                self.coins += reward

    def global_production(self):
        if self.boss_rule and self.boss_rule.get("type") == "gold":
            # 指令·覆写：金币产量归零
            return
        current_time = pygame.time.get_ticks()
        if current_time - self.last_global_production_time >= 1000:
            self.coins += self.gold_per_second
            self.last_global_production_time = current_time

    def apply_time_buffs(self):
        for t in self.towers:
            t.attack_speed_buff = 0
            t.production_buff = 0.0
        gold_ps = 0.0
        for tt in self.towers:
            if tt.type != TowerType.TIME:
                continue
            n = tt.level * ((tt.level + 4) // 5)
            if tt.level <= 5:
                half = 192
            elif tt.level <= 10:
                half = 320
            else:
                half = 448
            cx, cy = tt.rect.center
            for other in self.towers:
                if other is tt:
                    continue
                ox, oy = other.rect.center
                if abs(ox - cx) <= half and abs(oy - cy) <= half:
                    other.attack_speed_buff += n
                    if other.type == TowerType.PRODUCTION:
                        other.production_buff += n
        for t in self.towers:
            if t.type == TowerType.PRODUCTION:
                mult = 2 if t.is_on_gold_ore else 1
                gold_ps += t.level * mult * (1 + t.production_buff / 100)
        self.gold_per_second = gold_ps

    def spawn_damage_text(self, value, pos, color=RED, scale=1.4, speed_x=0.0, speed_y=-2, boss=False):
        if boss:
            # BOSS 受击极密集，超过上限就丢掉最旧的一条，避免 5 个点位被数字糊死
            alive = [t for t in self.damage_texts if getattr(t, "is_boss", False)]
            if len(alive) >= BOSS_DAMAGE_TEXT_LIMIT:
                oldest = max(alive, key=lambda t: t.timer)
                oldest.kill()
        # 超长数字（1 亿以上）压缩成「x.xx亿」，否则单条飘字能吃掉四分之一屏宽。
        if isinstance(value, int) and value >= 100_000_000:
            value = stats.format_damage(value)
        text = DamageText(value, pos[0], pos[1], color=color, scale=scale,
                          speed_x=speed_x, speed_y=speed_y)
        text.is_boss = boss
        self.damage_texts.add(text)

    def save_game(self):
        try:
            towers_data = []
            for t in self.towers:
                td = {
                    "x": t.x, "y": t.y, "type": t.type.value, "level": t.level,
                    "physical_branch": t.physical_branch, "wind_branch": t.wind_branch,
                    "ice_branch": t.ice_branch, "flame_branch": t.flame_branch,
                    "poison_branch": t.poison_branch, "bomb_branch": t.bomb_branch,
                    "trident_branch": t.trident_branch, "teleport_branch": t.teleport_branch,
                    "shield_branch": t.shield_branch,
                    "bomb_subtype": t.bomb_subtype.value if hasattr(t, 'bomb_subtype') and t.bomb_subtype else None,
                    "is_nuclear": getattr(t, 'is_nuclear', False),
                    "has_shield": getattr(t, 'has_shield', False),
                }
                towers_data.append(td)
            try:
                seed_idx = SEED_PATHS.index(self.path)
            except ValueError:
                seed_idx = 0
            data = {
                "seed": seed_idx,
                "gold": self.coins, "emeralds": self.emeralds, "wave": self.wave_manager.current_wave,
                "temperature": self.temperature, "weather": self.weather.value,
                "gold_per_second": self.gold_per_second, "gold_per_wave": self.gold_per_wave,
                "emerald_per_wave": self.emerald_per_wave,
                "enchantments": [e.value for e in self.enchantments],
                "poison_base_damage": self.poison_base_damage,
                "damage_stats": self.damage_stats.to_dict(),
                "sacrifices": self.sacrifices,
                "gold_ore_positions": [list(p) for p in self.gold_ore_positions],
                "towers": towers_data,
            }
            # 原子写：先写 .tmp 并 fsync，再 os.replace 覆盖。
            # 原实现直接 open(path,"w") 后 json.dump —— 写到一半断电/被关窗口
            # 就会留下半截 JSON，下次启动必然读档失败（配合旧的窄 try 就是闪退）。
            # os.replace 在同一分区上是原子的，进程被杀也不会出现半截存档。
            save_path = get_save_path()
            tmp_path = save_path + ".tmp"
            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp_path, save_path)
        except Exception as e:
            print(f"Save failed: {e}")

    def _reset_state(self):
        self.enemies.empty()
        self.towers.empty()
        self.bullets.empty()
        self.damage_texts.empty()
        self.dragons.empty()
        if getattr(self, "damage_stats", None) is None:
            self.damage_stats = stats.DamageStats()
        self.damage_stats.reset()
        self.damage_element = None
        self.stats_open = False
        self.confirm_reset = 0      # 「重新开始」二次确认倒计时（帧）
        self.coins = 2500
        self.emeralds = 100
        self.wave_manager = WaveManager()
        self.selected_tower_type = None
        self.selected_tower = None
        self.show_range = False
        self.enemies_killed = 0
        self.game_time = 0
        self.gold_per_second = 0
        self.gold_per_wave = 0
        self.emerald_per_wave = 0
        self.last_global_production_time = pygame.time.get_ticks()
        self.temperature = 30
        self.lava_timer = 0
        self.weather = Weather.SUNNY
        self.weather_particles = []
        self.weather_banner_timer = 0
        self.weather_banner_text = ""
        self.dragon_breath_pools = []
        self.lightning_effects = []
        self.wind_explosions = []
        self.endless_greed_explosions = []
        self.ice_explosions = []
        self.hell_rays = []
        self.resonance_storms = []
        self.poison_splashes = []
        self.wither_splashes = []
        self.horizontal_lightning_effects = []
        self.tnt_explosions = []
        self.mushroom_explosions = []
        self.shockwave_effects = []
        self.thunderstorm_timer = 0
        self.resonance_counter = 0
        self.masterpiece_counter = 0     # 臻品呈现：场上所有神锅共用的攻击计数
        self.sacrifices = 0
        self.meteors = []
        self.bees = []
        self.bee_spawn_remaining = 0
        self.bee_spawn_timer = 0
        self.crystals = []
        self.lantern_shockwaves = []
        self.stars = []
        self.ice_star_bursts = []
        self.masterpiece_shockwaves = []
        self.bagua_arrays = []
        self.ultimate_video = None
        self.masterpiece_pending = False   # 视频播完才结算，标记「这一发还没落地」
        self._lantern_towers = 0
        self.enemy_grid = {}
        self.fog_timer = 0
        self.fog_visible = False
        self.pending_first_wave_weather = False
        self.gold_ore_positions = set()
        self.night_dark_timer = 0
        self.herobrine_phase = 0
        self.herobrine_spawned = False
        self.herobrine = None
        self.herobrine_summon_timer = 0
        self.herobrine_summon_queue = []
        self._init_boss_state()
        self.command_block_timer = 0
        self.command_blocks = []
        self.ice_walls = []
        self.enchantments = []
        self.poison_base_damage = 5
        self.shop_offers = []
        self.shop_offers_wave = -1

    # ------------------------------------------------------------------ 最终BOSS状态

    def _init_boss_state(self):
        """第 100 波最终 BOSS 相关的全部运行时状态。"""
        self.final_boss = None
        self.boss_spawned = False
        self.boss_banner_text = ""
        self.boss_banner_timer = 0
        self.boss_flash = 0
        self.boss_acid_timer = 0
        self.boss_time_frozen = 0
        self.boss_rule = None
        self.boss_strikes = []
        self.boss_beams = []
        self.boss_runes = []
        self.boss_shockwaves = []
        self.boss_portals = []

    def set_boss_banner(self, text, frames=150):
        self.boss_banner_text = text
        self.boss_banner_timer = max(1, int(frames))

    def update_boss_fx(self):
        if self.boss_flash > 0:
            self.boss_flash -= 1
        if self.boss_banner_timer > 0:
            self.boss_banner_timer -= 1
        if self.boss_acid_timer > 0:
            self.boss_acid_timer -= 1
        if self.boss_time_frozen > 0:
            self.boss_time_frozen -= 1
        if self.boss_rule is not None:
            self.boss_rule["timer"] -= 1
            if self.boss_rule["timer"] <= 0:
                self.boss_rule = None

        for effect in self.boss_strikes[:]:
            if not effect.update():
                self.boss_strikes.remove(effect)
        for effect in self.boss_beams[:]:
            if not effect.update():
                self.boss_beams.remove(effect)
        for effect in self.boss_runes[:]:
            if not effect.update():
                self.boss_runes.remove(effect)
        for effect in self.boss_shockwaves[:]:
            if not effect.update():
                self.boss_shockwaves.remove(effect)
        for effect in self.boss_portals[:]:
            if not effect.update():
                self.boss_portals.remove(effect)

    def destroy_tower_by_boss(self, tower):
        """BOSS 指令抹除炮塔（不计入出售、不返还金币）。"""
        if tower is None or tower not in self.towers:
            return
        if tower.is_invincible():
            return
        if self.selected_tower is tower:
            self.selected_tower = None
        tower.kill()

    def play_boss_bgm(self):
        for bgm in assets.bgm_files:
            if "Celestial Fury" in bgm or "The End" in bgm:
                audio.play_music(assets.resource_path(bgm), -1)
                return

    def force_boss_weather(self):
        """第 50 / 100 波强制「永夜」。

        正常推进时 select_weather() 已经会强制一次；但读档（load_game 直接
        start_new_wave，不经过 select_weather）或调试跳波会绕过它，导致
        100 波顶着逆风/晴天打 BOSS。所有入口统一走这里兜底。
        """
        self.fog_visible = False
        self.weather = Weather.ENDLESS_NIGHT
        # 读档时背景可能还是白天配色，这里无条件重建一次永夜场景
        self._build_background(night_mode=True, gold_ore_positions=self.gold_ore_positions)
        base_temp = WEATHER_CONFIG[self.weather]["temp"]
        self.temperature = base_temp
        for t in self.towers:
            if t.type in (TowerType.FLAME, TowerType.TRIDENT):
                self.temperature += t.level
            elif t.type == TowerType.ICE:
                self.temperature -= t.level
            elif t.type == TowerType.BOMB:
                self.temperature += self.get_bomb_temp_effect(t)
            elif t.type == TowerType.SHIELD and t.level >= 11 and t.shield_branch == 2:
                self.temperature -= t.level
        self.temperature += self.enchantment_temp_bonus()
        self.weather_banner_text = WEATHER_CONFIG[self.weather]["desc"]
        self.play_boss_bgm()

    def start_boss_fight(self):
        self.boss_spawned = True
        self.force_boss_weather()
        self.fog_visible = False
        self.set_boss_banner(f"{FINAL_BOSS_NAME} 降临 —— {FINAL_BOSS_TITLE}", 240)
        self.boss_flash = 120
        if assets.explode_sound:
            audio.play_sound(assets.explode_sound)

    def load_game(self):
        new_path = get_save_path()
        old_path = resource_path("save.json")
        if not os.path.exists(new_path) and os.path.exists(old_path):
            try:
                os.makedirs(os.path.dirname(new_path), exist_ok=True)
                with open(old_path) as src:
                    data = src.read()
                with open(new_path, "w") as dst:
                    dst.write(data)
            except Exception:
                pass
        try:
            with open(new_path, encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            return False

        # 反序列化全程保护。
        #
        # 原实现只保护了上面那个 json.load，:998 的 Enchantment(v)、
        # :1013 的 TowerType(td["type"])、:1029 的 BombSubType(sv) 全是
        # 裸枚举转换 —— 存档里出现一个已删除/改名的枚举值就直接崩到桌面。
        # 玩家看到的现象是「游戏更新后打不开了」，而且越玩得久越容易触发。
        #
        # 失败时必须再做一次 _reset_state()：此时对象已经停在半初始化状态
        # （path 改了、towers 加了一半），不回滚的话即使返回 False，
        # 后续 draw/update 依然会踩到脏数据。
        try:
            self._apply_save_data(data, new_path)
        except Exception as e:
            self._reset_state()
            # 不删档：改名保留，用户还能手工修复或反馈给我们。
            # 加序号避免连续两次损坏时把第一次的备份覆盖掉。
            try:
                backup = new_path + ".corrupt.bak"
                if os.path.exists(backup):
                    backup = new_path + f".corrupt.{int(time.time())}.bak"
                os.replace(new_path, backup)
            except Exception:
                pass
            print(f"Load failed, save backed up: {e}")
            return False
        return True

    def _apply_save_data(self, data, save_path):
        """把已解析的存档字典套用到当前实例上。

        单独成方法是为了让 load_game 能用一个大 try 包住全流程；
        这里允许抛异常，由调用方负责回滚与备份。
        """
        self._reset_state()
        seed_idx = data.get("seed", 0)
        if 0 <= seed_idx < len(SEED_PATHS):
            self.path = list(SEED_PATHS[seed_idx])
        else:
            self.path = list(SEED_PATHS[0])
        self.start_point = self.path[0]
        self.end_point = self.path[-1]
        ore_positions = data.get("gold_ore_positions", [])
        saved_ore = set(tuple(p) for p in ore_positions)
        self._build_background(gold_ore_positions=saved_ore)
        self.coins = data.get("gold", 2500)
        self.emeralds = data.get("emeralds", 0)
        self.temperature = data.get("temperature", 30)
        self.weather = Weather(data.get("weather", Weather.SUNNY.value))
        self.gold_per_second = data.get("gold_per_second", 0)
        self.gold_per_wave = data.get("gold_per_wave", 0)
        self.emerald_per_wave = data.get("emerald_per_wave", 0)
        self.enchantments = [Enchantment(v) for v in data.get("enchantments", [])]
        # 基础毒伤直接读存档；兼容曾经写过的 poison_contract_stacks 字段
        base_poison = data.get("poison_base_damage")
        if base_poison is None:
            # 兼容短暂出现过的旧字段（当时的层数按 base-10 记录）
            try:
                base_poison = 10 + max(0, int(data.get("poison_contract_stacks", 0)))
            except (TypeError, ValueError):
                base_poison = 5
        self.poison_base_damage = base_poison
        self.damage_stats.load_dict(data.get("damage_stats"))
        self.sacrifices = data.get("sacrifices", 0)
        wave_num = max(1, data.get("wave", 1))
        self.wave_manager.current_wave = wave_num - 1
        for td in data.get("towers", []):
            try:
                ttype = TowerType(td["type"])
            except ValueError:
                # 旧存档里可能有已经删掉的塔（比如剑系 type=11），跳过而不是让整份存档读不出来
                continue
            t = Tower(ttype, td["x"], td["y"], self)
            while t.level < td["level"]:
                t.upgrade()
            t.physical_branch = td.get("physical_branch", 1)
            t.wind_branch = td.get("wind_branch", 1)
            t.ice_branch = td.get("ice_branch", 1)
            t.flame_branch = td.get("flame_branch", 1)
            t.poison_branch = td.get("poison_branch", 1)
            t.bomb_branch = td.get("bomb_branch", 1)
            t.trident_branch = td.get("trident_branch", 1)
            t.teleport_branch = td.get("teleport_branch", 1)
            t.shield_branch = td.get("shield_branch", 1)
            if hasattr(t, 'bomb_subtype'):
                sv = td.get("bomb_subtype")
                t.bomb_subtype = BombSubType(sv) if sv is not None else BombSubType.SNOW
            if hasattr(t, 'is_nuclear'):
                t.is_nuclear = td.get("is_nuclear", False)
            t.has_shield = td.get("has_shield", False)
            # 分支是在升级之后才套用的，所以带分支数值的塔必须整体重算一次，
            # 否则读档后神锅会保留「普通冰塔」的数值（伤害 55 而不是 500+）
            if ttype in (TowerType.TELEPORT, TowerType.FLAME, TowerType.ICE):
                t.recalculate_stats()
            t.update_sprite()
            self.towers.add(t)
        base_temp = WEATHER_CONFIG[self.weather]["temp"]
        self.temperature = base_temp
        for t in self.towers:
            if t.type in (TowerType.FLAME, TowerType.TRIDENT):
                self.temperature += t.level
            elif t.type == TowerType.ICE:
                self.temperature -= t.level
            elif t.type == TowerType.BOMB:
                self.temperature += self.get_bomb_temp_effect(t)
            elif t.type == TowerType.SHIELD and t.level >= 11:
                if t.shield_branch == 2:
                    self.temperature -= t.level
        self.temperature += self.enchantment_temp_bonus()
        self.wave_manager.start_new_wave()
        if self.wave_manager.current_wave in (50, FINAL_BOSS_WAVE):
            # 读档直接进入 BOSS 波时不会走 select_weather，这里强制补上永夜
            self.force_boss_weather()
            self.save_game()
        self.state = GameState.PLAYING
        self.pending_first_wave_weather = False
        self.weather_banner_text = WEATHER_CONFIG[self.weather]["desc"]
        self.weather_banner_timer = 180
        if self.weather == Weather.ENDLESS_NIGHT:
            self._build_background(night_mode=True, gold_ore_positions=saved_ore)
            audio.stop_music()
            for bgm in assets.bgm_files:
                if "Celestial Fury" in bgm or "The End" in bgm:
                    audio.play_music(assets.resource_path(bgm), -1)
                    break

    def add_dragon_breath(self, x, y, temperature, tower_level, stun_time):
        pool = DragonBreathPool(x, y, temperature, tower_level, stun_time, self)
        self.dragon_breath_pools.append(pool)

    def add_lightning(self, x, y, is_golden):
        effect = LightningEffect(x, y, is_golden)
        self.lightning_effects.append(effect)

    def add_resonance_burst(self, x, y):
        """雷神之锤子弹命中爆裂：用 resonance_storm 原尺寸帧，不缩放。"""
        burst = ResonanceStorm(x, y, frames=assets.resonance_storm_raw_frames)
        self.resonance_storms.append(burst)

    def add_lantern_shockwave(self, x, y, radius):
        self.lantern_shockwaves.append(LanternShockwave(x, y, radius))

    def add_ice_star_burst(self, x, y):
        """神锅四芒星命中的小爆点。"""
        self.ice_star_bursts.append(IceStarBurst(x, y))

    def spawn_bagua_array(self, tower):
        """卧龙能量满 100：在道路格上放一座八卦阵（有敌人的格子优先）。"""
        occupied = {(b.tile_x, b.tile_y) for b in self.bagua_arrays}
        enemy_tiles = []
        for e in self.enemies:
            if e.health <= 0:
                continue
            tx = int(e.rect.centerx) // TILE_SIZE
            ty = int(e.rect.centery) // TILE_SIZE
            if (tx, ty) in self.path and (tx, ty) not in occupied:
                enemy_tiles.append((tx, ty))
        if enemy_tiles:
            tile = random.choice(enemy_tiles)
        else:
            free = [p for p in self.path if p not in occupied]
            if not free:
                return
            tile = random.choice(free)

        lv = getattr(tower, "level", 15)
        dmg = int(CD_BAGUA_DAMAGE.get(lv, 128) * abs(self.temperature))
        dmg = max(1, int(dmg * self.get_element_damage_multiplier(TowerType.TRIDENT)))
        self.bagua_arrays.append(BaguaArray(tile[0], tile[1], dmg, self))

    def notify_tower_hit(self, tower):
        """某座塔被打了（含破盾、含被免疫挡下的攻击）：3x3 内的卧龙各 +50 能量。

        卧龙自己免疫，但「挨了一下」这件事本身要算 —— 否则苦力怕/BOSS 打它
        只会显示没掉血、能量却一动不动。加个 1 秒冷却，避免 BOSS 贴身光环
        每 18 帧刷一次把能量刷爆。
        """
        if tower is None:
            return
        for t in self.towers:
            if not t.is_crouch_dragon():
                continue
            if abs(t.x - tower.x) <= 1 and abs(t.y - tower.y) <= 1:
                if t.hit_energy_cd > 0:
                    continue
                t.hit_energy_cd = CD_ENERGY_HIT_CD
                t.gain_energy(CD_ENERGY_PER_HIT)

    def add_masterpiece_shockwave(self):
        """大招落点冲击波：从地图中心炸开，半径取到能盖住屏幕四角。"""
        cx, cy = MAP_CENTER_X, MAP_CENTER_Y
        radius = max(math.hypot(cx - x, cy - y)
                     for x in (0, SCREEN_WIDTH) for y in (0, SCREEN_HEIGHT))
        self.masterpiece_shockwaves.append(
            MasterpieceShockwave(cx, cy, radius))

    def masterpiece_active(self):
        """臻品呈现的生效条件：持有该附魔，且场上同时有寒冰盾（盾塔分支 2）与神锅（冰塔分支 4）。"""
        if Enchantment.MASTERPIECE not in self.enchantments:
            return False
        has_pot = any(t.type == TowerType.ICE and t.level >= 11 and t.ice_branch == HOLY_POT_BRANCH
                      for t in self.towers)
        has_ice_shield = any(t.type == TowerType.SHIELD and t.level >= 11 and t.shield_branch == 2
                             for t in self.towers)
        return has_pot and has_ice_shield

    def trigger_masterpiece_ultimate(self):
        """「臻品呈现」大招起手：先播动画，伤害等动画放完再结算。

        以前是触发瞬间就结算，1.6 秒的动画把整个屏幕盖住，
        伤害飘字全被埋在视频下面 —— 玩家只能看到血条掉，看不到打了多少。
        现在改成「播片 → 播完冲击波炸一下 → 炸的同时飘字」。
        """
        if self.masterpiece_pending:
            # 上一发还没落地就又攒满了：先把上一发结算掉，别把伤害吞了
            self.masterpiece_pending = False
            self.resolve_masterpiece_ultimate()

        if self.ultimate_video is not None:
            self.ultimate_video.finish()
        self.ultimate_video = UltimateVideo()
        if self.ultimate_video.done:
            # 没有可用的视频帧（打包漏了 video/ 目录）：直接结算，别让大招凭空消失
            self.ultimate_video = None
            self.resolve_masterpiece_ultimate()
        else:
            self.masterpiece_pending = True

    def resolve_masterpiece_ultimate(self):
        """大招落地：全屏冲击波 + 全屏伤害 + 永久冰系破甲 + 冰冻 4 秒。

        伤害属于冰系，所以吃冰系伤害加成（含本附魔自己的 +240%）。
        冰冻沿用「寒冰盾」那套写法：先清空冰冻抗性再直接写 freeze_time，
        否则连吃几次冰冻后抗性叠满，4 秒会被削成 1 秒多。
        """
        self.add_masterpiece_shockwave()

        damage = int((MASTERPIECE_DAMAGE + MASTERPIECE_TEMP_MULT * abs(self.temperature))
                     * self.get_element_damage_multiplier("ice"))
        prev_element = self.damage_element
        self.damage_element = "ice"
        try:
            for enemy in list(self.enemies):
                if enemy.health <= 0:
                    continue
                # 全屏 AOE 一次打十几只，数字全叠在同一个点会糊成一坨，
                # 给每个目标一个随机横向漂移，飘字会自然散开
                reward = enemy.take_damage(damage, color=ICE_BLUE, scale=1.6, element="ice",
                                           text_speed_x=random.uniform(-2.2, 2.2))
                self.coins += reward
                enemy.apply_ice_broken()
                enemy.freeze_resistance = 0
                enemy.freeze_time = max(enemy.freeze_time, MASTERPIECE_FREEZE_FRAMES)
        finally:
            self.damage_element = prev_element

    def apply_production_bonus(self):
        self.coins += 5 * self.gold_per_wave * self.wave_manager.current_wave
        self.emeralds += self.emerald_per_wave

    def get_enchant_damage_multiplier(self, tower_type):
        bonus = 0
        bonus += 5 * self.enchantments.count(Enchantment.BALANCED)
        type_map = {
            Enchantment.PHYSICAL: (TowerType.PHYSICAL, TowerType.TELEPORT),
            Enchantment.ICE: (TowerType.ICE,),
            Enchantment.FLAME: (TowerType.FLAME,),
            Enchantment.TRIDENT: (TowerType.TRIDENT,),
            Enchantment.WIND: (TowerType.WIND,),
            Enchantment.POISON: (TowerType.POISON,),
            Enchantment.BOMB: (TowerType.BOMB,),
        }
        for ench, types in type_map.items():
            if tower_type in types:
                if ench == Enchantment.PHYSICAL:
                    bonus += 15 * self.enchantments.count(ench)
                else:
                    bonus += 20 * self.enchantments.count(ench)
        # 灯火通明：火系伤害 +80%（加算，不随附魔重复叠加）
        if tower_type == TowerType.FLAME and self.lantern_active():
            bonus += LANTERN_FIRE_BONUS
        # 臻品呈现：需要「寒冰盾 + 神锅」同时在场，才给全局冰系 +240%（加算）
        if tower_type == TowerType.ICE and self.masterpiece_active():
            bonus += MASTERPIECE_ICE_BONUS * self.enchantments.count(Enchantment.MASTERPIECE)
        return 1.0 + bonus / 100.0

    def burn_tick_damage(self, base):
        """燃烧每跳的实际伤害 = 基础 × 烈焰粉 × 高温燃烧 × 灯火通明 × (1 + 火系伤害加成)。"""
        dmg = base
        if Enchantment.BLAZE_POWDER in self.enchantments:
            dmg *= 1.3
        if Enchantment.BURN in self.enchantments:
            dmg *= 2
        if self.lantern_active():
            dmg *= LANTERN_BURN_MULT
        dmg *= self.get_element_damage_multiplier("fire")
        return int(dmg)

    def get_element_damage_multiplier(self, element):
        """按伤害属性取附魔倍率（燃烧 / 中毒 / 龙息 / 闪电等结算统一用它）。

        百分比伤害属于真实伤害，不调用这里。
        """
        tower_type = ELEMENT_TO_TOWER_TYPE.get(element)
        if tower_type is None:
            return 1.0
        return self.get_enchant_damage_multiplier(tower_type)

    def enchantment_temp_bonus(self):
        return 0

    def gauntlet_attack(self, enemy):
        weights = [a[2] for a in GAUNTLET_ATTACKS]
        tower_type, atk, _, color = random.choices(GAUNTLET_ATTACKS, weights=weights)[0]
        prev_element = self.damage_element
        self.damage_element = stats.tower_element(tower_type)
        wave = max(1, self.wave_manager.current_wave)
        damage = int(atk * wave ** 2 * self.get_enchant_damage_multiplier(tower_type))
        reward = enemy.take_damage(damage, color=color)
        self.coins += reward
        if tower_type == TowerType.FLAME:
            enemy.apply_burn(max(1, self.temperature), 2 * 60)
        elif tower_type == TowerType.POISON:
            enemy.apply_poison(1)
        elif tower_type == TowerType.ICE:
            enemy.apply_freeze(int(0.25 * 60))
        elif tower_type == TowerType.WIND:
            armored = (EnemyType.IRON_ARMORED, EnemyType.GOLD_ARMORED,
                       EnemyType.DIAMOND_ARMORED, EnemyType.NETHERITE_ARMORED)
            enemy.apply_knockback(12)
            if enemy.enemy_type not in armored:
                enemy.wind_mark_tower = SimpleNamespace(damage=damage, wind_knockback=12)
        elif tower_type == TowerType.TRIDENT:
            col = enemy.rect.centerx // TILE_SIZE
            for e in self.enemies:
                if e.rect.centerx // TILE_SIZE == col and e.health > 0:
                    reward = e.take_damage(damage, color=color)
                    self.coins += reward
                    e.on_lightning_hit()
            self.add_lightning(enemy.rect.centerx, 800, False)
        self.damage_element = prev_element

    def frost_combo_active(self):
        if Enchantment.FROZEN_DEEP not in self.enchantments:
            return False
        has_bomb = any(t.type == TowerType.ICE and t.level >= 11 and t.ice_branch == 1 for t in self.towers)
        has_wall = any(t.type == TowerType.ICE and t.level >= 11 and t.ice_branch == 3 for t in self.towers)
        return has_bomb and has_wall

    def poison_contract_active(self):
        if Enchantment.POISON_CONTRACT not in self.enchantments:
            return False
        has_ring = any(t.type == TowerType.POISON and t.level >= 11 and t.poison_branch == 1 for t in self.towers)
        has_hydra = any(t.type == TowerType.POISON and t.level >= 11 and t.poison_branch == 3 for t in self.towers)
        return has_ring and has_hydra

    def wither_rose_active(self):
        if Enchantment.WITHER_ROSE not in self.enchantments:
            return False
        has_head = any(t.type == TowerType.POISON and t.level >= 11 and t.poison_branch == 2 for t in self.towers)
        has_nuke = any(t.type == TowerType.BOMB and t.level >= 11 and t.bomb_branch == 2 for t in self.towers)
        return has_head and has_nuke

    def lantern_active(self):
        """灯火通明：持有附魔且场上存在 3 座满级星焰提灯时生效。

        `_lantern_towers` 每帧刷新一次，避免燃烧跳伤时反复遍历炮塔。
        """
        if Enchantment.LANTERN not in self.enchantments:
            return False
        return getattr(self, "_lantern_towers", 0) >= LANTERN_ENCHANT_TOWERS

    def dragon_legend_active(self):
        if Enchantment.DRAGON_LEGEND not in self.enchantments:
            return False
        has_ice = any(t.type == TowerType.ICE and t.level >= 11 and t.ice_branch == 2 for t in self.towers)
        has_fire = any(t.type == TowerType.FLAME and t.level >= 11 and t.flame_branch == 2 for t in self.towers)
        has_electric = any(t.type == TowerType.TRIDENT and t.level >= 11 and t.trident_branch == 2 for t in self.towers)
        return has_ice and has_fire and has_electric

    def endless_greed_active(self):
        if Enchantment.ENDLESS_GREED not in self.enchantments:
            return False
        has_t1 = any(t.type == TowerType.PHYSICAL and t.level >= 11 and t.physical_branch == 1 for t in self.towers)
        has_t2 = any(t.type == TowerType.PHYSICAL and t.level >= 11 and t.physical_branch == 2 for t in self.towers)
        has_t3 = any(t.type == TowerType.PHYSICAL and t.level >= 11 and t.physical_branch == 3 for t in self.towers)
        has_e1 = any(t.type == TowerType.TELEPORT and t.level >= 11 and t.teleport_branch == 1 for t in self.towers)
        has_e2 = any(t.type == TowerType.TELEPORT and t.level >= 11 and t.teleport_branch == 2 for t in self.towers)
        has_w1 = any(t.type == TowerType.WIND and t.level >= 11 and t.wind_branch == 1 for t in self.towers)
        has_tr1 = any(t.type == TowerType.TRIDENT and t.level >= 11 and t.trident_branch == 1 for t in self.towers)
        return has_t1 and has_t2 and has_t3 and has_e1 and has_e2 and has_w1 and has_tr1

    def endless_greed_explode(self, x, y):
        self.coins += 500
        exp = EndlessGreedExplosion(x, y, self)
        self.endless_greed_explosions.append(exp)

    def _crystal_cell_taken(self, col, row):
        return any(c.col == col and c.row == row for c in self.crystals)

    def _crystal_cell_forbidden(self, col, row):
        """起点（出生点）和终点（房子）格子上不生成不稳定水晶。"""
        return (col, row) == tuple(self.start_point) or (col, row) == tuple(self.end_point)

    def _crystal_cell_ok(self, col, row):
        return (not self._crystal_cell_forbidden(col, row)
                and not self._crystal_cell_taken(col, row))

    def try_spawn_crystal_near(self, x, y):
        if Enchantment.UNSTABLE_CRYSTAL not in self.enchantments:
            return
        if random.random() >= 0.10:
            return
        c0 = int(x) // TILE_SIZE
        r0 = int(y) // TILE_SIZE
        candidates = [(c, r) for (c, r) in self.path
                      if abs(c - c0) <= 2 and abs(r - r0) <= 2
                      and self._crystal_cell_ok(c, r)]
        if not candidates:
            return
        col, row = random.choice(candidates)
        self.crystals.append(UnstableCrystal(col, row, self))

    def spawn_crystals_fullmap(self):
        if Enchantment.UNSTABLE_CRYSTAL not in self.enchantments:
            return 0
        spawned = 0
        for col, row in self.path:
            if not self._crystal_cell_ok(col, row):
                continue
            if random.random() < 0.10:
                self.crystals.append(UnstableCrystal(col, row, self))
                spawned += 1
        # 保底 1 颗：核弹爆炸至少要能在道路上看到一颗不稳定水晶
        if spawned == 0:
            free = [(c, r) for (c, r) in self.path if self._crystal_cell_ok(c, r)]
            if free:
                col, row = random.choice(free)
                self.crystals.append(UnstableCrystal(col, row, self))
                spawned = 1
        return spawned

    def apply_acid_rain_downgrade(self, min_level=0):
        """酸雨侵蚀：场上所有炮塔等级 -1；护盾可以挡下，脉冲护盾免疫。

        min_level=1 时最低只降到 1 级（最终 BOSS 的酸雨技能用这个模式，不会直接删塔）。
        返回被侵蚀的炮塔数量。
        """
        affected = 0
        destroyed = []
        for t in self.towers:
            if t.level < 1:
                if min_level > 0:
                    continue
                if t.type in (TowerType.FLAME, TowerType.TRIDENT, TowerType.BOMB):
                    self.temperature -= 1
                elif t.type == TowerType.ICE:
                    self.temperature += 1
                destroyed.append(t)
                continue
            if t.level <= min_level:
                continue
            if t.in_pulse():
                continue
            if getattr(t, 'has_shield', False):
                t.break_shield()
                self.trigger_shield_burst(t)
                self.notify_tower_hit(t)
                continue
            if t.is_invincible():
                self.notify_tower_hit(t)   # 免疫归免疫，「被酸雨打了」照样算
                continue
            self.notify_tower_hit(t)
            old_level = t.level
            t.level -= 1
            t.upgrade_cost = int(t.upgrade_cost / 1.5)
            if t.type == TowerType.PRODUCTION:
                multiplier = 2 if t.is_on_gold_ore else 1
                self.gold_per_second -= multiplier
            if old_level > 1:
                if t.type == TowerType.PHYSICAL:
                    t.damage -= 15
                    t.range -= TILE_SIZE // 2
                    t.fire_rate = min(60, t.fire_rate + 6)
                elif t.type == TowerType.ICE:
                    t.damage -= 5
                    t.range -= TILE_SIZE // 4
                    t.fire_rate = min(60, t.fire_rate + 6)
                    if old_level >= 6:
                        t.freeze_time = round(t.freeze_time - 0.1, 1)
                    self.temperature += 1
                    # 神锅（分支 4）的数值来自独立数值表，逐项加减会算歪；
                    # 降到 Lv10 以下时也要顺手退回普通冰塔形态，所以整体重算一次。
                    t.recalculate_stats()
                elif t.type == TowerType.TELEPORT:
                    if t.teleport_branch == 2:
                        t.damage -= 100
                        t.range -= TILE_SIZE // 2
                        t.fire_rate = min(60, t.fire_rate + 6)
                    else:
                        t.damage -= 5
                        t.teleport_chance = max(0, t.teleport_chance - 0.01)
                        t.range -= TILE_SIZE // 4
                        t.fire_rate = min(60, t.fire_rate + 6)
                        if old_level >= 6:
                            t.oneshot_chance = max(0, t.oneshot_chance - 0.01)
                elif t.type == TowerType.FLAME:
                    t.damage -= 15
                    t.range -= TILE_SIZE // 4
                    t.fire_rate = min(60, t.fire_rate + 6)
                    if old_level >= 6:
                        t.stun_time = round(t.stun_time - 0.1, 1)
                    self.temperature -= 1
                elif t.type == TowerType.TRIDENT:
                    t.damage -= 25
                    t.range -= TILE_SIZE // 2
                    t.fire_rate = min(60, t.fire_rate + 6)
                    t.lightning_damage -= 50
                    self.temperature -= 1
                elif t.type == TowerType.WIND:
                    t.wind_knockback -= 12
                    if old_level >= 7:
                        t.damage -= 20
                        t.range -= TILE_SIZE // 2
                    elif old_level == 6:
                        t.damage -= 20
                        t.range -= TILE_SIZE // 2
                        t.fire_rate = min(60, t.fire_rate + 6)
                    else:
                        t.damage -= 5
                        t.range -= TILE_SIZE // 4
                        t.fire_rate = min(60, t.fire_rate + 6)
                elif t.type == TowerType.POISON:
                    t.damage -= 15
                    t.range -= TILE_SIZE // 2
                    t.fire_rate = min(60, t.fire_rate + 6)
                elif t.type == TowerType.BOMB:
                    t.damage -= 100
                    if old_level >= 11 and t.level < 11:
                        t.is_nuclear = False
                        base_range = int(TILE_SIZE * 2.2)
                        t.range = base_range + int(TILE_SIZE * 0.2) * (t.level - 1)
                        t.fire_rate = 120
                    self.temperature -= 1
                if t.type == TowerType.PRODUCTION:
                    multiplier = 2 if t.is_on_gold_ore else 1
                    if old_level >= 6:
                        self.gold_per_wave -= multiplier
                    if old_level >= 11:
                        self.emerald_per_wave -= EMERALD_PER_WAVE_BY_LEVEL.get(old_level, 3) - EMERALD_PER_WAVE_BY_LEVEL.get(t.level, 0)
                t.update_sprite()
                if t.type == TowerType.FLAME:
                    # 火系各分支数值差异较大（提灯走独立表），统一按等级重算
                    t.recalculate_stats()
            affected += 1
        for t in destroyed:
            if self.selected_tower is t:
                self.selected_tower = None
            t.kill()
        return affected

    def _shop_pool(self):
        return [e for e in ENCHANTMENT_ORDER
                if (e.value >= 10 or e in NON_REPEATABLE_ENCHANTMENTS) and e not in self.enchantments
                or (e.value < 10 and e not in NON_REPEATABLE_ENCHANTMENTS)]

    def open_shop(self):
        if self.shop_offers_wave != self.wave_manager.current_wave or not self.shop_offers:
            self.reroll_shop()
        self.state = GameState.SHOP
        self.save_game()

    def reroll_shop(self):
        pool = self._shop_pool()
        self.shop_offers = random.sample(pool, min(3, len(pool)))
        self.shop_offers_wave = self.wave_manager.current_wave

    def refresh_shop(self):
        if self.emeralds < 20:
            return
        self.emeralds -= 20
        self.reroll_shop()
        self.save_game()

    def close_shop(self):
        self.state = GameState.PLAYING
        self.wave_manager.start_new_wave()
        self.wave_manager.wave_timer = 0
        self.select_weather()
        self.weather_banner_timer = 180

    def buy_enchantment(self, ench):
        if (ench.value >= 10 or ench in NON_REPEATABLE_ENCHANTMENTS) and ench in self.enchantments:
            return
        cost = ENCHANTMENT_DATA[ench]["cost"]
        if self.emeralds < cost:
            return
        self.emeralds -= cost
        self.enchantments.append(ench)
        if ench in self.shop_offers:
            self.shop_offers.remove(ench)
        if assets.trader_accept_sound:
            audio.play_sound(assets.trader_accept_sound)
        self.save_game()

    def update(self):
        # 「重新开始」二次确认窗口：放在所有提前返回之前，
        # 保证暂停 / 统计弹窗 / 图鉴打开时窗口也会正常过期，
        # 不会出现「很久以前点过一次，回来一点就删档」的情况。
        if self.confirm_reset > 0:
            self.confirm_reset -= 1

        if self.stats_open or self.codex.open:
            return
        if self.state == GameState.PAUSED:
            return
        # 大招动画独立于游戏状态推进：暂停时冻结、结束后自动清空并结算
        if self.ultimate_video is not None:
            if not self.ultimate_video.update():
                self.ultimate_video = None
                if self.masterpiece_pending:
                    self.masterpiece_pending = False
                    self.resolve_masterpiece_ultimate()

        if self.state == GameState.PLAYING:
            self.game_time += 1
            self._lantern_towers = sum(
                1 for t in self.towers
                if t.type == TowerType.FLAME and t.level == 15 and t.flame_branch == 3)
            if self.pending_first_wave_weather and self.wave_manager.wave_timer <= 0:
                self.select_weather()
                if self.wave_manager.current_wave != 50:
                    self.weather_banner_timer = 180
                self.pending_first_wave_weather = False
            self.global_production()
            if Enchantment.LAVA in self.enchantments:
                self.lava_timer += 1
                if self.lava_timer >= 5 * 60:
                    self.lava_timer = 0
                    self.temperature += 1

            for enemy in self.enemies:
                reached_end = enemy.update()
                if reached_end:
                    enemy.kill()
                    self.state = GameState.GAME_OVER
                    self.stats_open = True

            if Enchantment.BLAZE_POWDER in self.enchantments:
                for enemy in self.enemies:
                    enemy.apply_burn(self.temperature, 999999)

            self._build_enemy_grid()
            self.update_boss_fx()

            self.apply_time_buffs()

            frozen_by_boss = self.boss_time_frozen > 0
            for tower in self.towers:
                if tower.hit_energy_cd > 0:
                    tower.hit_energy_cd -= 1
                if tower.disabled_timer > 0:
                    tower.disabled_timer -= 1
                if tower.type not in (TowerType.PRODUCTION, TowerType.TIME):
                    if frozen_by_boss or tower.disabled_timer > 0:
                        tower.update_shield_tower()
                        continue
                    bullets = tower.attack(self.game_time)
                    for bullet in bullets:
                        self.bullets.add(bullet)
                tower.update_shield_tower()

            self.bullets.update()
            self.damage_texts.update()
            self.dragons.update()
            for dragon in list(self.dragons):
                if dragon.done:
                    dragon.kill()

            self.update_weather_particles()
            if self.weather_banner_timer > 0:
                self.weather_banner_timer -= 1

            if self.weather == Weather.FOG:
                if self.lantern_active():
                    # 灯火通明：全场迷雾被永久驱散，计时器也压住不让它重新聚集
                    self.fog_visible = False
                    self.fog_timer = 0
                elif not self.fog_visible:
                    if self.fog_timer > 0:
                        self.fog_timer -= 1
                    else:
                        self.fog_visible = True

            if self.weather == Weather.ENDLESS_NIGHT:
                self.night_dark_timer += 1
                if self.final_boss is not None:
                    # 最终BOSS战期间不压黑屏，否则弹幕与预警看不清
                    self.fog_visible = False
                elif self.night_dark_timer >= 1800:
                    self.night_dark_timer = 0
                    self.fog_visible = True
                    for enemy in self.enemies:
                        # 永夜的回复不能复活已经倒下的最终BOSS
                        if getattr(enemy, "is_boss", False) or enemy.health <= 0:
                            continue
                        heal_amount = int(enemy.max_health * 0.05)
                        enemy.health = min(enemy.health + heal_amount, enemy.max_health)
                if self.fog_visible and self.night_dark_timer >= 300:
                    self.fog_visible = False

                self.herobrine_summon_timer += 1
                summon_interval = 30 if self.herobrine_phase == 2 else 60
                if self.herobrine_summon_queue and self.herobrine_summon_timer >= summon_interval:
                    self.herobrine_summon_timer = 0
                    enemy_type = self.herobrine_summon_queue.pop(0)
                    enemy = Enemy(self.path, enemy_type, self)
                    self.enemies.add(enemy)

                self.command_block_timer += 1
                initial_delay = 45 * 60
                interval = 30 * 60
                if self.wave_manager.current_wave == 50 and self.command_block_timer >= initial_delay and (self.command_block_timer - initial_delay) % interval == 0:
                    towers_list = list(self.towers)
                    if towers_list:
                        target_tower = random.choice(towers_list)
                        self.command_blocks.append({
                            'x': target_tower.x,
                            'y': target_tower.y,
                            'timer': 0,
                            'max_timer': 3 * 60
                        })
                        self.weather_banner_text = "HIM释放会爆炸的命令方块了!"
                        self.weather_banner_timer = 180

                for cb in list(self.command_blocks):
                    cb['timer'] += 1
                    if cb['timer'] >= cb['max_timer']:
                        self.command_blocks.remove(cb)
                        blast = cb.get('radius', 1)
                        for tower in list(self.towers):
                            dx = abs(tower.x - cb['x'])
                            dy = abs(tower.y - cb['y'])
                            if dx <= blast and dy <= blast:
                                if tower.in_pulse():
                                    continue
                                if getattr(tower, 'has_shield', False):
                                    tower.break_shield()
                                    self.trigger_shield_burst(tower)
                                    self.notify_tower_hit(tower)
                                elif tower.is_invincible():
                                    self.notify_tower_hit(tower)
                                    continue
                                else:
                                    self.notify_tower_hit(tower)
                                    self.destroy_tower_by_boss(tower)
                        for wall in list(self.ice_walls):
                            dx = abs(wall.x - cb['x'])
                            dy = abs(wall.y - cb['y'])
                            if dx <= blast and dy <= blast:
                                self.destroy_ice_wall(wall)
                        explosion = TNTExplosion(cb['x'] * TILE_SIZE + TILE_SIZE // 2,
                                                 cb['y'] * TILE_SIZE + TILE_SIZE // 2,
                                                 0, 0, None, self)
                        self.tnt_explosions.append(explosion)

            if self.wave_manager.current_wave in (50, FINAL_BOSS_WAVE):
                if not audio.music_busy():
                    boss_bgm = None
                    for bgm in assets.bgm_files:
                        if "Celestial Fury" in bgm or "The End" in bgm:
                            boss_bgm = bgm
                            break
                    if boss_bgm:
                        audio.play_music(assets.resource_path(boss_bgm), -1)
            else:
                if not audio.music_busy():
                    self.play_random_bgm()

            for pool in self.dragon_breath_pools[:]:
                if not pool.update(self.game_time):
                    self.dragon_breath_pools.remove(pool)

            for effect in self.lightning_effects[:]:
                effect.update()
                if effect.done:
                    self.lightning_effects.remove(effect)

            for explosion in self.wind_explosions[:]:
                if not explosion.update():
                    self.wind_explosions.remove(explosion)

            for explosion in self.endless_greed_explosions[:]:
                if not explosion.update():
                    self.endless_greed_explosions.remove(explosion)

            for exp in self.ice_explosions[:]:
                if not exp.update():
                    self.ice_explosions.remove(exp)

            for burst in self.ice_star_bursts[:]:
                if not burst.update():
                    self.ice_star_bursts.remove(burst)

            for wave_fx in self.masterpiece_shockwaves[:]:
                if not wave_fx.update():
                    self.masterpiece_shockwaves.remove(wave_fx)

            for bagua in self.bagua_arrays[:]:
                if not bagua.update():
                    self.bagua_arrays.remove(bagua)

            for ray in self.hell_rays[:]:
                if not ray.update():
                    self.hell_rays.remove(ray)

            for storm in self.resonance_storms[:]:
                if not storm.update():
                    self.resonance_storms.remove(storm)

            for wave_fx in self.lantern_shockwaves[:]:
                if not wave_fx.update():
                    self.lantern_shockwaves.remove(wave_fx)

            for star in self.stars[:]:
                if not star.update():
                    self.stars.remove(star)

            for meteor in self.meteors[:]:
                if meteor.done:
                    self.meteors.remove(meteor)
                else:
                    meteor.update()

            for splash in self.poison_splashes[:]:
                if not splash.update():
                    self.poison_splashes.remove(splash)

            for splash in self.wither_splashes[:]:
                if not splash.update():
                    self.wither_splashes.remove(splash)

            for effect in self.horizontal_lightning_effects[:]:
                effect.update()
                if effect.done:
                    self.horizontal_lightning_effects.remove(effect)

            for explosion in self.tnt_explosions[:]:
                explosion.update()
                if explosion.done:
                    self.tnt_explosions.remove(explosion)

            for explosion in self.creeper_explosions[:]:
                explosion.update()
                if explosion.done:
                    self.creeper_explosions.remove(explosion)

            for wall in self.ice_walls[:]:
                if not wall.update():
                    pass

            for explosion in self.mushroom_explosions[:]:
                explosion.update()
                if explosion.done:
                    self.mushroom_explosions.remove(explosion)

            for sw in self.shockwave_effects[:]:
                sw.update()
                if sw.done:
                    self.shockwave_effects.remove(sw)

            if self.bee_spawn_remaining > 0:
                self.bee_spawn_timer += 1
                if self.bee_spawn_timer >= 30:
                    self.bee_spawn_timer = 0
                    self.bee_spawn_remaining -= 1
                    ex, ey = self.end_point
                    cx = ex * TILE_SIZE + TILE_SIZE // 2
                    cy = ey * TILE_SIZE + TILE_SIZE // 2
                    sx, sy = self.start_point
                    base_angle = math.atan2(
                        (sy * TILE_SIZE + TILE_SIZE // 2) - cy,
                        (sx * TILE_SIZE + TILE_SIZE // 2) - cx)
                    n = 5
                    spread = math.radians(120)
                    radius = TILE_SIZE * 0.6
                    for i in range(n):
                        a = base_angle - spread / 2 + spread * i / (n - 1)
                        bx = cx + math.cos(a) * radius
                        by = cy + math.sin(a) * radius
                        self.bees.append(Bee(bx, by, self))
            for bee in self.bees[:]:
                if not bee.update():
                    self.bees.remove(bee)

            for crystal in self.crystals[:]:
                if not crystal.update():
                    self.crystals.remove(crystal)

            if self.weather == Weather.THUNDERSTORM:
                self.thunderstorm_timer += 1
                if self.thunderstorm_timer >= 180:
                    self.thunderstorm_timer = 0
                    col = random.randint(0, GRID_WIDTH - 1)
                    hit_enemy = None
                    for enemy in self.enemies:
                        if enemy.health > 0 and enemy.rect.centerx // TILE_SIZE == col:
                            hit_enemy = enemy
                            break
                    if hit_enemy:
                        for enemy in self.enemies:
                            e_col = enemy.rect.centerx // TILE_SIZE
                            if e_col == col and enemy.health > 0:
                                reward = enemy.take_damage(50, color=ELECTRIC_PURPLE, element="electric")
                                self.coins += reward
                                enemy.apply_burn(self.temperature, 240)
                                enemy.on_lightning_hit()
                        self.add_lightning((col + 0.5) * TILE_SIZE, 800, False)

            for enemy in list(self.enemies):
                if enemy.health <= 0:
                    self.enemies_killed += 1
                    enemy.kill()

            if self.wave_manager.current_wave in (50, FINAL_BOSS_WAVE) and self.wave_manager.wave_timer > 0:
                self.wave_manager.update()
            elif self.wave_manager.is_wave_complete(self.enemies):
                self.apply_production_bonus()
                if self.wave_manager.is_game_complete(self.enemies):
                    self.state = GameState.VICTORY
                    self.stats_open = True
                elif self.wave_manager.current_wave % 4 == 0:
                    self.open_shop()
                else:
                    self.wave_manager.start_new_wave()
                    self.wave_manager.wave_timer = 0
                    self.select_weather()
                    self.weather_banner_timer = 180
            else:
                enemy_type = self.wave_manager.update()
                if enemy_type:
                    if enemy_type == EnemyType.FINAL_BOSS:
                        boss = FinalBoss(self.path, enemy_type, self)
                        self.enemies.add(boss)
                        self.final_boss = boss
                        self.start_boss_fight()
                    else:
                        enemy = Enemy(self.path, enemy_type, self)
                        self.enemies.add(enemy)
                        if enemy_type == EnemyType.HEROBRINE:
                            self.force_boss_weather()
                            self.herobrine_spawned = True
                            for _ in range(5):
                                self.herobrine_summon_queue.append(EnemyType.SLIME)
                            for _ in range(5):
                                self.herobrine_summon_queue.append(EnemyType.MAGMA_CUBE)


    def _roll_weather(self, wave_num):
        """按波数抽取天气（50 / 100 波固定永夜）。"""
        if wave_num in (50, FINAL_BOSS_WAVE):
            return Weather.ENDLESS_NIGHT
        pool = list(WEATHER_POOL)
        if 50 < wave_num < FINAL_BOSS_WAVE:
            pool.append(Weather.ENDLESS_NIGHT)
        return random.choice(pool)

    def select_weather(self):
        self.fog_visible = False
        self.lava_timer = 0
        self.weather = self._roll_weather(self.wave_manager.current_wave)
        self._build_background(night_mode=(self.weather == Weather.ENDLESS_NIGHT),
                               gold_ore_positions=self.gold_ore_positions)
        base_temp = WEATHER_CONFIG[self.weather]["temp"]
        self.temperature = base_temp
        for t in self.towers:
            if t.type in (TowerType.FLAME, TowerType.TRIDENT):
                self.temperature += t.level
            elif t.type == TowerType.ICE:
                self.temperature -= t.level
            elif t.type == TowerType.BOMB:
                self.temperature += self.get_bomb_temp_effect(t)
            elif t.type == TowerType.SHIELD and t.level >= 11:
                if t.shield_branch == 2:
                    self.temperature -= t.level
        self.temperature += self.enchantment_temp_bonus()
        self.save_game()
        self.weather_banner_text = WEATHER_CONFIG[self.weather]["desc"]
        if self.weather == Weather.ACID_RAIN and Enchantment.WAX in self.enchantments:
            self.bee_spawn_remaining = 10
            self.bee_spawn_timer = 0
        if self.weather == Weather.ENDLESS_NIGHT and not self.herobrine_spawned:
            audio.stop_music()
            boss_bgm = None
            for bgm in assets.bgm_files:
                if "Celestial Fury" in bgm or "The End" in bgm:
                    boss_bgm = bgm
                    break
            if boss_bgm:
                audio.play_music(assets.resource_path(boss_bgm), -1)
        if self.weather == Weather.ACID_RAIN:
            if Enchantment.WAX not in self.enchantments:
                self.apply_acid_rain_downgrade()
            for enemy in self.enemies:
                enemy.apply_poison(10)
        if self.weather == Weather.SCORCHING_SUN and self.temperature > 0:
            for enemy in self.enemies:
                enemy.burn_damage = max(enemy.burn_damage, self.temperature)
                enemy.burn_time = max(enemy.burn_time, 999999)
        if self.weather == Weather.FIRE_RAIN and self.temperature > 0:
            for enemy in self.enemies:
                enemy.burn_damage = max(enemy.burn_damage, self.temperature)
                enemy.burn_time = max(enemy.burn_time, 999999)
        if self.weather == Weather.FOG:
            self.fog_visible = False
            self.fog_timer = 180
        if self.weather == Weather.MAGNETIC_STORM:
            for enemy in self.enemies:
                if enemy.enemy_type in (EnemyType.IRON_ARMORED, EnemyType.GOLD_ARMORED, EnemyType.DIAMOND_ARMORED, EnemyType.NETHERITE_ARMORED):
                    enemy.broken = True

    def play_random_bgm(self):
        if not assets.bgm_files:
            return
        if len(assets.bgm_files) == 1:
            idx = 0
        else:
            available = [i for i in range(len(assets.bgm_files)) if i != assets.bgm_index]
            idx = random.choice(available)
        assets.bgm_index = idx
        audio.play_music(assets.resource_path(assets.bgm_files[idx]), 0)

    def update_weather_particles(self):
        if self.weather in (Weather.RAINY, Weather.THUNDERSTORM, Weather.ACID_RAIN):
            if random.random() < 0.4:
                x = random.randint(0, SCREEN_WIDTH)
                y = random.randint(-20, 0)
                speed = random.randint(12, 18)
                length = random.randint(8, 15)
                tag = "acid_rain" if self.weather == Weather.ACID_RAIN else "rain"
                self.weather_particles.append([x, y, speed, length, tag])
        elif self.weather == Weather.SNOWY:
            if random.random() < 0.3:
                x = random.randint(0, SCREEN_WIDTH)
                y = random.randint(-20, 0)
                speed = random.uniform(1, 3)
                drift = random.uniform(-0.5, 0.5)
                size = random.randint(2, 5)
                self.weather_particles.append([x, y, speed, drift, size, "snow"])
        elif self.weather == Weather.FIRE_RAIN:
            if random.random() < 0.3:
                x = random.randint(0, SCREEN_WIDTH)
                y = random.randint(SCREEN_HEIGHT, SCREEN_HEIGHT + 40)
                speed = random.uniform(1, 3)
                drift = random.uniform(-0.3, 0.3)
                size = random.randint(4, 10)
                phase = random.uniform(0, 6.28)
                self.weather_particles.append([x, y, speed, drift, size, phase, "fire"])

        for p in self.weather_particles:
            if p[-1] in ("rain", "acid_rain"):
                p[1] += p[2]
            elif p[-1] == "snow":
                p[1] += p[2]
                p[0] += p[3]
            elif p[-1] == "fire":
                p[1] -= p[2]
                p[0] += p[3]
                p[5] += 0.1

        self.weather_particles = [
            p for p in self.weather_particles
            if not ((p[-1] in ("rain", "acid_rain") and p[1] > SCREEN_HEIGHT) or
                    (p[-1] == "snow" and (p[1] > SCREEN_HEIGHT or p[0] < 0 or p[0] > SCREEN_WIDTH)) or
                    (p[-1] == "fire" and p[1] < -40))
        ]

    def draw(self):
        self.screen.fill(BLACK)
        if self.state == GameState.MENU:
            self.ui_manager.draw_menu()
        elif self.state in (GameState.PLAYING, GameState.WAVE_PREPARATION, GameState.PAUSED):
            self.ui_manager.draw_game()
        elif self.state == GameState.SHOP:
            self.ui_manager.draw_game()
            self.ui_manager.draw_shop()
        elif self.state == GameState.GAME_OVER:
            self.ui_manager.draw_game_over()
        elif self.state == GameState.VICTORY:
            self.ui_manager.draw_victory()
        if self.codex.open:
            self.codex.draw(self.screen)
            pygame.display.flip()
            return
        if self.stats_open and self.state != GameState.MENU:
            self.ui_manager.draw_damage_stats()
        pygame.display.flip()

    def get_tower_at(self, x, y):
        for t in self.towers:
            if t.x == x and t.y == y:
                return t
        return None

    def can_build_tower(self, x, y):
        if x < 0 or x >= GRID_WIDTH or y < 1 or y > GRID_HEIGHT:
            return False
        if (x, y) in self.path:
            return False
        if self.get_tower_at(x, y):
            return False
        costs = {ttype: cost for ttype, name, cost, key in TOWER_DATA}
        return self.coins >= costs.get(self.selected_tower_type, 9999)

    def build_tower(self, x, y, tower_type):
        costs = {ttype: cost for ttype, name, cost, key in TOWER_DATA}
        cost = costs[tower_type]
        if self.coins >= cost:
            self.coins -= cost
            t = Tower(tower_type, x, y, self)
            self.towers.add(t)
            if tower_type == TowerType.PRODUCTION:
                multiplier = 2 if (x, y) in self.gold_ore_positions else 1
                self.gold_per_second += multiplier
            if tower_type in (TowerType.FLAME, TowerType.TRIDENT):
                self.temperature += 1
            elif tower_type == TowerType.ICE:
                self.temperature -= 1
            elif tower_type == TowerType.BOMB:
                self.temperature += self.get_bomb_temp_effect(t)

    def start_game(self):
        if self.load_game():
            return
        try:
            os.remove(get_save_path())
        except Exception:
            pass
        try:
            os.remove(resource_path("save.json"))
        except Exception:
            pass
        self.state = GameState.PLAYING
        self.wave_manager.start_new_wave()
        self.pending_first_wave_weather = True
        self.weather_banner_text = "准备时间"
        self.weather_banner_timer = 240

    def restart_wave(self):
        """从本波开头重来：炮塔 / 金币 / 附魔 / 温度全部保留，只把这一波清场重打。

        和 reset_game 的区别是「不碰存档、不碰炮塔」，所以只需要清掉场上的敌人、
        子弹和一次性特效，再把 wave_manager 的生成进度归零 —— 不调用 start_new_wave，
        波数保持不变，同一波从头再打一遍。
        """
        self.enemies.empty()
        self.bullets.empty()
        self.dragons.empty()
        self.damage_texts.empty()

        for attr in ("dragon_breath_pools", "lightning_effects", "wind_explosions",
                     "endless_greed_explosions", "ice_explosions", "hell_rays",
                     "resonance_storms", "poison_splashes", "wither_splashes",
                     "horizontal_lightning_effects", "tnt_explosions",
                     "mushroom_explosions", "shockwave_effects", "meteors", "bees",
                     "crystals", "lantern_shockwaves", "stars", "ice_star_bursts",
                     "masterpiece_shockwaves", "weather_particles",
                     "command_blocks", "ice_walls"):
            getattr(self, attr, []).clear()

        # 第 50 / 100 波死亡重来时，BOSS 相关状态必须一起复位，否则不会重新召唤
        self._init_boss_state()
        self.herobrine = None
        self.herobrine_spawned = False
        self.herobrine_summon_timer = 0
        self.herobrine_phase = 0
        self.herobrine_summon_queue = []

        self.bee_spawn_remaining = 0
        self.bee_spawn_timer = 0
        self.thunderstorm_timer = 0
        self.fog_timer = 0
        self.fog_visible = False
        self.night_dark_timer = 0
        self.enemy_grid = {}
        self._lantern_towers = 0
        self.ultimate_video = None
        self.masterpiece_pending = False

        # 本波从头再打：只把生成进度归零，波数不变
        wm = self.wave_manager
        wm.enemies_spawned = 0
        wm.gold_armored_spawned = 0
        wm.ghost_spawned = 0
        wm.spawn_timer = 0
        wm.wave_timer = 0

        self.state = GameState.PLAYING
        self.stats_open = False
        self.confirm_reset = 0
        self.selected_tower = None
        self.weather_banner_timer = 0

    def reset_game(self):
        # 存档不删除，改成改名备份：.bak 会被下一次 save_game 覆盖，
        # 但至少在「开新局后立刻后悔」的窗口里还能捞回来。
        # 原先是 os.remove —— 配合菜单隐形热区，等于点一下就永久丢档。
        save_path = get_save_path()
        if os.path.exists(save_path):
            try:
                os.replace(save_path, save_path + ".bak")
            except Exception:
                pass
        self.confirm_reset = 0
        self.path = random.choice(SEED_PATHS)
        self.start_point = self.path[0]
        self.end_point = self.path[-1]
        self._build_background()
        self.enemies.empty()
        self.towers.empty()
        self.bullets.empty()
        self.damage_texts.empty()
        self.damage_stats.reset()
        self.damage_element = None
        self.stats_open = False

        self.coins = 2500
        self.emeralds = 100
        self.wave_manager = WaveManager()
        self.selected_tower_type = None
        self.selected_tower = None
        self.show_range = False
        self.enemies_killed = 0
        self.game_time = 0
        self.gold_per_second = 0
        self.gold_per_wave = 0
        self.emerald_per_wave = 0
        self.last_global_production_time = pygame.time.get_ticks()
        self.temperature = 30
        self.lava_timer = 0
        self.weather = Weather.SUNNY
        self.weather_particles = []
        self.weather_banner_timer = 0
        self.weather_banner_text = ""
        self.dragon_breath_pools = []
        self.lightning_effects = []
        self.wind_explosions = []
        self.endless_greed_explosions = []
        self.ice_explosions = []
        self.hell_rays = []
        self.resonance_storms = []
        self.poison_splashes = []
        self.wither_splashes = []
        self.horizontal_lightning_effects = []
        self.tnt_explosions = []
        self.mushroom_explosions = []
        self.shockwave_effects = []
        self.thunderstorm_timer = 0
        self.resonance_counter = 0
        self.masterpiece_counter = 0     # 臻品呈现：场上所有神锅共用的攻击计数
        self.sacrifices = 0
        self.meteors = []
        self.bees = []
        self.bee_spawn_remaining = 0
        self.bee_spawn_timer = 0
        self.crystals = []
        self.lantern_shockwaves = []
        self.stars = []
        self.ice_star_bursts = []
        self.masterpiece_shockwaves = []
        self.bagua_arrays = []
        self.ultimate_video = None
        self.masterpiece_pending = False   # 视频播完才结算，标记「这一发还没落地」
        self._lantern_towers = 0
        self.enemy_grid = {}
        self.fog_timer = 0
        self.fog_visible = False
        self.pending_first_wave_weather = False
        self.enchantments = []
        self.poison_base_damage = 5
        self.shop_offers = []
        self.shop_offers_wave = -1
        self._init_boss_state()
        self.start_game()

    def run(self):
        """主循环。

        包一层 crash log：玩家报告「游戏闪退了」时，没有日志就只能靠猜。
        日志写到存档同目录（一定有写权限），把完整 traceback 落盘，
        同时仍然抛出，保留正常的非零退出码。
        """
        try:
            while True:
                self.handle_events()
                self.update()
                self.draw()
                self.clock.tick(self.fps)
        except SystemExit:
            raise
        except Exception:
            import traceback
            detail = traceback.format_exc()
            try:
                log_path = os.path.join(os.path.dirname(get_save_path()), "crash.log")
                with open(log_path, "a", encoding="utf-8") as f:
                    f.write(f"\n===== {time.strftime('%Y-%m-%d %H:%M:%S')} =====\n")
                    f.write(detail)
            except Exception:
                pass
            print(detail)
            raise