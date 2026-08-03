import pygame
import random
import math
import json
import sys
import os
import assets
from config import *
from enemy import Enemy, DamageText
from tower import Tower, Bullet, BombBullet, NuclearMissile, WitherBullet
from effects import WindExplosion, IceExplosion, DragonBreathPool, LightningEffect, HorizontalLightningEffect, PoisonSplash, TNTExplosion, MushroomExplosion, NuclearShockwave, WitherSplash
from wave_manager import WaveManager
from ui import UIManager, get_tower_info
from dragons import Dragon


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
        self.coins = 2560
        self.lives = 20
        self.wave_manager = WaveManager()
        self.selected_tower_type = None
        self.selected_tower = None
        self.show_range = False
        self.enemies_killed = 0
        self.game_time = 0
        self.gold_per_second = 0
        self.gold_per_wave = 0
        self.gold_profit_per_wave = 0
        self.last_global_production_time = pygame.time.get_ticks()
        self.temperature = 30
        self.weather = Weather.SUNNY
        self.weather_particles = []
        self.weather_banner_timer = 0
        self.weather_banner_text = ""
        self.pending_first_wave_weather = False
        self.TOWER_DATA = TOWER_DATA

        self.dragon_breath_pools = []
        self.lightning_effects = []
        self.wind_explosions = []
        self.ice_explosions = []
        self.poison_splashes = []
        self.wither_splashes = []
        self.horizontal_lightning_effects = []
        self.tnt_explosions = []
        self.creeper_explosions = []
        self.mushroom_explosions = []
        self.shockwave_effects = []
        self.thunderstorm_timer = 0

        self.fog_timer = 0
        self.fog_visible = False
        self.weather_forecast = []
        self.forecast_purchased = False
        self.forecast_weather_idx = -1

        self.night_dark_timer = 0
        self.herobrine_phase = 0
        self.herobrine_spawned = False
        self.herobrine = None
        self.herobrine_summon_timer = 0
        self.herobrine_summon_queue = []

        self.command_block_timer = 0
        self.command_blocks = []
        self.ice_walls = []

        self.path = random.choice(SEED_PATHS)
        self.start_point = self.path[0]
        self.end_point = self.path[-1]
        self.background_surface = None
        self.enemy_grid = {}
        self._build_background()

        self.ui_manager = UIManager(self)

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
            col = e.rect.centerx // TILE_SIZE
            row = e.rect.centery // TILE_SIZE
            self.enemy_grid.setdefault((col, row), []).append(e)

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                import sys
                sys.exit()

            if event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:
                    mouse_x, mouse_y = pygame.mouse.get_pos()

                    if (RESTART_BTN_X <= mouse_x <= RESTART_BTN_X + RESTART_BTN_WIDTH and
                            RESTART_BTN_Y <= mouse_y <= RESTART_BTN_Y + RESTART_BTN_HEIGHT):
                        self.reset_game()
                        return

                    if (EXIT_BTN_X <= mouse_x <= EXIT_BTN_X + EXIT_BTN_WIDTH and
                            EXIT_BTN_Y <= mouse_y <= EXIT_BTN_Y + EXIT_BTN_HEIGHT):
                        pygame.quit()
                        import sys
                        sys.exit()

                    grid_x = mouse_x // TILE_SIZE
                    grid_y = mouse_y // TILE_SIZE

                    if self.state == GameState.MENU:
                        if 900 <= mouse_x <= 1660 and 840 <= mouse_y <= 920:
                            self.start_game()
                        elif 900 <= mouse_x <= 1660 and 1020 <= mouse_y <= 1100:
                            pygame.quit()
                            import sys
                            sys.exit()

                    elif self.state in (GameState.PLAYING, GameState.WAVE_PREPARATION):
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

                    elif self.state in (GameState.GAME_OVER, GameState.VICTORY):
                        if 900 <= mouse_x <= 1660 and 850 <= mouse_y <= 930:
                            self.reset_game()

                    if (FORECAST_BTN_X <= mouse_x <= FORECAST_BTN_X + FORECAST_BTN_WIDTH and
                            FORECAST_BTN_Y <= mouse_y <= FORECAST_BTN_Y + FORECAST_BTN_HEIGHT):
                        if self.state == GameState.PLAYING and not self.forecast_purchased and self.wave_manager.current_wave < 47 and self.coins >= 100 * self.wave_manager.current_wave:
                            self.coins -= 100 * self.wave_manager.current_wave
                            self.forecast_purchased = True
                            self.forecast_weather_idx = self.wave_manager.current_wave
                            if self.forecast_weather_idx < len(self.weather_forecast):
                                w = self.weather_forecast[self.forecast_weather_idx]
                                self.weather_banner_text = f"下波天气：{WEATHER_CONFIG[w]['desc']}"
                                self.weather_banner_timer = 120

            elif event.type == pygame.KEYDOWN:
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
                                assets.level_up_sound.play()
                            if tower.type in (TowerType.FLAME, TowerType.TRIDENT):
                                self.temperature += 1
                            elif tower.type == TowerType.ICE:
                                self.temperature -= 1
                                self.temperature = max(-273, self.temperature)
                            elif tower.type == TowerType.BOMB:
                                new_effect = self.get_bomb_temp_effect(tower)
                                self.temperature += (new_effect - old_effect)
                                self.temperature = max(-273, self.temperature)
                    elif event.key == pygame.K_e and self.selected_tower:
                        for _ in range(5):
                            tower = self.selected_tower
                            if tower.level >= 15 or self.coins < tower.upgrade_cost:
                                break
                            self.coins -= tower.upgrade_cost
                            old_effect = self.get_bomb_temp_effect(tower) if tower.type == TowerType.BOMB else 0
                            tower.upgrade()
                            if assets.level_up_sound and tower.level in (6, 11):
                                assets.level_up_sound.play()
                            if tower.type in (TowerType.FLAME, TowerType.TRIDENT):
                                self.temperature += 1
                            elif tower.type == TowerType.ICE:
                                self.temperature -= 1
                                self.temperature = max(-273, self.temperature)
                            elif tower.type == TowerType.BOMB:
                                new_effect = self.get_bomb_temp_effect(tower)
                                self.temperature += (new_effect - old_effect)
                                self.temperature = max(-273, self.temperature)
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
                        self.temperature = max(-273, self.temperature)
                    elif event.key == pygame.K_r and self.selected_tower and self.selected_tower.type == TowerType.POISON:
                        max_branch = 3 if self.selected_tower.level >= 11 else 2
                        self.selected_tower.poison_branch = self.selected_tower.poison_branch % max_branch + 1
                        self.selected_tower.update_sprite()
                    elif event.key == pygame.K_r and self.selected_tower and self.selected_tower.type == TowerType.PHYSICAL and self.selected_tower.level >= 11:
                        self.selected_tower.physical_branch = 3 - self.selected_tower.physical_branch
                        self.selected_tower.update_sprite()
                    elif event.key == pygame.K_r and self.selected_tower and self.selected_tower.type == TowerType.WIND and self.selected_tower.level >= 11:
                        self.selected_tower.wind_branch = 3 - self.selected_tower.wind_branch
                        self.selected_tower.update_sprite()
                    elif event.key == pygame.K_r and self.selected_tower and self.selected_tower.type == TowerType.ICE and self.selected_tower.level >= 11:
                        self.selected_tower.ice_branch = self.selected_tower.ice_branch % 3 + 1
                        self.selected_tower.update_sprite()
                    elif event.key == pygame.K_r and self.selected_tower and self.selected_tower.type == TowerType.FLAME and self.selected_tower.level >= 11:
                        self.selected_tower.flame_branch = 3 - self.selected_tower.flame_branch
                        self.selected_tower.update_sprite()
                    elif event.key == pygame.K_r and self.selected_tower and self.selected_tower.type == TowerType.TRIDENT and self.selected_tower.level >= 11:
                        self.selected_tower.trident_branch = 3 - self.selected_tower.trident_branch
                        self.selected_tower.update_sprite()
                    elif event.key == pygame.K_r and self.selected_tower and self.selected_tower.type == TowerType.TELEPORT:
                        self.selected_tower.teleport_branch = 3 - self.selected_tower.teleport_branch
                        self.selected_tower.recalculate_stats()
                        self.selected_tower.update_sprite()
                    elif event.key == pygame.K_r and self.selected_tower and self.selected_tower.type == TowerType.SHIELD and self.selected_tower.level >= 11:
                        self.selected_tower.shield_branch = self.selected_tower.shield_branch % 4 + 1
                        self.selected_tower.update_sprite()
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
                                self.gold_profit_per_wave -= (level - 10) * 0.001 * multiplier
                        if self.selected_tower.type in (TowerType.FLAME, TowerType.TRIDENT):
                            self.temperature -= self.selected_tower.level
                        elif self.selected_tower.type == TowerType.ICE:
                            self.temperature += self.selected_tower.level
                        elif self.selected_tower.type == TowerType.BOMB:
                            old_temp_effect = self.get_bomb_temp_effect(self.selected_tower)
                            self.temperature -= old_temp_effect
                        elif self.selected_tower.type == TowerType.SHIELD and self.selected_tower.level >= 11:
                            if self.selected_tower.shield_branch == 1:
                                self.temperature -= self.selected_tower.level
                            elif self.selected_tower.shield_branch == 2:
                                self.temperature += self.selected_tower.level
                            elif self.selected_tower.shield_branch == 4:
                                pass
                        self.temperature = max(-273, self.temperature)
                        self.selected_tower.kill()
                        self.selected_tower = None
                    elif event.key == pygame.K_ESCAPE:
                        if self.state in (GameState.PLAYING, GameState.WAVE_PREPARATION):
                            self.pre_pause_state = self.state
                            self.state = GameState.PAUSED
                        elif self.state == GameState.PAUSED:
                            self.state = self.pre_pause_state
                            self.pre_pause_state = None
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
                    damage = (tower.level - 10) * 36 * abs(self.temperature)
                    for enemy in self.enemies:
                        enemy.take_damage(damage, color=(255, 100, 0))
                        enemy.burn_time = float('inf')
                        enemy.burn_damage = max(enemy.burn_damage, self.temperature)
                elif tower.shield_branch == 2:
                    damage = (tower.level - 10) * 30 * abs(self.temperature)
                    for enemy in self.enemies:
                        enemy.take_damage(damage, color=(100, 150, 255))
                        enemy.freeze_resistance = 0
                        enemy.freeze_time = max(enemy.freeze_time, 3 * 60)
                elif tower.shield_branch == 3:
                    damage = int(self.coins * 0.01)
                    for enemy in self.enemies:
                        enemy.take_damage(damage, color=(255, 215, 0))
                    self.coins += (tower.level - 10) * 1000
                elif tower.shield_branch == 4:
                    damage = (tower.level - 10) * 25 * abs(self.temperature)
                    for enemy in self.enemies:
                        enemy.take_damage(damage, color=(255, 255, 0))
                        enemy.stun_resistance = 0
                        enemy.stun_time = max(enemy.stun_time, 60)
                        enemy.burn_time = float('inf')
                        enemy.burn_damage = max(enemy.burn_damage, self.temperature)

    def global_production(self):
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

    def spawn_damage_text(self, value, pos, color=RED, scale=1.4):
        text = DamageText(value, pos[0], pos[1], color=color, scale=scale)
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
                "gold": self.coins, "lives": self.lives, "wave": self.wave_manager.current_wave,
                "temperature": self.temperature, "weather": self.weather.value,
                "forecast_purchased": self.forecast_purchased,
                "weather_forecast": [w.value for w in self.weather_forecast],
                "gold_per_second": self.gold_per_second, "gold_per_wave": self.gold_per_wave,
                "gold_profit_per_wave": self.gold_profit_per_wave,
                "gold_ore_positions": [list(p) for p in self.gold_ore_positions],
                "towers": towers_data,
            }
            with open(get_save_path(), "w") as f:
                json.dump(data, f, indent=4)
        except Exception as e:
            print(f"Save failed: {e}")

    def _reset_state(self):
        self.enemies.empty()
        self.towers.empty()
        self.bullets.empty()
        self.damage_texts.empty()
        self.dragons.empty()
        self.coins = 2560
        self.lives = 20
        self.wave_manager = WaveManager()
        self.selected_tower_type = None
        self.selected_tower = None
        self.show_range = False
        self.enemies_killed = 0
        self.game_time = 0
        self.gold_per_second = 0
        self.gold_per_wave = 0
        self.gold_profit_per_wave = 0
        self.last_global_production_time = pygame.time.get_ticks()
        self.temperature = 30
        self.weather = Weather.SUNNY
        self.weather_particles = []
        self.weather_banner_timer = 0
        self.weather_banner_text = ""
        self.dragon_breath_pools = []
        self.lightning_effects = []
        self.wind_explosions = []
        self.ice_explosions = []
        self.poison_splashes = []
        self.wither_splashes = []
        self.horizontal_lightning_effects = []
        self.tnt_explosions = []
        self.mushroom_explosions = []
        self.shockwave_effects = []
        self.thunderstorm_timer = 0
        self.enemy_grid = {}
        self.fog_timer = 0
        self.fog_visible = False
        self.weather_forecast = []
        self.forecast_purchased = False
        self.forecast_weather_idx = -1
        self.pending_first_wave_weather = False
        self.gold_ore_positions = set()
        self.night_dark_timer = 0
        self.herobrine_phase = 0
        self.herobrine_spawned = False
        self.herobrine = None
        self.herobrine_summon_timer = 0
        self.herobrine_summon_queue = []
        self.command_block_timer = 0
        self.command_blocks = []
        self.ice_walls = []

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
            with open(new_path) as f:
                data = json.load(f)
        except Exception:
            return False
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
        self.lives = data.get("lives", 20)
        self.temperature = data.get("temperature", 30)
        self.weather = Weather(data.get("weather", Weather.SUNNY.value))
        self.forecast_purchased = data.get("forecast_purchased", False)
        self.gold_per_second = data.get("gold_per_second", 0)
        self.gold_per_wave = data.get("gold_per_wave", 0)
        self.gold_profit_per_wave = data.get("gold_profit_per_wave", 0.0)
        raw_forecast = data.get("weather_forecast", [])
        self.weather_forecast = [Weather(v) for v in raw_forecast]
        wave_num = max(1, data.get("wave", 1))
        self.wave_manager.current_wave = wave_num - 1
        for td in data.get("towers", []):
            ttype = TowerType(td["type"])
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
            if ttype == TowerType.TELEPORT:
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
                if t.shield_branch == 1:
                    self.temperature += t.level
                elif t.shield_branch == 2:
                    self.temperature -= t.level
        self.temperature = max(-273, self.temperature)
        self.wave_manager.start_new_wave()
        self.forecast_weather_idx = self.wave_manager.current_wave if self.forecast_purchased else -1
        self.state = GameState.PLAYING
        self.pending_first_wave_weather = False
        self.weather_banner_text = WEATHER_CONFIG[self.weather]["desc"]
        self.weather_banner_timer = 180
        if self.weather == Weather.ENDLESS_NIGHT:
            self._build_background(night_mode=True, gold_ore_positions=saved_ore)
            pygame.mixer.music.stop()
            for bgm in assets.bgm_files:
                if "Celestial Fury" in bgm or "The End" in bgm:
                    pygame.mixer.music.load(assets.resource_path(bgm))
                    pygame.mixer.music.play(-1)
                    break
        return True

    def add_dragon_breath(self, x, y, temperature, tower_level, stun_time):
        pool = DragonBreathPool(x, y, temperature, tower_level, stun_time, self)
        self.dragon_breath_pools.append(pool)

    def add_lightning(self, x, y, is_golden):
        effect = LightningEffect(x, y, is_golden)
        self.lightning_effects.append(effect)

    def apply_production_bonus(self):
        self.coins += 5 * self.gold_per_wave * self.wave_manager.current_wave
        self.coins += int(self.coins * self.gold_profit_per_wave)

    def update(self):
        if self.state == GameState.PAUSED:
            return
        if self.state == GameState.PLAYING:
            self.game_time += 1
            if self.pending_first_wave_weather and self.wave_manager.wave_timer <= 0:
                self.select_weather()
                if self.wave_manager.current_wave != 50:
                    self.weather_banner_timer = 180
                self.pending_first_wave_weather = False
            self.global_production()

            for enemy in self.enemies:
                reached_end = enemy.update()
                if reached_end:
                    if enemy.enemy_type == EnemyType.HEROBRINE:
                        self.lives -= 50
                    else:
                        self.lives -= 1
                    enemy.kill()
                    if self.lives <= 0:
                        self.state = GameState.GAME_OVER

            self._build_enemy_grid()

            self.apply_time_buffs()

            for tower in self.towers:
                if tower.type not in (TowerType.PRODUCTION, TowerType.TIME):
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

            if self.weather == Weather.FOG and not self.fog_visible:
                if self.fog_timer > 0:
                    self.fog_timer -= 1
                else:
                    self.fog_visible = True

            if self.weather == Weather.ENDLESS_NIGHT:
                self.night_dark_timer += 1
                if self.night_dark_timer >= 1800:
                    self.night_dark_timer = 0
                    self.fog_visible = True
                    for enemy in self.enemies:
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
                if self.command_block_timer >= initial_delay and (self.command_block_timer - initial_delay) % interval == 0:
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
                                for tower in list(self.towers):
                                    dx = abs(tower.x - cb['x'])
                                    dy = abs(tower.y - cb['y'])
                                    if dx <= 1 and dy <= 1:
                                        if getattr(tower, 'has_shield', False):
                                            tower.has_shield = False
                                            self.trigger_shield_burst(tower)
                                        else:
                                            tower.kill()
                                            self.towers.remove(tower)
                                for wall in list(self.ice_walls):
                                    dx = abs(wall.x - cb['x'])
                                    dy = abs(wall.y - cb['y'])
                                    if dx <= 1 and dy <= 1:
                                        self.destroy_ice_wall(wall)
                                explosion = TNTExplosion(cb['x'] * TILE_SIZE + TILE_SIZE // 2,
                                                         cb['y'] * TILE_SIZE + TILE_SIZE // 2,
                                                         0, 0, None, self)
                                self.tnt_explosions.append(explosion)

            if self.wave_manager.current_wave == 50:
                if not pygame.mixer.music.get_busy():
                    boss_bgm = None
                    for bgm in assets.bgm_files:
                        if "Celestial Fury" in bgm or "The End" in bgm:
                            boss_bgm = bgm
                            break
                    if boss_bgm:
                        pygame.mixer.music.load(assets.resource_path(boss_bgm))
                        pygame.mixer.music.play(-1)
            else:
                if not pygame.mixer.music.get_busy():
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

            for exp in self.ice_explosions[:]:
                if not exp.update():
                    self.ice_explosions.remove(exp)

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
                                reward = enemy.take_damage(50, color=GOLD)
                                self.coins += reward
                                enemy.apply_burn(self.temperature, 240)
                                enemy.on_lightning_hit()
                        self.add_lightning((col + 0.5) * TILE_SIZE, 800, False)

            for enemy in list(self.enemies):
                if enemy.health <= 0:
                    self.enemies_killed += 1
                    enemy.kill()

            if self.wave_manager.current_wave == 50 and self.wave_manager.wave_timer > 0:
                self.wave_manager.update()
            elif self.wave_manager.is_wave_complete(self.enemies):
                self.apply_production_bonus()
                if self.wave_manager.is_game_complete(self.enemies):
                    self.state = GameState.VICTORY
                else:
                    self.forecast_purchased = False
                    self.wave_manager.start_new_wave()
                    self.wave_manager.wave_timer = 0
                    self.select_weather()
                    self.weather_banner_timer = 180
            else:
                enemy_type = self.wave_manager.update()
                if enemy_type:
                    enemy = Enemy(self.path, enemy_type, self)
                    self.enemies.add(enemy)
                    if enemy_type == EnemyType.HEROBRINE:
                        self.herobrine_spawned = True
                        for _ in range(5):
                            self.herobrine_summon_queue.append(EnemyType.SLIME)
                        for _ in range(5):
                            self.herobrine_summon_queue.append(EnemyType.MAGMA_CUBE)


    def generate_weather_forecast(self):
        weathers = [Weather.ACID_RAIN, Weather.EXTREME_HEAT, Weather.SUNNY, Weather.CLOUDY, Weather.RAINY, Weather.SNOWY,
                    Weather.THUNDERSTORM, Weather.TAILWIND, Weather.HEADWIND,
                    Weather.SCORCHING_SUN, Weather.FOG, Weather.EXTREME_COLD, Weather.MAGNETIC_STORM,
                    Weather.FIRE_RAIN, Weather.AURORA]
        self.weather_forecast = [random.choice(weathers) for _ in range(self.wave_manager.total_waves)]

    def select_weather(self):
        self.fog_visible = False
        if self.wave_manager.current_wave == 50:
            self.weather = Weather.ENDLESS_NIGHT
            self._build_background(night_mode=True)
        else:
            wave_idx = self.wave_manager.current_wave - 1
            if 0 <= wave_idx < len(self.weather_forecast):
                self.weather = self.weather_forecast[wave_idx]
            else:
                self.weather = Weather.SUNNY
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
                if t.shield_branch == 1:
                    self.temperature += t.level
                elif t.shield_branch == 2:
                    self.temperature -= t.level
        self.temperature = max(-273, self.temperature)
        self.save_game()
        self.weather_banner_text = WEATHER_CONFIG[self.weather]["desc"]
        if self.weather == Weather.ENDLESS_NIGHT and not self.herobrine_spawned:
            pygame.mixer.music.stop()
            boss_bgm = None
            for bgm in assets.bgm_files:
                if "Celestial Fury" in bgm or "The End" in bgm:
                    boss_bgm = bgm
                    break
            if boss_bgm:
                pygame.mixer.music.load(assets.resource_path(boss_bgm))
                pygame.mixer.music.play(-1)
        if self.weather == Weather.ACID_RAIN:
            destroyed = []
            for t in self.towers:
                if t.level >= 1:
                    if getattr(t, 'has_shield', False):
                        t.has_shield = False
                        self.trigger_shield_burst(t)
                        continue
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
                        elif t.type == TowerType.TIME:
                            pass
                        if t.type == TowerType.PRODUCTION:
                            multiplier = 2 if t.is_on_gold_ore else 1
                            if old_level >= 6: self.gold_per_wave -= multiplier
                            if old_level >= 11: self.gold_profit_per_wave -= 0.001 * multiplier
                        t.update_sprite()
                    else:
                        if t.type in (TowerType.FLAME, TowerType.TRIDENT, TowerType.BOMB):
                            self.temperature -= 1
                        elif t.type == TowerType.ICE:
                            self.temperature += 1
                        self.temperature = max(-273, self.temperature)
                        destroyed.append(t)
            for t in destroyed:
                if self.selected_tower is t:
                    self.selected_tower = None
                t.kill()
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
        pygame.mixer.music.load(assets.resource_path(assets.bgm_files[idx]))
        pygame.mixer.music.play()

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
        elif self.state == GameState.GAME_OVER:
            self.ui_manager.draw_game_over()
        elif self.state == GameState.VICTORY:
            self.ui_manager.draw_victory()
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
                self.temperature = max(-273, self.temperature)
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
        self.generate_weather_forecast()
        self.state = GameState.PLAYING
        self.wave_manager.start_new_wave()
        self.pending_first_wave_weather = True
        self.weather_banner_text = "准备时间"
        self.weather_banner_timer = 240

    def reset_game(self):
        try:
            os.remove(get_save_path())
        except Exception:
            pass
        self.path = random.choice(SEED_PATHS)
        self.start_point = self.path[0]
        self.end_point = self.path[-1]
        self._build_background()
        self.enemies.empty()
        self.towers.empty()
        self.bullets.empty()
        self.damage_texts.empty()

        self.coins = 2560
        self.lives = 20
        self.wave_manager = WaveManager()
        self.selected_tower_type = None
        self.selected_tower = None
        self.show_range = False
        self.enemies_killed = 0
        self.game_time = 0
        self.gold_per_second = 0
        self.gold_per_wave = 0
        self.gold_profit_per_wave = 0
        self.last_global_production_time = pygame.time.get_ticks()
        self.temperature = 30
        self.weather = Weather.SUNNY
        self.weather_particles = []
        self.weather_banner_timer = 0
        self.weather_banner_text = ""
        self.dragon_breath_pools = []
        self.lightning_effects = []
        self.wind_explosions = []
        self.ice_explosions = []
        self.poison_splashes = []
        self.wither_splashes = []
        self.horizontal_lightning_effects = []
        self.tnt_explosions = []
        self.mushroom_explosions = []
        self.shockwave_effects = []
        self.thunderstorm_timer = 0
        self.enemy_grid = {}
        self.fog_timer = 0
        self.fog_visible = False
        self.weather_forecast = []
        self.forecast_purchased = False
        self.forecast_weather_idx = -1
        self.pending_first_wave_weather = False
        self.start_game()

    def run(self):
        while True:
            self.handle_events()
            self.update()
            self.draw()
            self.clock.tick(self.fps)