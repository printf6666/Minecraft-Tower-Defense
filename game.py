import pygame
import random
import json
import sys
import os
import assets
from config import *
from enemy import Enemy, DamageText
from tower import Tower, Bullet, DragonBreathPool, LightningEffect, WindExplosion, IceExplosion, HorizontalLightningEffect, PoisonSplash
from wave_manager import WaveManager


def resource_path(relative_path):
    base_path = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_path, relative_path)


with open(resource_path("seed.json")) as f:
    SEED_PATHS = [[tuple(cell) for cell in path] for path in json.load(f)["seed_paths"]]


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

        self.dragon_breath_pools = []
        self.lightning_effects = []
        self.wind_explosions = []
        self.ice_explosions = []
        self.poison_splashes = []
        self.horizontal_lightning_effects = []
        self.thunderstorm_timer = 0

        self.fog_timer = 0
        self.fog_visible = False
        self.weather_forecast = []
        self.forecast_purchased = False
        self.forecast_weather_idx = -1

        self.path = random.choice(SEED_PATHS)
        self.start_point = self.path[0]
        self.end_point = self.path[-1]

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
                if event.key == pygame.K_1:
                    self.selected_tower_type = TowerType.PHYSICAL
                elif event.key == pygame.K_2:
                    self.selected_tower_type = TowerType.PRODUCTION
                elif event.key == pygame.K_3:
                    self.selected_tower_type = TowerType.ICE
                elif event.key == pygame.K_4:
                    self.selected_tower_type = TowerType.TELEPORT
                elif event.key == pygame.K_5:
                    self.selected_tower_type = TowerType.FLAME
                elif event.key == pygame.K_6:
                    self.selected_tower_type = TowerType.TRIDENT
                elif event.key == pygame.K_7:
                    self.selected_tower_type = TowerType.WIND
                elif event.key == pygame.K_8:
                    self.selected_tower_type = TowerType.POISON
                elif event.key == pygame.K_u and self.selected_tower:
                    if self.selected_tower.level < 15 and self.coins >= self.selected_tower.upgrade_cost:
                        self.coins -= self.selected_tower.upgrade_cost
                        self.selected_tower.upgrade()
                        if self.selected_tower.type in (TowerType.FLAME, TowerType.TRIDENT):
                            self.temperature += 1

                elif event.key == pygame.K_s and self.selected_tower:
                    base_cost_map = {
                        TowerType.PHYSICAL: 100,
                        TowerType.PRODUCTION: 50,
                        TowerType.ICE: 150,
                        TowerType.TELEPORT: 300,
                        TowerType.FLAME: 200,
                        TowerType.TRIDENT: 400,
                        TowerType.WIND: 250,
                        TowerType.POISON: 175
                    }
                    sell_price = base_cost_map[self.selected_tower.type] * self.selected_tower.level
                    self.coins += sell_price

                    if self.selected_tower.type == TowerType.PRODUCTION:
                        level = self.selected_tower.level
                        self.gold_per_second -= level
                        if level >= 6:
                            self.gold_per_wave -= (level - 5)
                        if level >= 11:
                            self.gold_profit_per_wave -= (level - 10) * 0.01

                    if self.selected_tower.type in (TowerType.FLAME, TowerType.TRIDENT):
                        self.temperature -= self.selected_tower.level

                    self.selected_tower.kill()
                    self.selected_tower = None
                elif event.key == pygame.K_ESCAPE:
                    self.selected_tower = None
                    self.selected_tower_type = None
                    self.show_range = False
                elif event.key == pygame.K_F11:
                    pygame.display.toggle_fullscreen()
                elif event.key == pygame.K_p:
                    if self.state in (GameState.PLAYING, GameState.WAVE_PREPARATION):
                        self.pre_pause_state = self.state
                        self.state = GameState.PAUSED
                    elif self.state == GameState.PAUSED:
                        self.state = self.pre_pause_state
                        self.pre_pause_state = None

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
        self.coins += 10 * self.gold_per_wave * self.wave_manager.current_wave
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

            for tower in self.towers:
                if tower.type != TowerType.PRODUCTION:
                    bullets = tower.attack(self.game_time)
                    for bullet in bullets:
                        self.bullets.add(bullet)

            self.bullets.update()
            self.damage_texts.update()

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

            for effect in self.horizontal_lightning_effects[:]:
                effect.update()
                if effect.done:
                    self.horizontal_lightning_effects.remove(effect)

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
            if t.type in (TowerType.FLAME, TowerType.TRIDENT):
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
                        self.gold_per_second -= 1
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
                        if t.type == TowerType.PRODUCTION:
                            if old_level >= 6: self.gold_per_wave -= 1
                            if old_level >= 11: self.gold_profit_per_wave -= 0.01
                        t.update_sprite()
                    else:
                        if t.type in (TowerType.FLAME, TowerType.TRIDENT):
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
                if enemy.enemy_type in (EnemyType.ARMORED, EnemyType.GOLD_ARMORED):
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

        for p in self.weather_particles[:]:
            if p[-1] in ("rain", "acid_rain"):
                p[1] += p[2]
                if p[1] > SCREEN_HEIGHT:
                    self.weather_particles.remove(p)
            elif p[-1] == "snow":
                p[1] += p[2]
                p[0] += p[3]
                if p[1] > SCREEN_HEIGHT or p[0] < 0 or p[0] > SCREEN_WIDTH:
                    self.weather_particles.remove(p)

    def draw(self):
        self.screen.fill(BLACK)
        if self.state == GameState.MENU:
            self.draw_menu()
        elif self.state in (GameState.PLAYING, GameState.WAVE_PREPARATION, GameState.PAUSED):
            self.draw_game()
        elif self.state == GameState.GAME_OVER:
            self.draw_game_over()
        elif self.state == GameState.VICTORY:
            self.draw_victory()
        pygame.display.flip()

    def draw_menu(self):
        title = assets.font_large.render("像素防线:晶域守卫", True, WHITE)
        self.screen.blit(title, (SCREEN_WIDTH // 2 - title.get_width() // 2, 300))
        pygame.draw.rect(self.screen, GREEN, (900, 900, 760, 80))
        start_text = assets.font_medium.render("开始游戏", True, WHITE)
        self.screen.blit(start_text, (1200, 915))
        pygame.draw.rect(self.screen, RED, (900, 1020, 760, 80))
        exit_text = assets.font_medium.render("退出游戏", True, WHITE)
        self.screen.blit(exit_text, (1200, 1035))
        instructions = ["游戏说明:", "1. 鼠标点击建造炮塔", "2. 1/2/3/4/5/6/7/8键选择炮塔", "3. U升级 S出售 P暂停"]
        for i, text in enumerate(instructions):
            text_surface = assets.font_small.render(text, True, WHITE)
            self.screen.blit(text_surface, (900, 1200 + i * 50))

    def draw_game(self):
        path_set = set(self.path)
        for x in range(GRID_WIDTH):
            for y in range(1, GRID_HEIGHT + 1):
                if (x, y) in path_set:
                    self.screen.blit(assets.dirt_img, (x * TILE_SIZE, y * TILE_SIZE))
                else:
                    self.screen.blit(assets.stone_img, (x * TILE_SIZE, y * TILE_SIZE))
        sx, sy = self.start_point
        ex, ey = self.end_point
        self.screen.blit(assets.start_img, (sx * TILE_SIZE, sy * TILE_SIZE))
        self.screen.blit(assets.house_img, (ex * TILE_SIZE, ey * TILE_SIZE))

        self.towers.draw(self.screen)
        self.enemies.draw(self.screen)
        self.bullets.draw(self.screen)
        self.damage_texts.draw(self.screen)
        for tower in self.towers:
            self.screen.blit(assets.font_tower_level.render(f"Lv{tower.level}", True, YELLOW),
                             (tower.x * TILE_SIZE + 70, tower.y * TILE_SIZE + 90))
        for enemy in self.enemies:
            enemy.draw_health_bar(self.screen)

        if self.show_range and self.selected_tower:
            self.selected_tower.draw_range(self.screen)

        self.draw_weather_particles()
        self.draw_weather_banner()

        if self.fog_visible:
            gw = GRID_WIDTH * TILE_SIZE
            gh = GRID_HEIGHT * TILE_SIZE
            s = pygame.Surface((gw, gh), pygame.SRCALPHA)
            s.fill((230, 230, 230, 255))
            self.screen.blit(s, (0, TILE_SIZE))

        for pool in self.dragon_breath_pools:
            pool.draw(self.screen)
        for effect in self.lightning_effects:
            effect.draw(self.screen)
        for explosion in self.wind_explosions:
            explosion.draw(self.screen)
        for exp in self.ice_explosions:
            exp.draw(self.screen)
        for splash in self.poison_splashes:
            splash.draw(self.screen)
        for effect in self.horizontal_lightning_effects:
            effect.draw(self.screen)

        self.draw_ui()
        if self.state == GameState.PAUSED:
            self.draw_pause_overlay()

    def draw_ui(self):
        pygame.draw.rect(self.screen, BLACK, (0, 0, SCREEN_WIDTH, 80))
        pygame.draw.line(self.screen, WHITE, (0, 80), (SCREEN_WIDTH, 80), 4)
        self.screen.blit(assets.gold_img, (30, 8))
        self.screen.blit(assets.font_medium.render(str(self.coins), True, GOLD), (85, 16))
        self.screen.blit(assets.heart_img, (360, 16))
        self.screen.blit(assets.font_medium.render(str(self.lives), True, RED), (415, 16))
        self.screen.blit(assets.clock_img, (720, 16))
        self.screen.blit(
            assets.font_medium.render(f"{self.wave_manager.current_wave}/{self.wave_manager.total_waves}", True, WHITE),
            (775, 16))
        weather_name = WEATHER_CONFIG[self.weather]["name"]
        weather_color = WEATHER_CONFIG[self.weather]["color"]
        self.screen.blit(assets.font_medium.render(f"天气:{weather_name}  温度:{self.temperature}", True, weather_color), (1520, 16))

        can_buy = self.state == GameState.PLAYING and not self.forecast_purchased
        can_afford = self.coins >= 100 * self.wave_manager.current_wave
        btn_color = FORECAST_BTN_COLOR if can_buy and can_afford else FORECAST_BTN_COLOR_DISABLED
        pygame.draw.rect(self.screen, btn_color,
                         (FORECAST_BTN_X, FORECAST_BTN_Y, FORECAST_BTN_WIDTH, FORECAST_BTN_HEIGHT))
        if self.forecast_purchased and 0 <= self.forecast_weather_idx < len(self.weather_forecast):
            w = self.weather_forecast[self.forecast_weather_idx]
            label = f"天气预报:{WEATHER_CONFIG[w]['name']}"
        else:
            label = f"天气预报:花费{100*self.wave_manager.current_wave}金"
        fc_color = WHITE if can_afford else GRAY
        fc_text = assets.font_small.render(label, True, fc_color)
        self.screen.blit(fc_text, (FORECAST_BTN_X + 20, FORECAST_BTN_Y + 10))

        pygame.draw.rect(self.screen, BLACK, (0, SCREEN_HEIGHT - 120, SCREEN_WIDTH, 120))
        pygame.draw.line(self.screen, WHITE, (0, SCREEN_HEIGHT - 120), (SCREEN_WIDTH, SCREEN_HEIGHT - 120), 4)
        self.screen.blit(assets.icon1, (40, SCREEN_HEIGHT - 100))
        self.screen.blit(assets.icon2, (360, SCREEN_HEIGHT - 100))
        self.screen.blit(assets.icon3, (680, SCREEN_HEIGHT - 100))
        self.screen.blit(assets.icon4, (1000, SCREEN_HEIGHT - 100))
        self.screen.blit(assets.icon5, (1320, SCREEN_HEIGHT - 100))
        self.screen.blit(assets.icon6, (1640, SCREEN_HEIGHT - 100))
        self.screen.blit(assets.icon7, (1960, SCREEN_HEIGHT - 100))
        self.screen.blit(assets.icon8, (2280, SCREEN_HEIGHT - 100))

        self.screen.blit(assets.font_small.render("(1):100", True, WHITE), (140, SCREEN_HEIGHT - 85))
        self.screen.blit(assets.font_small.render("(2):50", True, WHITE), (460, SCREEN_HEIGHT - 85))
        self.screen.blit(assets.font_small.render("(3):150", True, WHITE), (780, SCREEN_HEIGHT - 85))
        self.screen.blit(assets.font_small.render("(4):300", True, WHITE), (1100, SCREEN_HEIGHT - 85))
        self.screen.blit(assets.font_small.render("(5):200", True, WHITE), (1420, SCREEN_HEIGHT - 85))
        self.screen.blit(assets.font_small.render("(6):400", True, WHITE), (1740, SCREEN_HEIGHT - 85))
        self.screen.blit(assets.font_small.render("(7):250", True, WHITE), (2060, SCREEN_HEIGHT - 85))
        self.screen.blit(assets.font_small.render("(8):175", True, WHITE), (2380, SCREEN_HEIGHT - 85))

        positions = {
            TowerType.PHYSICAL: (40, SCREEN_HEIGHT - 100),
            TowerType.PRODUCTION: (360, SCREEN_HEIGHT - 100),
            TowerType.ICE: (680, SCREEN_HEIGHT - 100),
            TowerType.TELEPORT: (1000, SCREEN_HEIGHT - 100),
            TowerType.FLAME: (1320, SCREEN_HEIGHT - 100),
            TowerType.TRIDENT: (1640, SCREEN_HEIGHT - 100),
            TowerType.WIND: (1960, SCREEN_HEIGHT - 100),
            TowerType.POISON: (2280, SCREEN_HEIGHT - 100)
        }
        if self.selected_tower_type in positions:
            x, y = positions[self.selected_tower_type]
            pygame.draw.rect(self.screen, WHITE, (x, y, 80, 80), 4)

        pygame.draw.rect(self.screen, INFO_BORDER_COLOR,
                         (INFO_BORDER_X, INFO_BORDER_Y, INFO_BORDER_SIZE, INFO_BORDER_SIZE), INFO_BORDER_WIDTH)
        if self.selected_tower:
            infos = self.get_tower_info(self.selected_tower)
            for i, info in enumerate(infos):
                self.screen.blit(assets.font_small.render(info, True, WHITE),
                                 (INFO_BORDER_X + 20, INFO_BORDER_Y + 20 + i * 32))
        pygame.draw.rect(self.screen, RESTART_BTN_COLOR,
                         (RESTART_BTN_X, RESTART_BTN_Y, RESTART_BTN_WIDTH, RESTART_BTN_HEIGHT))
        restart_text = assets.font_small.render("重新开始", True, WHITE)
        self.screen.blit(restart_text, (RESTART_BTN_X + 40, RESTART_BTN_Y + 10))

        pygame.draw.rect(self.screen, EXIT_BTN_COLOR,
                         (EXIT_BTN_X, EXIT_BTN_Y, EXIT_BTN_WIDTH, EXIT_BTN_HEIGHT))
        exit_text = assets.font_small.render("退出游戏", True, WHITE)
        self.screen.blit(exit_text, (EXIT_BTN_X + EXIT_BTN_WIDTH // 2 - exit_text.get_width() // 2, EXIT_BTN_Y + 10))

    def draw_weather_particles(self):
        for p in self.weather_particles:
            if p[-1] == "rain":
                x, y, _, length = p[0], p[1], p[2], p[3]
                color = (100, 150, 255, 180)
                s = pygame.Surface((2, length), pygame.SRCALPHA)
                s.fill(color)
                self.screen.blit(s, (int(x), int(y)))
            elif p[-1] == "acid_rain":
                x, y, _, length = p[0], p[1], p[2], p[3]
                color = (0, 200, 0, 180)
                s = pygame.Surface((2, length), pygame.SRCALPHA)
                s.fill(color)
                self.screen.blit(s, (int(x), int(y)))
            elif p[-1] == "snow":
                x, y, _, _, size = p[0], p[1], p[2], p[3], p[4]
                color = (255, 255, 255, 200)
                s = pygame.Surface((size * 2, size * 2), pygame.SRCALPHA)
                pygame.draw.circle(s, color, (size, size), size)
                self.screen.blit(s, (int(x) - size, int(y) - size))

    def draw_weather_banner(self):
        if self.weather_banner_timer <= 0:
            return
        alpha = min(255, self.weather_banner_timer * 2)
        banner_w = 1200
        banner_h = 60
        banner_x = SCREEN_WIDTH // 2 - banner_w // 2
        banner_y = 200
        s = pygame.Surface((banner_w, banner_h), pygame.SRCALPHA)
        s.fill((0, 0, 0, min(180, alpha)))
        self.screen.blit(s, (banner_x, banner_y))
        text = assets.font_medium.render(self.weather_banner_text, True, WHITE)
        text.set_alpha(alpha)
        self.screen.blit(text, (SCREEN_WIDTH // 2 - text.get_width() // 2, banner_y + 10))

    def draw_pause_overlay(self):
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 128))
        self.screen.blit(overlay, (0, 0))
        pause_text = assets.font_large.render("已暂停", True, WHITE)
        continue_text = assets.font_small.render("按 P 继续", True, WHITE)
        self.screen.blit(pause_text, (SCREEN_WIDTH // 2 - pause_text.get_width() // 2, SCREEN_HEIGHT // 2 - 60))
        self.screen.blit(continue_text, (SCREEN_WIDTH // 2 - continue_text.get_width() // 2, SCREEN_HEIGHT // 2 + 20))

    def draw_game_over(self):
        self.screen.fill(BLACK)
        text1 = assets.font_large.render("游戏结束!", True, RED)
        self.screen.blit(text1, (SCREEN_WIDTH // 2 - text1.get_width() // 2, 400))
        pygame.draw.rect(self.screen, GREEN, (900, 850, 760, 80))
        restart_text = assets.font_medium.render("重新开始", True, WHITE)
        self.screen.blit(restart_text, (SCREEN_WIDTH // 2 - restart_text.get_width() // 2, 855))

    def draw_victory(self):
        self.screen.fill(BLACK)
        text1 = assets.font_large.render("胜利!", True, GREEN)
        self.screen.blit(text1, (SCREEN_WIDTH // 2 - text1.get_width() // 2, 400))
        pygame.draw.rect(self.screen, GREEN, (900, 850, 760, 80))
        restart_text = assets.font_medium.render("重新开始", True, WHITE)
        self.screen.blit(restart_text, (SCREEN_WIDTH // 2 - restart_text.get_width() // 2, 855))

    def get_tower_info(self, tower):
        base_cost_map = {
            TowerType.PHYSICAL: 100,
            TowerType.PRODUCTION: 50,
            TowerType.ICE: 150,
            TowerType.TELEPORT: 300,
            TowerType.FLAME: 200,
            TowerType.TRIDENT: 400,
            TowerType.WIND: 250,
            TowerType.POISON: 175
        }
        info = []
        if tower.type == TowerType.PHYSICAL:
            if tower.level >= 11:
                info = [f"时空撕裂箭塔 Lv{tower.level}", f"伤害:{tower.damage}", f"攻击间隔:0.5s",
                        f"将当前金币的1%作为伤害加成", f"破甲:受伤永久增加20%"]
            elif tower.level >= 6:
                info = [f"黄金箭塔 Lv{tower.level}", f"伤害:{tower.damage}", f"攻击间隔:0.5s", f"将当前金币的1%作为伤害加成"]
            else:
                info = [f"箭塔 Lv{tower.level}", f"伤害:{tower.damage}", f"攻击间隔:{tower.fire_rate / 60}s"]
        elif tower.type == TowerType.PRODUCTION:
            if tower.level >= 11:
                info = [f"无尽矿 Lv{tower.level}", f"全局产量:{self.gold_per_second}/s",
                        f"全局每波产出:{10 * self.gold_per_wave}*当前波数", f"全局每波利息:{int(100 * self.gold_profit_per_wave)}%"]
            elif tower.level >= 6:
                info = [f"下界金矿 Lv{tower.level}", f"全局每波产出:{10 * self.gold_per_wave}*当前波数",
                        f"全局产量:{self.gold_per_second}/s"]
            else:
                info = [f"金矿 Lv{tower.level}", f"全局产量:{self.gold_per_second}/s"]
        elif tower.type == TowerType.ICE:
            if tower.level >= 11:
                bonus = 300 + 150 * (tower.level - 11)
                info = [f"冰霜炸弹塔 Lv{tower.level}", f"减速:50%", f"伤害:{tower.damage}", f"冻结:{tower.freeze_time}s",
                        f"对冻结+{bonus}伤害", f"攻击间隔:0.5s"]
            elif tower.level >= 6:
                info = [f"冰球塔 Lv{tower.level}", f"减速:50%", f"伤害:{tower.damage}", f"冻结:{tower.freeze_time}s",
                        f"攻击间隔:0.5s"]
            else:
                info = [f"缓慢箭塔 Lv{tower.level}", f"减速:50%", f"伤害:{tower.damage}", f"攻击间隔:{tower.fire_rate / 60}s"]
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
                dmg_mult = (tower.level - 10) ** 2
                info = [f"龙息塔 Lv{tower.level}", f"伤害:{tower.damage}", f"燃烧:{self.temperature}/s,持续4s",
                        f"龙息:{dmg_mult}倍温度/s", f"击晕:{tower.stun_time}s", f"攻击间隔:0.5s"]
            elif tower.level >= 6:
                info = [f"火球塔 Lv{tower.level}", f"伤害:{tower.damage}", f"燃烧:{self.temperature}/s,持续4s",
                        f"击晕:{tower.stun_time}s", f"攻击间隔:0.5s"]
            else:
                info = [f"火焰塔 Lv{tower.level}", f"伤害:{tower.damage}", f"燃烧:{self.temperature}/s,持续4s",
                        f"攻击间隔:{tower.fire_rate / 60}s"]
        elif tower.type == TowerType.TRIDENT:
            if tower.level >= 11:
                mult_text = "3倍" if tower.level >= 15 else "2倍"
                info = [f"海神三叉戟 Lv{tower.level}", f"伤害:{tower.damage}", f"闪电:{tower.lightning_damage}",
                        f"将当前金币的1%作为伤害加成", f"伤害倍率:{mult_text}",
                        f"攻击施放十字闪电", f"攻击间隔:0.5s"]
            elif tower.level >= 6:
                info = [f"黄金三叉戟 Lv{tower.level}", f"伤害:{tower.damage}", f"闪电:{tower.lightning_damage}",
                        f"将当前金币的1%作为伤害加成", f"攻击间隔:0.5s"]
            else:
                info = [f"三叉戟塔 Lv{tower.level}", f"伤害:{tower.damage}", f"闪电:{tower.lightning_damage}",
                        f"攻击间隔:{tower.fire_rate / 60}s"]
        elif tower.type == TowerType.WIND:
            if tower.level >= 11:
                per_px = {11: 8, 12: 10, 13: 12, 14: 14, 15: 16}
                stun_s = {11: 0.1, 12: 0.2, 13: 0.3, 14: 0.4, 15: 0.5}
                info = [f"重锤塔 Lv{tower.level}", f"伤害:{tower.damage}+{per_px.get(tower.level,8)}/px",
                        f"击退:{tower.wind_knockback}px", f"击晕:{stun_s.get(tower.level,0.1)}s", f"攻击间隔:0.5s"]
            elif tower.level >= 6:
                info = [f"蓄风箭塔 Lv{tower.level}", f"伤害:{tower.damage}", f"击退:{tower.wind_knockback}px",
                        f"蓄风印记", f"攻击间隔:0.5s"]
            else:
                info = [f"风弹塔 Lv{tower.level}", f"伤害:{tower.damage}", f"击退:{tower.wind_knockback}px",
                        f"攻击间隔:{tower.fire_rate / 60}s"]
        elif tower.type == TowerType.POISON:
            if tower.level >= 11:
                stacks = tower.level * 4
                info = [f"剧毒环刃塔 Lv{tower.level}", f"伤害:{tower.damage}",
                        f"中毒层数:{stacks}层/次", f"攻击间隔:0.5s"]
            elif tower.level >= 6:
                info = [f"毒瓶塔 Lv{tower.level}", f"伤害:{tower.damage}",
                        f"中毒层数:{tower.level}层/次", f"范围溅射", f"攻击间隔:0.5s"]
            else:
                info = [f"毒箭塔 Lv{tower.level}", f"伤害:{tower.damage}",
                        f"中毒层数:{tower.level}层/次", f"攻击间隔:{tower.fire_rate / 60}s"]
        upgrade_str = "MAX" if tower.level >= 15 else str(tower.upgrade_cost)
        info.extend(
            [f"射程:{round(tower.get_effective_range() / TILE_SIZE, 1)}", f"升级:{upgrade_str}"])
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
        costs = {TowerType.PHYSICAL: 100, TowerType.PRODUCTION: 50, TowerType.ICE: 150, TowerType.TELEPORT: 300,
                 TowerType.FLAME: 200, TowerType.TRIDENT: 400, TowerType.WIND: 250, TowerType.POISON: 175}
        return self.coins >= costs.get(self.selected_tower_type, 9999)

    def build_tower(self, x, y, tower_type):
        costs = {TowerType.PHYSICAL: 100, TowerType.PRODUCTION: 50, TowerType.ICE: 150, TowerType.TELEPORT: 300,
                 TowerType.FLAME: 200, TowerType.TRIDENT: 400, TowerType.WIND: 250, TowerType.POISON: 175}
        cost = costs[tower_type]
        if self.coins >= cost:
            self.coins -= cost
            t = Tower(tower_type, x, y, self)
            self.towers.add(t)
            if tower_type == TowerType.PRODUCTION:
                self.gold_per_second += 1
            if tower_type in (TowerType.FLAME, TowerType.TRIDENT):
                self.temperature += 1

    def start_game(self):
        self.generate_weather_forecast()
        self.state = GameState.PLAYING
        self.wave_manager.start_new_wave()
        self.pending_first_wave_weather = True
        self.weather_banner_text = "准备时间"
        self.weather_banner_timer = 300

    def reset_game(self):
        self.path = random.choice(SEED_PATHS)
        self.start_point = self.path[0]
        self.end_point = self.path[-1]
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
        self.horizontal_lightning_effects = []
        self.thunderstorm_timer = 0
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
