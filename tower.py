import pygame
import random
import assets
from config import *


class Tower(pygame.sprite.Sprite):
    def __init__(self, tower_type, x, y, game):
        super().__init__()
        self.type = tower_type
        self.x = x
        self.y = y
        self.level = 1
        self.range = 0
        self.damage = 0
        self.fire_rate = 0
        self.cost = 0
        self.upgrade_cost = 0
        self.last_shot = 0
        self.target = None
        self.game = game

        self.teleport_chance = 0.06
        self.penetrate = False
        self.freeze_time = 0
        self.oneshot_chance = 0
        self.stun_time = 0

        self.lightning_damage = 0
        self.execute_threshold = 0
        self.wind_knockback = 0

        self.dragon_breath_cooldown = 0

        self.setup_tower()
        self.update_sprite()

        self.rect = self.image.get_rect()
        self.rect.topleft = (x * TILE_SIZE, y * TILE_SIZE)
        self.is_production = (self.type == TowerType.PRODUCTION)

    def setup_tower(self):
        if self.type == TowerType.PHYSICAL:
            self.range = TILE_SIZE * 3
            self.damage = 20
            self.fire_rate = 60
            self.cost = 100
            self.upgrade_cost = 150
        elif self.type == TowerType.PRODUCTION:
            self.range = 0
            self.damage = 0
            self.fire_rate = 0
            self.cost = 50
            self.upgrade_cost = 75
        elif self.type == TowerType.ICE:
            self.range = TILE_SIZE * 1.5
            self.damage = 5
            self.fire_rate = 60
            self.cost = 150
            self.upgrade_cost = 225
        elif self.type == TowerType.TELEPORT:
            self.range = TILE_SIZE * 1.5
            self.damage = 5
            self.fire_rate = 60
            self.cost = 300
            self.upgrade_cost = 450
        elif self.type == TowerType.FLAME:
            self.range = TILE_SIZE * 1.5
            self.damage = 20
            self.fire_rate = 60
            self.cost = 200
            self.upgrade_cost = 300
        elif self.type == TowerType.TRIDENT:
            self.range = TILE_SIZE * 2
            self.damage = 50
            self.fire_rate = 60
            self.cost = 400
            self.upgrade_cost = 600
            self.lightning_damage = 100
        elif self.type == TowerType.WIND:
            self.range = int(TILE_SIZE * 1.5)
            self.damage = 5
            self.fire_rate = 60
            self.cost = 250
            self.upgrade_cost = 375
            self.wind_knockback = 12

    def upgrade(self):
        if self.level >= 15:
            return
        self.level += 1
        self.upgrade_cost = int(self.upgrade_cost * 1.5)
        if self.type == TowerType.PRODUCTION:
            self.game.gold_per_second += 1
            if self.level >= 6: self.game.gold_per_wave += 1
            if self.level >= 11: self.game.gold_profit_per_wave += 0.01
        if self.type == TowerType.PHYSICAL:
            self.damage += 15
            self.range += TILE_SIZE // 2
            self.fire_rate = max(30, self.fire_rate - 6)
        elif self.type == TowerType.ICE:
            self.damage += 5
            self.range += TILE_SIZE // 4
            self.fire_rate = max(30, self.fire_rate - 6)
            if self.level >= 6: self.freeze_time = round(self.freeze_time + 0.1, 1)
        elif self.type == TowerType.TELEPORT:
            self.damage += 5
            self.teleport_chance += 0.01
            self.range += TILE_SIZE // 4
            self.fire_rate = max(30, self.fire_rate - 6)
            if self.level >= 6: self.oneshot_chance += 0.01
            if self.level >= 11:
                self.execute_threshold = min(10, 6 + (self.level - 11))
        elif self.type == TowerType.FLAME:
            self.damage += 15
            self.range += TILE_SIZE // 4
            self.fire_rate = max(30, self.fire_rate - 6)
            if self.level >= 6: self.stun_time = round(self.stun_time + 0.1, 1)
        elif self.type == TowerType.TRIDENT:
            self.damage += 25
            self.range += TILE_SIZE // 2
            self.fire_rate = max(30, self.fire_rate - 6)
            self.lightning_damage += 50
        elif self.type == TowerType.WIND:
            self.wind_knockback += 12
            self.fire_rate = max(30, self.fire_rate - 6)
            if self.level >= 6:
                self.damage += 20
                self.range += TILE_SIZE // 2
            else:
                self.damage += 5
                self.range += TILE_SIZE // 4

        self.update_sprite()

    def update_sprite(self):
        prefix = str(self.type.value + 1)
        if self.level >= 11:
            img = f"tower/{prefix}{prefix}{prefix}.png"
        elif self.level >= 6:
            img = f"tower/{prefix}{prefix}.png"
        else:
            img = f"tower/{prefix}.png"

        self.image = assets.load_image(img, (TILE_SIZE, TILE_SIZE))
        self.rect = self.image.get_rect()
        self.rect.topleft = (self.x * TILE_SIZE, self.y * TILE_SIZE)

    def can_attack(self, current_time):
        return current_time - self.last_shot >= self.fire_rate

    def get_effective_range(self):
        r = self.range
        if self.game.weather == Weather.TAILWIND:
            r += int(self.range * 0.5)
        if self.game.weather == Weather.HEADWIND:
            r -= int(self.range * 0.5)
        return r

    def attack(self, current_time):
        if not self.can_attack(current_time):
            return []
        self.last_shot = current_time

        directions = [(0, -1), (0, 1), (-1, 0), (1, 0)]
        bullets = []
        for dx, dy in directions:
            bullet = Bullet(
                self.rect.centerx, self.rect.centery,
                dx, dy, self.get_effective_range(),
                self.damage, self.type, self.game,
                self.teleport_chance, self.penetrate,
                self.freeze_time, self.oneshot_chance, self.stun_time,
                self.game.enemies, self.level)
            bullet.lightning_damage = self.lightning_damage
            bullet.execute_threshold = self.execute_threshold
            bullet.source_tower = self
            bullets.append(bullet)
        return bullets

    def draw_range(self, surface):
        if self.type != TowerType.PRODUCTION:
            pygame.draw.circle(surface, (255, 255, 255, 50), self.rect.center, self.get_effective_range(), 2)


class Bullet(pygame.sprite.Sprite):
    def __init__(self, x, y, dx, dy, max_distance, damage, tower_type, game,
                 teleport_chance=0, penetrate=False,
                 freeze_time=0, oneshot_chance=0, stun_time=0, enemies=None, tower_level=1):
        super().__init__()
        self.x = x
        self.y = y
        self.dx = dx
        self.dy = dy
        self.speed = 12
        self.max_distance = max_distance
        self.traveled = 0

        self.damage = damage
        self.tower_type = tower_type
        self.game = game
        self.teleport_chance = teleport_chance
        self.penetrate = penetrate
        self.freeze_time = freeze_time
        self.oneshot_chance = oneshot_chance
        self.stun_time = stun_time
        self.enemies = enemies
        self.tower_level = tower_level

        self.lightning_damage = 0
        self.execute_threshold = 0
        self.source_tower = None

        prefix = str(self.tower_type.value + 1)
        if self.tower_level >= 11:
            img = f"tower/{prefix}{prefix}{prefix}.png"
        elif self.tower_level >= 6:
            img = f"tower/{prefix}{prefix}.png"
        else:
            img = f"tower/{prefix}.png"

        self.raw_img = assets.load_image(img, (TILE_SIZE // 2, TILE_SIZE // 2))

        if self.dx == 1 and self.dy == 0:
            rotate_angle = -45
        elif self.dx == 0 and self.dy == -1:
            rotate_angle = -315
        elif self.dx == -1 and self.dy == 0:
            rotate_angle = -225
        elif self.dx == 0 and self.dy == 1:
            rotate_angle = -135
        else:
            rotate_angle = 0

        self.image = pygame.transform.rotate(self.raw_img, rotate_angle)
        self.rect = self.image.get_rect(center=(x, y))

    def calculate_final_damage(self):
        dmg = self.damage
        if self.tower_type == TowerType.PHYSICAL and self.tower_level >= 6:
            dmg += int(self.game.coins * 0.01)

        if self.tower_type == TowerType.TRIDENT:
            if self.tower_level >= 6:
                gold_bonus = int(self.game.coins * 0.01)
                dmg += gold_bonus
            if self.tower_level >= 11:
                w = self.game.weather
                if w in (Weather.RAINY, Weather.THUNDERSTORM, Weather.ACID_RAIN):
                    mults = {11: 2, 12: 3, 13: 5, 14: 8, 15: 10}
                    dmg *= mults.get(self.tower_level, 1)

        if self.tower_type == TowerType.WIND:
            if self.tower_level >= 11:
                per_px = {11: 8, 12: 10, 13: 12, 14: 14, 15: 16}
                dmg = int(self.traveled * per_px.get(self.tower_level, 8))

        return int(dmg)

    def calculate_lightning_damage(self):
        ldmg = self.lightning_damage
        if self.tower_type == TowerType.TRIDENT:
            if self.tower_level >= 6:
                gold_bonus = int(self.game.coins * 0.01)
                ldmg += gold_bonus
            if self.tower_level >= 11:
                w = self.game.weather
                if w in (Weather.RAINY, Weather.THUNDERSTORM, Weather.ACID_RAIN):
                    mults = {11: 2, 12: 3, 13: 5, 14: 8, 15: 10}
                    ldmg *= mults.get(self.tower_level, 1)
        return int(ldmg)

    def update(self):
        self.x += self.dx * self.speed
        self.y += self.dy * self.speed
        self.traveled += self.speed
        self.rect.center = (self.x, self.y)

        if self.traveled >= self.max_distance:
            self.kill()
            return

        for enemy in self.enemies:
            if self.rect.colliderect(enemy.rect):
                self.on_hit(enemy)
                return

    def get_damage_color(self):
        if self.tower_type == TowerType.PHYSICAL:
            return WHITE
        elif self.tower_type == TowerType.ICE:
            return ICE_BLUE
        elif self.tower_type == TowerType.TELEPORT:
            return WHITE
        elif self.tower_type == TowerType.FLAME:
            return YELLOW
        elif self.tower_type == TowerType.TRIDENT:
            return GOLD
        elif self.tower_type == TowerType.WIND:
            return MINT
        return RED

    def on_hit(self, enemy):
        final_dmg = self.calculate_final_damage()

        if self.tower_type == TowerType.ICE and self.tower_level >= 11 and enemy.freeze_time > 0:
            bonus = 300 + 150 * (self.tower_level - 11)
            final_dmg += bonus

        if self.tower_type == TowerType.TELEPORT and self.tower_level >= 11 and self.execute_threshold > 0:
            threshold_ratio = self.execute_threshold / 100.0
            if enemy.health <= enemy.max_health * threshold_ratio:
                reward = enemy.take_damage(9999999, color=RED, scale=1.2)
                self.game.coins += reward
                self.game.score += reward
                self.kill()
                return

        color = self.get_damage_color()
        reward = enemy.take_damage(final_dmg, color=color)
        self.game.coins += reward
        self.game.score += reward
        self.apply_effects(enemy)
        self.kill()

    def apply_effects(self, enemy):
        if self.tower_type == TowerType.ICE:
            rain_weathers = (Weather.RAINY, Weather.THUNDERSTORM, Weather.ACID_RAIN, Weather.EXTREME_COLD)
            if self.game.weather not in rain_weathers:
                enemy.apply_slow(0.5, 60)
            freeze_frames = int(self.freeze_time * 60)
            if self.game.weather == Weather.SNOWY:
                freeze_frames = int(freeze_frames * 1.5)
            if self.game.weather == Weather.EXTREME_COLD:
                freeze_frames = int(freeze_frames * 2)
            enemy.apply_freeze(freeze_frames)
            if self.tower_level >= 11:
                freeze_frames_for_exp = freeze_frames
                if self.freeze_time <= 0:
                    freeze_frames_for_exp = 60
                exp = IceExplosion(enemy.rect.centerx, enemy.rect.centery, freeze_frames_for_exp, self.game)
                self.game.ice_explosions.append(exp)
        if self.tower_type == TowerType.TELEPORT:
            if random.random() < self.teleport_chance:
                enemy.teleport_to_start()
            if random.random() < self.oneshot_chance:
                reward = enemy.take_damage(9999999, color=RED, scale=1.2)
                self.game.coins += reward
                self.game.score += reward
        if self.tower_type == TowerType.FLAME:
            burn_dmg = self.game.temperature
            enemy.apply_burn(burn_dmg, 240)
            if self.tower_level >= 6:
                enemy.apply_stun(int(self.stun_time * 60))
            if self.tower_level >= 11:
                self.game.add_dragon_breath(
                    enemy.rect.centerx, enemy.rect.centery,
                    self.game.temperature, self.tower_level, self.stun_time)
        if self.tower_type == TowerType.PHYSICAL:
            if self.tower_level >= 11 and not enemy.broken:
                enemy.broken = True
        if self.tower_type == TowerType.TRIDENT:
            col = enemy.rect.centerx // TILE_SIZE
            lightning_dmg = self.calculate_lightning_damage()
            for e in self.game.enemies:
                e_col = e.rect.centerx // TILE_SIZE
                if e_col == col and e.health > 0:
                    reward = e.take_damage(lightning_dmg, color=GOLD)
                    self.game.coins += reward
                    self.game.score += reward
                    e.apply_burn(self.game.temperature, 240)
            is_golden = False
            if self.tower_level >= 6:
                is_golden = True
            if self.tower_level >= 11:
                w = self.game.weather
                is_golden = (w == Weather.SUNNY or w == Weather.EXTREME_HEAT)
            self.game.add_lightning(enemy.rect.centerx, 800, is_golden)
        if self.tower_type == TowerType.WIND:
            if self.source_tower:
                enemy.apply_knockback(self.source_tower.wind_knockback)
                if self.tower_level >= 6:
                    enemy.wind_mark_tower = self.source_tower
                if self.tower_level >= 11:
                    stun_frames = {11: 6, 12: 12, 13: 18, 14: 24, 15: 30}
                    enemy.apply_stun(stun_frames.get(self.tower_level, 6))


class WindExplosion:
    def __init__(self, x, y, damage, knockback, game):
        self.x = x
        self.y = y
        self.duration = 6
        self.radius = 128
        for enemy in game.enemies:
            if enemy.health <= 0:
                continue
            dx = enemy.rect.centerx - x
            dy = enemy.rect.centery - y
            if (dx * dx + dy * dy) <= self.radius * self.radius:
                reward = enemy.take_damage(damage, color=MINT, scale=0.8)
                game.coins += reward
                game.score += reward
                enemy.apply_knockback(knockback)

    def update(self):
        self.duration -= 1
        return self.duration > 0

    def draw(self, screen):
        alpha = int(80 * self.duration / 6)
        s = pygame.Surface((self.radius * 2, self.radius * 2), pygame.SRCALPHA)
        pygame.draw.circle(s, (152, 255, 152, alpha), (self.radius, self.radius), self.radius)
        screen.blit(s, (self.x - self.radius, self.y - self.radius))


class IceExplosion:
    def __init__(self, x, y, freeze_time, game):
        self.x = x
        self.y = y
        self.duration = 6
        self.radius = 128
        for enemy in game.enemies:
            if enemy.health <= 0:
                continue
            dx = enemy.rect.centerx - x
            dy = enemy.rect.centery - y
            if (dx * dx + dy * dy) <= self.radius * self.radius:
                enemy.apply_freeze(freeze_time)

    def update(self):
        self.duration -= 1
        return self.duration > 0

    def draw(self, screen):
        alpha = int(80 * self.duration / 6)
        s = pygame.Surface((self.radius * 2, self.radius * 2), pygame.SRCALPHA)
        pygame.draw.circle(s, (100, 150, 255, alpha), (self.radius, self.radius), self.radius)
        screen.blit(s, (self.x - self.radius, self.y - self.radius))


class DragonBreathPool:
    def __init__(self, x, y, temperature, tower_level, stun_time, game):
        self.x = x
        self.y = y
        self.radius = 128
        self.duration = 10
        dmg_mult = (tower_level - 10) ** 2
        dmg = int(temperature * dmg_mult)
        for enemy in game.enemies:
            if enemy.health <= 0:
                continue
            dx = enemy.rect.centerx - self.x
            dy = enemy.rect.centery - self.y
            if (dx * dx + dy * dy) <= self.radius * self.radius:
                reward = enemy.take_damage(dmg, color=PURPLE, scale=0.7)
                game.coins += reward
                game.score += reward
                if stun_time > 0:
                    enemy.apply_stun(int(stun_time * 60))

    def update(self, game_time):
        self.duration -= 1
        return self.duration > 0

    def draw(self, screen):
        alpha = min(80, int(80 * self.duration / 10))
        s = pygame.Surface((self.radius * 2, self.radius * 2), pygame.SRCALPHA)
        pygame.draw.circle(s, (128, 0, 128, alpha), (self.radius, self.radius), self.radius)
        screen.blit(s, (self.x - self.radius, self.y - self.radius))


class LightningEffect:
    def __init__(self, x, y, is_golden):
        self.x = x
        self.y = y
        self.frame = 0
        self.frame_timer = 0
        self.frame_duration = 4
        self.max_frames = 5
        self.is_golden = is_golden
        self.done = False

    def update(self):
        if self.done:
            return
        self.frame_timer += 1
        if self.frame_timer >= self.frame_duration:
            self.frame_timer = 0
            self.frame += 1
            if self.frame >= self.max_frames:
                self.done = True

    def draw(self, screen):
        if self.done:
            return
        frames = assets.golden_lightning_frames if self.is_golden else assets.white_lightning_frames
        if frames and self.frame < len(frames):
            img = frames[self.frame]
            rect = img.get_rect(center=(self.x, self.y))
            screen.blit(img, rect)
