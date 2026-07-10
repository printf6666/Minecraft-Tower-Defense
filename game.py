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
from ui import UIManager
from dragons import Dragon


def resource_path(relative_path):
    base_path = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_path, relative_path)


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

TOWER_DATA = [
    (TowerType.PHYSICAL,   "物理", 100,  pygame.K_1),
    (TowerType.PRODUCTION, "生产", 50,   pygame.K_2),
    (TowerType.ICE,        "冰系", 150,  pygame.K_3),
    (TowerType.TELEPORT,   "传送", 300,  pygame.K_4),
    (TowerType.FLAME,      "火系", 200,  pygame.K_5),
    (TowerType.TRIDENT,    "三叉", 400,  pygame.K_6),
    (TowerType.WIND,       "风系", 250,  pygame.K_7),
    (TowerType.POISON,     "毒系", 175,  pygame.K_8),
    (TowerType.BOMB,       "TNT", 500,  pygame.K_9),
    ]


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
        self.coins = 2500000
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
        self.mushroom_explosions = []
        self.shockwave_effects = []
        self.thunderstorm_timer = 0

        self.fog_timer = 0
        self.fog_visible = False
        self.weather_forecast = []
        self.forecast_purchased = False
        self.forecast_weather_idx = -1

        self.path = random.choice(SEED_PATHS)
        self.start_point = self.path[0]
        self.end_point = self.path[-1]
        self.background_surface = None
        self.enemy_grid = {}
        self._build_background()

        self.ui_manager = UIManager(self)

    def _build_background(self):
        gw = GRID_WIDTH * TILE_SIZE
        gh = (GRID_HEIGHT + 1) * TILE_SIZE
        self.background_surface = pygame.Surface((gw, gh))
        self.background_surface.fill(BLACK)
        path_set = set(self.path)

        stone_tiles = []
        for x in range(GRID_WIDTH):
            for y in range(1, GRID_HEIGHT + 1):
                if (x, y) not in path_set and (x, y) != self.end_point:
                    stone_tiles.append((x, y))

        self.gold_ore_positions = set(random.sample(stone_tiles, min(5, len(stone_tiles))))

        for x in range(GRID_WIDTH):
            for y in range(1, GRID_HEIGHT + 1):
                if (x, y) in path_set:
                    self.background_surface.blit(assets.dirt_img, (x * TILE_SIZE, y * TILE_SIZE))
                elif (x, y) in self.gold_ore_positions:
                    self.background_surface.blit(assets.gold_ore_img, (x * TILE_SIZE, y * TILE_SIZE))
                else:
                    self.background_surface.blit(assets.stone_img, (x * TILE_SIZE, y * TILE_SIZE))
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
                        if 900 <= mouse_x <= 1660 and 900 <= mouse_y <= 980:
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
                        if self.state == GameState.PLAYING and not self.forecast_purchased and self.coins >= 100 * self.wave_manager.current_wave:
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
                            self.selected_tower.upgrade()
                            if assets.level_up_sound and self.selected_tower.level in (6, 11):
                                assets.level_up_sound.play()
                            if self.selected_tower.type in (TowerType.FLAME, TowerType.TRIDENT, TowerType.BOMB):
                                self.temperature += 1
                    elif event.key == pygame.K_r and self.selected_tower and self.selected_tower.type == TowerType.BOMB:
                        if self.selected_tower.level >= 11:
                            self.selected_tower.bomb_branch = 3 - self.selected_tower.bomb_branch
                            self.selected_tower.update_sprite()
                        elif 6 <= self.selected_tower.level < 11:
                            sub_types = [BombSubType.SNOW, BombSubType.ICE, BombSubType.FLAME, BombSubType.POISON, BombSubType.WITHER_TNT]
                            idx = sub_types.index(self.selected_tower.bomb_subtype)
                            self.selected_tower.bomb_subtype = sub_types[(idx + 1) % 5]
                            self.selected_tower.update_sprite()
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
                        self.selected_tower.ice_branch = 3 - self.selected_tower.ice_branch
                        self.selected_tower.update_sprite()
                    elif event.key == pygame.K_r and self.selected_tower and self.selected_tower.type == TowerType.FLAME and self.selected_tower.level >= 11:
                        self.selected_tower.flame_branch = 3 - self.selected_tower.flame_branch
                        self.selected_tower.update_sprite()
                    elif event.key == pygame.K_r and self.selected_tower and self.selected_tower.type == TowerType.TRIDENT and self.selected_tower.level >= 11:
                        self.selected_tower.trident_branch = 3 - self.selected_tower.trident_branch
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
                        if self.selected_tower.type in (TowerType.FLAME, TowerType.TRIDENT, TowerType.BOMB):
                            self.temperature -= self.selected_tower.level
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

    def global_production(self):
        current_time = pygame.time.get_ticks()
        if current_time - self.last_global_production_time >= 1000:
            self.coins += self.gold_per_second
            self.last_global_production_time = current_time

    def spawn_damage_text(self, value, pos, color=RED, scale=1.4):
        text = DamageText(value, pos[0], pos[1], color=color, scale=scale)
        self.damage_texts.add(text)

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
                self.weather_banner_timer = 180
                self.pending_first_wave_weather = False
            self.global_production()

            for enemy in self.enemies:
                reached_end = enemy.update()
                if reached_end:
                    self.lives -= 1
                    enemy.kill()
                    if self.lives <= 0:
                        self.state = GameState.GAME_OVER

            self._build_enemy_grid()

            for tower in self.towers:
                if tower.type != TowerType.PRODUCTION:
                    bullets = tower.attack(self.game_time)
                    for bullet in bullets:
                        self.bullets.add(bullet)

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
                        self.add_lightning((col + 0.5) * TILE_SIZE, 800, False)

            for enemy in list(self.enemies):
                if enemy.health <= 0:
                    self.enemies_killed += 1
                    enemy.kill()

            if self.wave_manager.is_wave_complete(self.enemies):
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


    def generate_weather_forecast(self):
        weathers = [Weather.EXTREME_HEAT, Weather.SUNNY, Weather.CLOUDY, Weather.RAINY, Weather.SNOWY,
                    Weather.THUNDERSTORM, Weather.ACID_RAIN, Weather.TAILWIND, Weather.HEADWIND,
                    Weather.SCORCHING_SUN, Weather.FOG, Weather.EXTREME_COLD, Weather.MAGNETIC_STORM,
                    Weather.FIRE_RAIN]
        self.weather_forecast = [random.choice(weathers) for _ in range(self.wave_manager.total_waves)]

    def select_weather(self):
        self.fog_visible = False
        wave_idx = self.wave_manager.current_wave - 1
        if 0 <= wave_idx < len(self.weather_forecast):
            self.weather = self.weather_forecast[wave_idx]
        else:
            self.weather = Weather.SUNNY
        base_temp = WEATHER_CONFIG[self.weather]["temp"]
        self.temperature = base_temp
        for t in self.towers:
            if t.type in (TowerType.FLAME, TowerType.TRIDENT, TowerType.BOMB):
                self.temperature += t.level
        self.weather_banner_text = WEATHER_CONFIG[self.weather]["desc"]
        if self.weather == Weather.ACID_RAIN:
            destroyed = []
            for t in self.towers:
                if t.level >= 1:
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
                        elif t.type == TowerType.TELEPORT:
                            t.damage -= 5
                            t.teleport_chance = max(0, t.teleport_chance - 0.01)
                            t.range -= TILE_SIZE // 4
                            t.fire_rate = min(60, t.fire_rate + 6)
                            if old_level >= 6:
                                t.oneshot_chance = max(0, t.oneshot_chance - 0.01)
                            if old_level >= 11:
                                t.execute_threshold = 0
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
                            if old_level >= 6: self.gold_per_wave -= multiplier
                            if old_level >= 11: self.gold_profit_per_wave -= 0.001 * multiplier
                        t.update_sprite()
                    else:
                        if t.type in (TowerType.FLAME, TowerType.TRIDENT, TowerType.BOMB):
                            self.temperature -= 1
                        destroyed.append(t)
            for t in destroyed:
                if self.selected_tower is t:
                    self.selected_tower = None
                t.kill()
            for enemy in self.enemies:
                enemy.apply_poison(10)
        if self.weather == Weather.SCORCHING_SUN:
            for enemy in self.enemies:
                enemy.burn_damage = max(enemy.burn_damage, self.temperature)
                enemy.burn_time = max(enemy.burn_time, 999999)
        if self.weather == Weather.FIRE_RAIN:
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

    def get_tower_info(self, tower):
        base_cost_map = {ttype: cost for ttype, name, cost, key in TOWER_DATA}
        info = []
        if tower.type == TowerType.PHYSICAL:
            if tower.level >= 11:
                if tower.physical_branch == 2:
                    info = [f"天堂陨落箭塔 Lv{tower.level}", f"伤害:{tower.damage}", f"攻击间隔:0.5s", f"将当前金币的1%作为伤害加成", f"12方向散射", "按 R 切换分支"]
                else:
                    info = [f"时空撕裂箭塔 Lv{tower.level}", f"伤害:{tower.damage}", f"攻击间隔:0.5s",
                            f"将当前金币的1%作为伤害加成", f"破甲:受伤永久增加20%", "按 R 切换分支"]
            elif tower.level >= 6:
                info = [f"黄金箭塔 Lv{tower.level}", f"伤害:{tower.damage}", f"攻击间隔:0.5s", f"将当前金币的1%作为伤害加成"]
            else:
                info = [f"箭塔 Lv{tower.level}", f"伤害:{tower.damage}", f"攻击间隔:{tower.fire_rate / 60}s"]
        elif tower.type == TowerType.PRODUCTION:
            if tower.level >= 11:
                info = [f"无尽矿 Lv{tower.level}", f"全局产量:{self.gold_per_second}/s",
                        f"全局每波产出:{5 * self.gold_per_wave}*当前波数", f"全局每波利息:{round(100 * self.gold_profit_per_wave, 1)}%", "放置在金矿石上时产出+100%"]
            elif tower.level >= 6:
                info = [f"下界合金矿 Lv{tower.level}", f"全局每波产出:{5 * self.gold_per_wave}*当前波数",
                        f"全局产量:{self.gold_per_second}/s", "放置在金矿石上时产出+100%"]
            else:
                info = [f"金矿 Lv{tower.level}", f"全局产量:{self.gold_per_second}/s", "放置在金矿石上时产出+100%"]
        elif tower.type == TowerType.ICE:
            if tower.level >= 11:
                if tower.ice_branch == 2:
                    ice_dmg = {11: 30, 12: 60, 13: 90, 14: 120, 15: 150}
                    info = [f"冰龙塔 Lv{tower.level}", f"减速:50%", f"伤害:{tower.damage}", f"冻结:{tower.freeze_time}s",
                            f"2%召唤冰龙:{ice_dmg.get(tower.level,30)}倍温度+冰冻3s", f"攻击间隔:0.5s", "按R切换形态"]
                else:
                    bonus_pct = 300 * (tower.level - 10)
                    info = [f"冰霜炸弹塔 Lv{tower.level}", f"减速:50%", f"伤害:{tower.damage}", f"冻结:{tower.freeze_time}s",
                            f"对冻结+{bonus_pct}%温度伤害", f"攻击间隔:0.5s", "按R切换形态"]
            elif tower.level >= 6:
                info = [f"冰球塔 Lv{tower.level}", f"减速:50%", f"伤害:{tower.damage}", f"冻结:{tower.freeze_time}s",
                        f"攻击间隔:0.5s"]
            else:
                info = [f"雪球塔 Lv{tower.level}", f"减速:50%", f"伤害:{tower.damage}", f"攻击间隔:{tower.fire_rate / 60}s"]
        elif tower.type == TowerType.TELEPORT:
            if tower.level >= 11:
                info = [f"终望珍珠塔 Lv{tower.level}", f"秒杀概率:{int(tower.oneshot_chance * 100)}%",
                        f"瞬移概率:{int(tower.teleport_chance * 100)}%", f"斩杀线:{tower.execute_threshold}%",
                        f"范围伤害:{tower.damage}", f"攻击间隔:0.5s"]
            elif tower.level >= 6:
                info = [f"末影之眼塔 Lv{tower.level}", f"秒杀概率:{int(tower.oneshot_chance * 100)}%",
                        f"瞬移概率:{int(tower.teleport_chance * 100)}%", f"伤害:{tower.damage}", f"攻击间隔:0.5s"]
            else:
                info = [f"末影珍珠塔 Lv{tower.level}", f"瞬移概率:{int(tower.teleport_chance * 100)}%",
                        f"伤害:{tower.damage}", f"攻击间隔:{tower.fire_rate / 60}s"]
        elif tower.type == TowerType.FLAME:
            if tower.level >= 11:
                if tower.flame_branch == 2:
                    fire_dmg = {11: 36, 12: 72, 13: 108, 14: 144, 15: 180}
                    info = [f"火龙塔 Lv{tower.level}", f"伤害:{tower.damage}", f"燃烧:{self.temperature}/s,持续4s",
                            f"5%召唤火龙:{fire_dmg.get(tower.level,36)}倍温度+燃烧", f"击晕:{tower.stun_time}s", f"攻击间隔:0.5s", "按R切换形态"]
                else:
                    dmg_mult = (tower.level - 10) * 10
                    info = [f"龙息塔 Lv{tower.level}", f"伤害:{tower.damage}", f"燃烧:{self.temperature}/s,持续4s",
                            f"龙息:{dmg_mult}倍温度/s", f"击晕:{tower.stun_time}s", f"攻击间隔:0.5s", "按R切换形态"]
            elif tower.level >= 6:
                info = [f"火球塔 Lv{tower.level}", f"伤害:{tower.damage}", f"燃烧:{self.temperature}/s,持续4s",
                        f"击晕:{tower.stun_time}s", f"攻击间隔:0.5s"]
            else:
                info = [f"火焰塔 Lv{tower.level}", f"伤害:{tower.damage}", f"燃烧:{self.temperature}/s,持续4s",
                        f"攻击间隔:{tower.fire_rate / 60}s"]
        elif tower.type == TowerType.TRIDENT:
            if tower.level >= 11:
                if tower.trident_branch == 2:
                    info = [f"电龙塔 Lv{tower.level}", f"伤害:{tower.damage}", f"闪电:{tower.lightning_damage}",
                            f"将当前金币的1%作为伤害加成", f"5%召唤电龙:{(tower.level-10)*50}倍温度+麻痹1s", f"攻击间隔:0.5s", "按 R 切换形态"]
                else:
                    info = [f"海神三叉戟 Lv{tower.level}", f"伤害:{tower.damage}", f"闪电:{tower.lightning_damage}",
                            f"将当前金币的1%作为伤害加成", f"攻击施放十字闪电", f"攻击间隔:0.5s", "按 R 切换形态"]
            elif tower.level >= 6:
                info = [f"黄金三叉戟 Lv{tower.level}", f"伤害:{tower.damage}", f"闪电:{tower.lightning_damage}",
                        f"将当前金币的1%作为伤害加成", f"攻击间隔:0.5s"]
            else:
                info = [f"三叉戟塔 Lv{tower.level}", f"伤害:{tower.damage}", f"闪电:{tower.lightning_damage}",
                        f"攻击间隔:{tower.fire_rate / 60}s"]
        elif tower.type == TowerType.WIND:
            if tower.level >= 11:
                if tower.wind_branch == 2:
                    dmg_map = {11: 2000, 12: 4000, 13: 6000, 14: 8000, 15: 10000}
                    info = [f"雷神之锤塔 Lv{tower.level}", f"伤害:{tower.damage}",
                            f"子弹命中释放竖向闪电:{dmg_map.get(tower.level,2500)}", "按 R 切换分支", f"攻击间隔:0.5s"]
                else:
                    per_px = {11: 8, 12: 10, 13: 12, 14: 14, 15: 16}
                    stun_s = {11: 0.1, 12: 0.2, 13: 0.3, 14: 0.4, 15: 0.5}
                    info = [f"重锤塔 Lv{tower.level}", f"伤害:{tower.damage}+{per_px.get(tower.level,8)}/px",
                            f"击退:{tower.wind_knockback}px", f"击晕:{stun_s.get(tower.level,0.1)}s", "按 R 切换分支", f"攻击间隔:0.5s"]
            elif tower.level >= 6:
                info = [f"蓄风箭塔 Lv{tower.level}", f"伤害:{tower.damage}", f"击退:{tower.wind_knockback}px",
                        f"蓄风印记", f"攻击间隔:0.5s"]
            else:
                info = [f"风弹塔 Lv{tower.level}", f"伤害:{tower.damage}", f"击退:{tower.wind_knockback}px",
                        f"攻击间隔:{tower.fire_rate / 60}s"]
        elif tower.type == TowerType.POISON:
            if tower.poison_branch == 3:
                stacks = tower.level * 9
                info = [f"九头蛇毒箭塔 Lv{tower.level}", f"单体伤害:{tower.damage}",
                        f"中毒层数:{stacks}层/次", "按 R 切换分支", f"攻击间隔:0.5s"]
            elif tower.poison_branch == 2:
                if tower.level >= 11:
                    info = [f"凋零之首 Lv{tower.level}", f"范围伤害:{tower.damage}",
                            f"凋零:12s", "按 R 切换分支", f"攻击间隔:0.5s"]
                elif tower.level >= 6:
                    info = [f"凋零瓶 Lv{tower.level}", f"范围伤害:{tower.damage}",
                            f"范围凋零:5s", "按 R 切换分支", f"攻击间隔:0.5s"]
                else:
                    info = [f"凋零箭 Lv{tower.level}", f"伤害:{tower.damage}",
                            f"凋零:5s", "按 R 切换分支", f"攻击间隔:{tower.fire_rate / 60}s"]
            elif tower.level >= 11:
                stacks = tower.level * 4
                info = [f"剧毒环刃塔 Lv{tower.level}", f"范围伤害:{tower.damage}",
                        f"中毒层数:{stacks}层/次", "按 R 切换分支", f"攻击间隔:0.5s"]
            elif tower.level >= 6:
                info = [f"毒瓶塔 Lv{tower.level}", f"范围伤害:{tower.damage}",
                        f"中毒层数:{tower.level}层/次", "按 R 切换分支", f"攻击间隔:0.5s"]
            else:
                info = [f"毒箭塔 Lv{tower.level}", f"伤害:{tower.damage}",
                        f"中毒层数:{tower.level}层/次", "按 R 切换分支", f"攻击间隔:{tower.fire_rate / 60}s"]
        elif tower.type == TowerType.BOMB:
            if tower.level >= 11:
                if tower.bomb_branch == 2:
                    percent = [4, 5, 6, 7, 8][tower.level - 11]
                    fixed = [2000, 4000, 6000, 8000, 10000][tower.level - 11]
                    info = [f"凋零核弹塔 Lv{tower.level}",
                            f"伤害:{percent}%最大生命+{fixed}固定",
                            f"击晕:2s", f"凋零:10s",
                            f"射程:全屏", f"攻击间隔:20s", "按 R 切换形态"]
                else:
                    dmg = (20000 + 100 * self.temperature) * (tower.level - 10)
                    info = [f"核弹塔 Lv{tower.level}", f"伤害:{dmg}(受温度影响)",
                            f"击晕:2s", f"中毒:{tower.level * 10}层",
                            f"射程:全屏", f"攻击间隔:20s", "按 R 切换形态"]
            elif tower.level >= 6:
                sub_names = {BombSubType.SNOW: "雪TNT", BombSubType.ICE: "冰TNT",
                             BombSubType.FLAME: "火焰TNT", BombSubType.POISON: "毒TNT",
                             BombSubType.WITHER_TNT: "凋零TNT"}
                sub_name = sub_names.get(tower.bomb_subtype, "雪TNT")
                if tower.bomb_subtype == BombSubType.SNOW:
                    extra = "范围减速50%,持续12s"
                elif tower.bomb_subtype == BombSubType.ICE:
                    freeze_s = {6: 0.6, 7: 0.7, 8: 0.8, 9: 0.9, 10: 1.0}
                    extra = f"范围冰冻{freeze_s.get(tower.level, 0.6)}s"
                elif tower.bomb_subtype == BombSubType.FLAME:
                    extra = "范围燃烧8s"
                elif tower.bomb_subtype == BombSubType.POISON:
                    stacks = {6: 12, 7: 14, 8: 16, 9: 18, 10: 20}
                    extra = f"范围中毒{stacks.get(tower.level, 12)}层"
                elif tower.bomb_subtype == BombSubType.WITHER_TNT:
                    extra = "范围凋零5s"
                info = [f"{sub_name} Lv{tower.level}", f"伤害:{tower.damage}",
                        extra, "按 R 切换分支", "攻击间隔:2s"]
            else:
                info = [f"TNT塔 Lv{tower.level}", f"伤害:{tower.damage}", f"攻击间隔:2s"]
        upgrade_str = "MAX" if tower.level >= 15 else str(tower.upgrade_cost)
        if tower.type == TowerType.BOMB and tower.is_nuclear:
            info.extend([f"升级:{upgrade_str}"])
        else:
            info.extend([f"射程:{round(tower.get_effective_range() / TILE_SIZE, 1)}", f"升级:{upgrade_str}"])
        sell_price = base_cost_map[tower.type] * tower.level
        info.append(f"出售:{sell_price}")

        return info

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
            if tower_type in (TowerType.FLAME, TowerType.TRIDENT, TowerType.BOMB):
                self.temperature += 1

    def start_game(self):
        self.generate_weather_forecast()
        self.state = GameState.PLAYING
        self.wave_manager.start_new_wave()
        self.pending_first_wave_weather = True
        self.weather_banner_text = "准备时间"
        self.weather_banner_timer = 240

    def reset_game(self):
        self.path = random.choice(SEED_PATHS)
        self.start_point = self.path[0]
        self.end_point = self.path[-1]
        self._build_background()
        self.enemies.empty()
        self.towers.empty()
        self.bullets.empty()
        self.damage_texts.empty()

        self.coins = 2500
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