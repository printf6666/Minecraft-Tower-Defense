import pygame
import math
import assets
from config import *
from tower import TowerType
from enemy import EnemyType
from effects import WindExplosion, IceExplosion, DragonBreathPool, LightningEffect, HorizontalLightningEffect, PoisonSplash, TNTExplosion, MushroomExplosion, NuclearShockwave, WitherSplash


class UIManager:
    def __init__(self, game):
        self.game = game

    def draw_menu(self):
        title = assets.font_large.render("像素防线:晶域守卫", True, WHITE)
        self.game.screen.blit(title, (SCREEN_WIDTH // 2 - title.get_width() // 2, 300))
        pygame.draw.rect(self.game.screen, GREEN, (900, 840, 760, 80))
        start_text = assets.font_medium.render("开始游戏", True, WHITE)
        self.game.screen.blit(start_text, (1200, 855))
        pygame.draw.rect(self.game.screen, PURPLE, (900, 930, 760, 80))
        boss_text = assets.font_medium.render("BOSS战", True, WHITE)
        self.game.screen.blit(boss_text, (1200, 945))
        pygame.draw.rect(self.game.screen, RED, (900, 1020, 760, 80))
        exit_text = assets.font_medium.render("退出游戏", True, WHITE)
        self.game.screen.blit(exit_text, (1200, 1035))
        instructions = ["游戏说明:", "1. 鼠标点击建造炮塔", "2. 1/2/3/4/5/6/7/8/9键选择炮塔", "3. U升级 S出售 ESC暂停  R切换形态/TNT子类/毒分支"]
        for i, text in enumerate(instructions):
            text_surface = assets.font_small.render(text, True, WHITE)
            self.game.screen.blit(text_surface, (900, 1200 + i * 50))

    def draw_game(self):
        self.game.screen.blit(self.game.background_surface, (0, 0))

        self.game.towers.draw(self.game.screen)
        self.game.enemies.draw(self.game.screen)
        self.game.bullets.draw(self.game.screen)
        for dragon in self.game.dragons:
            dragon.draw(self.game.screen)
        for tower in self.game.towers:
            self.game.screen.blit(assets.font_tower_level.render(f"Lv{tower.level}", True, YELLOW),
                                 (tower.x * TILE_SIZE + 70, tower.y * TILE_SIZE + 90))
        for enemy in self.game.enemies:
            enemy.draw_health_bar(self.game.screen)

        self.draw_command_blocks()

        if self.game.show_range and self.game.selected_tower:
            self.game.selected_tower.draw_range(self.game.screen)

        self.draw_weather_particles()
        self.draw_weather_banner()

        if self.game.fog_visible:
            gw = GRID_WIDTH * TILE_SIZE
            gh = GRID_HEIGHT * TILE_SIZE
            s = pygame.Surface((gw, gh), pygame.SRCALPHA)
            s.fill((0, 0, 0, 255))
            self.game.screen.blit(s, (0, TILE_SIZE))

        for pool in self.game.dragon_breath_pools:
            pool.draw(self.game.screen)
        for effect in self.game.lightning_effects:
            effect.draw(self.game.screen)
        for explosion in self.game.wind_explosions:
            explosion.draw(self.game.screen)
        for exp in self.game.ice_explosions:
            exp.draw(self.game.screen)
        for splash in self.game.poison_splashes:
            splash.draw(self.game.screen)
        for splash in self.game.wither_splashes:
            splash.draw(self.game.screen)
        for effect in self.game.horizontal_lightning_effects:
            effect.draw(self.game.screen)
        for explosion in self.game.tnt_explosions:
            explosion.draw(self.game.screen)
        for sw in self.game.shockwave_effects:
            sw.draw(self.game.screen)
        for explosion in self.game.mushroom_explosions:
            explosion.draw(self.game.screen)
        self.game.damage_texts.draw(self.game.screen)

        self.draw_ui()
        self.draw_herobrine_health_bar()
        if self.game.state == GameState.PAUSED:
            self.draw_pause_overlay()

    def draw_ui(self):
        pygame.draw.rect(self.game.screen, BLACK, (0, 0, SCREEN_WIDTH, 80))
        pygame.draw.line(self.game.screen, WHITE, (0, 80), (SCREEN_WIDTH, 80), 4)
        self.game.screen.blit(assets.gold_img, (0, 8))
        self.game.screen.blit(assets.font_medium.render(str(self.game.coins), True, GOLD), (70, 16))
        self.game.screen.blit(assets.heart_img, (320, -25))
        self.game.screen.blit(assets.font_medium.render(str(self.game.lives), True, RED), (420, 16))
        self.game.screen.blit(
            assets.font_medium.render(f"波数:{self.game.wave_manager.current_wave}/{self.game.wave_manager.total_waves}", True, WHITE),
            (520, 16))
        weather_name = WEATHER_CONFIG[self.game.weather]["name"]
        weather_color = WEATHER_CONFIG[self.game.weather]["color"]
        self.game.screen.blit(assets.font_medium.render(f"天气:{weather_name}  温度:{self.game.temperature}", True, weather_color), (1550, 16))

        can_buy = self.game.state == GameState.PLAYING and not self.game.forecast_purchased
        can_afford = self.game.coins >= 100 * self.game.wave_manager.current_wave
        btn_color = FORECAST_BTN_COLOR if can_buy and can_afford else FORECAST_BTN_COLOR_DISABLED
        pygame.draw.rect(self.game.screen, btn_color,
                         (FORECAST_BTN_X, FORECAST_BTN_Y, FORECAST_BTN_WIDTH, FORECAST_BTN_HEIGHT))
        if self.game.forecast_purchased and 0 <= self.game.forecast_weather_idx < len(self.game.weather_forecast):
            w = self.game.weather_forecast[self.game.forecast_weather_idx]
            label = f"天气预报:{WEATHER_CONFIG[w]['name']}"
        else:
            label = f"天气预报:花费{100*self.game.wave_manager.current_wave}金"
        fc_color = WHITE if can_afford else GRAY
        fc_text = assets.font_small.render(label, True, fc_color)
        self.game.screen.blit(fc_text, (FORECAST_BTN_X + 20, FORECAST_BTN_Y + 10))

        pygame.draw.rect(self.game.screen, BLACK, (0, SCREEN_HEIGHT - 128, SCREEN_WIDTH, 128))
        pygame.draw.line(self.game.screen, WHITE, (0, SCREEN_HEIGHT - 128), (SCREEN_WIDTH, SCREEN_HEIGHT - 128), 4)

        icon_size = 100
        gap = 64
        step = icon_size + gap
        total_w = len(self.game.TOWER_DATA) * step - gap
        bar_left = 60
        bar_right = INFO_BORDER_X - 40
        start_x = bar_left + (bar_right - bar_left - total_w) // 2
        positions = {}
        for i, (ttype, name, cost, key) in enumerate(self.game.TOWER_DATA):
            ix = start_x + i * step
            iy = SCREEN_HEIGHT - 114
            self.game.screen.blit(assets.tower_icons[i], (ix, iy))
            num_surf = assets.font_tower_level.render(str(i + 1), True, YELLOW)
            self.game.screen.blit(num_surf, (ix + 2, iy + 2))
            price_surf = assets.font_tower_level.render(str(cost), True, GOLD)
            self.game.screen.blit(price_surf, (ix + icon_size - price_surf.get_width() - 2,
                                              iy + icon_size - price_surf.get_height() - 2))
            positions[ttype] = (ix, iy)
        if self.game.selected_tower_type in positions:
            x, y = positions[self.game.selected_tower_type]
            hl = 110
            pygame.draw.rect(self.game.screen, WHITE, (x - (hl - icon_size) // 2, y - (hl - icon_size) // 2, hl, hl), 4)

        pygame.draw.rect(self.game.screen, INFO_BORDER_COLOR,
                         (INFO_BORDER_X, INFO_BORDER_Y, INFO_BORDER_SIZE, INFO_BORDER_SIZE), INFO_BORDER_WIDTH)
        if self.game.selected_tower:
            infos = self.game.get_tower_info(self.game.selected_tower)
            for i, info in enumerate(infos):
                self.game.screen.blit(assets.font_small.render(info, True, WHITE),
                                     (INFO_BORDER_X + 20, INFO_BORDER_Y + 20 + i * 32))
        pygame.draw.rect(self.game.screen, RESTART_BTN_COLOR,
                         (RESTART_BTN_X, RESTART_BTN_Y, RESTART_BTN_WIDTH, RESTART_BTN_HEIGHT))
        restart_text = assets.font_small.render("重新开始", True, WHITE)
        self.game.screen.blit(restart_text, (RESTART_BTN_X + 40, RESTART_BTN_Y + 10))

        pygame.draw.rect(self.game.screen, EXIT_BTN_COLOR,
                         (EXIT_BTN_X, EXIT_BTN_Y, EXIT_BTN_WIDTH, EXIT_BTN_HEIGHT))
        exit_text = assets.font_small.render("退出游戏", True, WHITE)
        self.game.screen.blit(exit_text, (EXIT_BTN_X + EXIT_BTN_WIDTH // 2 - exit_text.get_width() // 2, EXIT_BTN_Y + 10))

    def draw_weather_particles(self):
        for p in self.game.weather_particles:
            if p[-1] == "rain":
                x, y, _, length = p[0], p[1], p[2], p[3]
                s = assets.rain_cache.get(length)
                if s is None:
                    s = pygame.Surface((2, length), pygame.SRCALPHA)
                    s.fill((100, 150, 255, 180))
                    assets.rain_cache[length] = s
                self.game.screen.blit(s, (int(x), int(y)))
            elif p[-1] == "acid_rain":
                x, y, _, length = p[0], p[1], p[2], p[3]
                s = assets.acid_rain_cache.get(length)
                if s is None:
                    s = pygame.Surface((2, length), pygame.SRCALPHA)
                    s.fill((0, 200, 0, 180))
                    assets.acid_rain_cache[length] = s
                self.game.screen.blit(s, (int(x), int(y)))
            elif p[-1] == "snow":
                x, y, _, _, size = p[0], p[1], p[2], p[3], p[4]
                s = assets.snow_cache.get(size)
                if s is None:
                    s = pygame.Surface((size * 2, size * 2), pygame.SRCALPHA)
                    pygame.draw.circle(s, (255, 255, 255, 200), (size, size), size)
                    assets.snow_cache[size] = s
                self.game.screen.blit(s, (int(x) - size, int(y) - size))
            elif p[-1] == "fire":
                x, y, _, _, size, phase = p[0], p[1], p[2], p[3], p[4], p[5]
                flicker = int(30 * (0.5 + 0.5 * math.sin(phase)))
                r = min(255, 200 + flicker)
                g = max(0, min(200, 150 - flicker))
                alpha = min(200, 120 + flicker)
                color_key = (r, g, 0)
                s = assets.fire_cache.get((size, color_key))
                if s is None:
                    s = pygame.Surface((size * 2, size * 2), pygame.SRCALPHA)
                    pygame.draw.circle(s, (*color_key, alpha), (size, size), size)
                    pygame.draw.circle(s, (255, 255, 100, alpha // 2), (size, size), size // 2)
                    assets.fire_cache[(size, color_key)] = s
                self.game.screen.blit(s, (int(x) - size, int(y) - size))

    def draw_weather_banner(self):
        if self.game.weather_banner_timer <= 0:
            return
        alpha = min(255, self.game.weather_banner_timer * 2)
        banner_w = 1200
        banner_h = 60
        banner_x = SCREEN_WIDTH // 2 - banner_w // 2
        banner_y = 200
        s = pygame.Surface((banner_w, banner_h), pygame.SRCALPHA)
        s.fill((0, 0, 0, min(180, alpha)))
        self.game.screen.blit(s, (banner_x, banner_y))
        text = assets.font_medium.render(self.game.weather_banner_text, True, WHITE)
        text.set_alpha(alpha)
        self.game.screen.blit(text, (SCREEN_WIDTH // 2 - text.get_width() // 2, banner_y + 10))

    def draw_pause_overlay(self):
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 128))
        self.game.screen.blit(overlay, (0, 0))
        pause_text = assets.font_large.render("已暂停", True, WHITE)
        continue_text = assets.font_small.render("按 ESC 继续", True, WHITE)
        self.game.screen.blit(pause_text, (SCREEN_WIDTH // 2 - pause_text.get_width() // 2, SCREEN_HEIGHT // 2 - 60))
        self.game.screen.blit(continue_text, (SCREEN_WIDTH // 2 - continue_text.get_width() // 2, SCREEN_HEIGHT // 2 + 20))

    def draw_game_over(self):
        self.game.screen.fill(BLACK)
        text1 = assets.font_large.render("游戏结束!", True, RED)
        self.game.screen.blit(text1, (SCREEN_WIDTH // 2 - text1.get_width() // 2, 400))
        pygame.draw.rect(self.game.screen, GREEN, (900, 850, 760, 80))
        restart_text = assets.font_medium.render("重新开始", True, WHITE)
        self.game.screen.blit(restart_text, (SCREEN_WIDTH // 2 - restart_text.get_width() // 2, 855))

    def draw_herobrine_health_bar(self):
        for enemy in self.game.enemies:
            if enemy.enemy_type == EnemyType.HEROBRINE:
                bar_x = 810
                bar_y = 20
                bar_width = 740
                bar_height = 50
                pygame.draw.rect(self.game.screen, (100, 0, 0), (bar_x, bar_y, bar_width, bar_height))
                health_ratio = enemy.health / enemy.max_health
                fill_width = int(bar_width * health_ratio)
                pygame.draw.rect(self.game.screen, (0, 255, 0), (bar_x, bar_y, fill_width, bar_height))
                layers_text = assets.font_medium.render(f"*{enemy.current_layer}", True, WHITE)
                text_x = bar_x + bar_width - layers_text.get_width() - 5
                text_y = bar_y + (bar_height - layers_text.get_height()) // 2
                self.game.screen.blit(layers_text, (text_x, text_y))
                break

    def draw_command_blocks(self):
        for cb in self.game.command_blocks:
            if cb["exploded"]:
                continue
            x, y = cb["x"], cb["y"]
            timer = cb["timer"]
            if timer > 0:
                alpha = 150 + int(100 * (timer % 30) / 30)
                img = assets.command_block_img.copy()
                img.set_alpha(alpha)
                self.game.screen.blit(img, (x * TILE_SIZE, y * TILE_SIZE))

    def draw_victory(self):
        self.game.screen.fill(BLACK)
        text1 = assets.font_large.render("胜利!", True, GREEN)
        self.game.screen.blit(text1, (SCREEN_WIDTH // 2 - text1.get_width() // 2, 400))
        pygame.draw.rect(self.game.screen, GREEN, (900, 850, 760, 80))
        restart_text = assets.font_medium.render("重新开始", True, WHITE)
        self.game.screen.blit(restart_text, (SCREEN_WIDTH // 2 - restart_text.get_width() // 2, 855))