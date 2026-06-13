import pygame
import assets
from config import *
from tower import WindExplosion


class Enemy(pygame.sprite.Sprite):
    def __init__(self, path, enemy_type, game):
        super().__init__()
        self.path = path
        self.path_index = 0
        self.game = game

        self.enemy_type = enemy_type
        enemy_key = enemy_type.name
        config = ENEMY_TYPES[enemy_key]

        self.speed = config["speed"]
        self.max_health = config["health"] * (1.2 ** game.wave_manager.current_wave)
        self.health = self.max_health
        self.reward = config["reward"]
        self.base_speed = self.speed

        self.stun_time = 0
        self.freeze_time = 0
        self.slow_time = 0
        self.burn_time = 0
        self.burn_damage = 0
        self.broken = False
        self.wind_mark_tower = None
        self.contaminated = False
        self.contaminated_timer = 0

        self.weather_slowed = False
        self.freeze_resistance = 0.0
        self.stun_resistance = 0.0
        self.last_freeze_time = -9999
        self.last_stun_time = -9999
        rain_weathers = (Weather.RAINY, Weather.THUNDERSTORM, Weather.ACID_RAIN)
        if game.weather in rain_weathers:
            self.speed *= 0.5
            self.base_speed = self.speed
            self.weather_slowed = True

        if game.weather == Weather.TAILWIND:
            self.speed *= 1.5
            self.base_speed = self.speed
            self.tailwind_boosted = True
        else:
            self.tailwind_boosted = False

        if game.weather == Weather.HEADWIND or game.weather == Weather.EXTREME_COLD:
            self.speed *= 0.5
            self.base_speed = self.speed
            self.weather_slowed = True

        if game.weather == Weather.SCORCHING_SUN:
            self.burn_damage = max(self.burn_damage, game.temperature)
            self.burn_time = max(self.burn_time, 999999)
        if game.weather == Weather.FIRE_RAIN:
            self.burn_damage = max(self.burn_damage, game.temperature)
            self.burn_time = max(self.burn_time, 999999)

        self.poison_stacks = 0
        self.poison_timer = 0
        if game.weather == Weather.ACID_RAIN:
            self.poison_stacks = 10
        if game.weather == Weather.MAGNETIC_STORM:
            if self.enemy_type in (EnemyType.ARMORED, EnemyType.GOLD_ARMORED):
                self.broken = True

        self.image = assets.load_image(f"enemy/{config['image']}")

        if enemy_key == "GHOST":
            self.image = pygame.transform.scale(self.image, (200, 200))
        elif enemy_key == "ARMORED" or enemy_key == "GOLD_ARMORED":
            self.image = pygame.transform.scale(self.image, (100, 100))
        elif enemy_key == "SLIMELING":
            self.image = pygame.transform.scale(self.image, (64, 64))
        elif enemy_key == "NORMAL" or enemy_key == "FAST":
            original_w = self.image.get_width()
            original_h = self.image.get_height()
            self.image = pygame.transform.scale(self.image, (original_w * 2, original_h * 2))
        else:
            self.image = pygame.transform.scale(self.image, (TILE_SIZE - 8, TILE_SIZE - 8))

        self.rect = self.image.get_rect()
        start_x, start_y = self.path[self.path_index]
        self.pos_x = start_x * TILE_SIZE + TILE_SIZE // 2
        self.pos_y = start_y * TILE_SIZE + TILE_SIZE // 2
        self.rect.center = (self.pos_x, self.pos_y)

        if self.enemy_type == EnemyType.GHOST:
            ex, ey = self.path[-1]
            self.ghost_target = (ex * TILE_SIZE + TILE_SIZE // 2, ey * TILE_SIZE + TILE_SIZE // 2)

    def apply_slow(self, slow_factor, duration):
        rain_weathers = (Weather.RAINY, Weather.THUNDERSTORM, Weather.ACID_RAIN, Weather.EXTREME_COLD)
        if self.game.weather in rain_weathers:
            return
        self.speed = self.base_speed * slow_factor
        self.slow_time = duration

    def apply_burn(self, damage, duration):
        rain_weathers = (Weather.RAINY, Weather.THUNDERSTORM, Weather.ACID_RAIN, Weather.EXTREME_COLD)
        if self.game.weather in rain_weathers:
            return
        self.burn_damage = damage
        self.burn_time = duration

    def apply_freeze(self, duration):
        if self.game.weather == Weather.FIRE_RAIN:
            return
        effective = int(duration * (1.0 - self.freeze_resistance))
        self.freeze_time = max(self.freeze_time, effective)
        self.freeze_resistance = min(0.90, self.freeze_resistance + 0.10)
        self.last_freeze_time = self.game.game_time

    def apply_stun(self, duration):
        effective = int(duration * (1.0 - self.stun_resistance))
        self.stun_time = max(self.stun_time, effective)
        self.stun_resistance = min(0.90, self.stun_resistance + 0.10)
        self.last_stun_time = self.game.game_time

    def apply_poison(self, stacks):
        if self.game.weather == Weather.ACID_RAIN:
            stacks *= 2
        self.poison_stacks += stacks

    def apply_contaminate(self):
        self.contaminated = True

    def update(self):
        if self.health <= 0:
            return False

        if self.game.game_time - self.last_freeze_time > 600:
            self.freeze_resistance = 0.0
        if self.game.game_time - self.last_stun_time > 600:
            self.stun_resistance = 0.0

        if self.stun_time > 0:
            self.stun_time -= 1
            return False
        if self.freeze_time > 0:
            self.freeze_time -= 1
            return False
        if self.slow_time > 0:
            self.slow_time -= 1
        else:
            self.speed = self.base_speed
        if self.burn_time > 0:
            self.burn_time -= 1
            if self.burn_time % 30 == 0:
                reward = self.take_damage(self.burn_damage, color=YELLOW, scale=1.0)
                self.game.coins += reward

        if self.poison_stacks > 0:
            self.poison_timer += 1
            if self.poison_timer >= 75:
                self.poison_timer = 0
                reward = self.take_damage(self.poison_stacks, color=GREEN, scale=1.0)
                self.game.coins += reward

        if self.contaminated:
            self.contaminated_timer += 1
            if self.contaminated_timer >= 120:
                self.contaminated_timer = 0
                dmg = int(self.max_health * 0.01)
                reward = self.take_damage(dmg, color=(0, 255, 100), scale=1.0)
                self.game.coins += reward

        if self.health <= 0:
            self.kill()
            return False

        if self.enemy_type == EnemyType.GHOST:
            tx, ty = self.ghost_target
            dx = tx - self.pos_x
            dy = ty - self.pos_y
            dist = (dx * dx + dy * dy) ** 0.5
            if dist < self.speed:
                self.game.lives -= 4
                self.kill()
                return True
            self.pos_x += (dx / dist) * self.speed
            self.pos_y += (dy / dist) * self.speed
            self.rect.center = (self.pos_x, self.pos_y)
            return False

        if self.path_index >= len(self.path) - 1:
            self.game.lives -= 1
            self.kill()
            return True

        target_x, target_y = self.path[self.path_index + 1]
        target_pixel_x = target_x * TILE_SIZE + TILE_SIZE // 2
        target_pixel_y = target_y * TILE_SIZE + TILE_SIZE // 2

        dx = target_pixel_x - self.pos_x
        dy = target_pixel_y - self.pos_y
        distance = (dx ** 2 + dy ** 2) ** 0.5

        if distance < self.speed:
            self.pos_x = target_pixel_x
            self.pos_y = target_pixel_y
            self.path_index += 1
        else:
            self.pos_x += (dx / distance) * self.speed
            self.pos_y += (dy / distance) * self.speed

        self.rect.center = (self.pos_x, self.pos_y)
        return False

    def get_active_buffs(self):
        buff_list = []
        if self.broken:
            buff_list.append("broken")
        if self.stun_time > 0:
            buff_list.append("stun")
        if self.freeze_time > 0:
            buff_list.append("freeze")
        if self.slow_time > 0 or self.weather_slowed:
            buff_list.append("slow")
        if self.burn_time > 0:
            buff_list.append("burn")
        if self.poison_stacks > 0:
            buff_list.append("poison")
        if self.wind_mark_tower is not None:
            buff_list.append("wind")
        if self.tailwind_boosted:
            buff_list.append("speed")
        if self.contaminated:
            buff_list.append("contaminated")
        return buff_list

    def teleport_to_start(self):
        self.path_index = 0
        start_x, start_y = self.path[self.path_index]
        self.pos_x = start_x * TILE_SIZE + TILE_SIZE // 2
        self.pos_y = start_y * TILE_SIZE + TILE_SIZE // 2
        self.rect.center = (self.pos_x, self.pos_y)

    def apply_knockback(self, distance):
        if self.enemy_type in (EnemyType.ARMORED, EnemyType.GOLD_ARMORED):
            return
        if self.path_index <= 0:
            return
        remaining = distance
        while remaining > 0:
            tx = self.path[self.path_index][0] * TILE_SIZE + TILE_SIZE // 2
            ty = self.path[self.path_index][1] * TILE_SIZE + TILE_SIZE // 2
            dx = tx - self.pos_x
            dy = ty - self.pos_y
            dist_to_target = (dx * dx + dy * dy) ** 0.5
            if dist_to_target <= 0:
                if self.path_index > 0:
                    self.path_index -= 1
                else:
                    break
                continue
            if remaining < dist_to_target:
                self.pos_x += (dx / dist_to_target) * remaining
                self.pos_y += (dy / dist_to_target) * remaining
                remaining = 0
            else:
                self.pos_x = tx
                self.pos_y = ty
                remaining -= dist_to_target
                if self.path_index > 0:
                    self.path_index -= 1
                else:
                    break
        self.rect.center = (self.pos_x, self.pos_y)

    def take_damage(self, damage, color=RED, scale=1.0):
        if self.health <= 0:
            return 0

        final_dmg = damage
        if self.enemy_type in (EnemyType.ARMORED, EnemyType.GOLD_ARMORED) and not self.broken:
            final_dmg *= 0.3
        if self.broken:
            final_dmg *= 1.2
        final_dmg = int(final_dmg)
        self.health -= final_dmg

        if self.game:
            self.game.spawn_damage_text(final_dmg, self.rect.center, color=color, scale=scale)

        if self.health <= 0:
            if self.enemy_type == EnemyType.SLIME:
                for _ in range(3):
                    child = Enemy(self.path, EnemyType.SLIMELING, self.game)
                    child.path_index = self.path_index
                    child.pos_x = self.pos_x
                    child.pos_y = self.pos_y
                    child.rect.center = (child.pos_x, child.pos_y)
                    self.game.enemies.add(child)
            if self.wind_mark_tower is not None:
                t = self.wind_mark_tower
                exp = WindExplosion(self.rect.centerx, self.rect.centery,
                                   t.damage, t.wind_knockback, self.game)
                self.game.wind_explosions.append(exp)
                self.wind_mark_tower = None
            self.kill()
            return self.reward
        return 0

    def draw_health_bar(self, screen):
        if self.health <= 0:
            return

        bar_width = TILE_SIZE - 4
        bar_height = 6
        bar_x = self.rect.x + 2
        bar_y = self.rect.y - 12

        pygame.draw.rect(screen, (60, 60, 60), (bar_x, bar_y, bar_width, bar_height))
        fill_w = int(bar_width * (self.health / self.max_health))
        pygame.draw.rect(screen, (0, 220, 0), (bar_x, bar_y, fill_w, bar_height))

        active_buffs = self.get_active_buffs()
        buff_start_x = bar_x
        buff_draw_y = bar_y - assets.BUFF_SIZE - 4
        for buff_key in active_buffs:
            icon = assets.buff_icons[buff_key]
            screen.blit(icon, (buff_start_x, buff_draw_y))
            buff_start_x += assets.BUFF_SIZE


class DamageText(pygame.sprite.Sprite):
    def __init__(self, text, x, y, color=RED, duration=45, speed_y=-2, scale=1.0):
        super().__init__()
        self.text = str(text)
        self.color = color
        self.duration = duration
        self.timer = 0
        self.speed_y = speed_y
        self.pos_x = float(x)
        self.pos_y = float(y)

        self.base_image = assets.font_damage.render(self.text, True, self.color)
        new_w = int(self.base_image.get_width() * scale)
        new_h = int(self.base_image.get_height() * scale)
        self.base_image = pygame.transform.smoothscale(self.base_image, (new_w, new_h))

        self.image = self.base_image.copy()
        self.rect = self.image.get_rect(center=(int(self.pos_x), int(self.pos_y)))

    def update(self):
        self.timer += 1
        self.pos_y += self.speed_y
        self.rect.center = (int(self.pos_x), int(self.pos_y))

        if (
            self.rect.right < 0 or
            self.rect.left > SCREEN_WIDTH or
            self.rect.bottom < 0 or
            self.rect.top > SCREEN_HEIGHT
        ):
            self.kill()
            return

        alpha = max(0, 255 - int(255 * self.timer / self.duration))
        self.image = self.base_image.copy()
        self.image.set_alpha(alpha)

        if self.timer >= self.duration:
            self.kill()
