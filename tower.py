import pygame
import random
import assets
from config import *

MAP_CENTER_X = GRID_WIDTH * TILE_SIZE // 2
MAP_CENTER_Y = (1 + GRID_HEIGHT) * TILE_SIZE // 2


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

        self.teleport_chance = 0.01
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
        elif self.type == TowerType.POISON:
            self.range = TILE_SIZE * 3
            self.damage = 20
            self.fire_rate = 60
            self.cost = 175
            self.upgrade_cost = int(175 * 1.5)
        elif self.type == TowerType.BOMB:
            self.range = int(TILE_SIZE * 2.2)
            self.damage = 100
            self.fire_rate = 120
            self.cost = 500
            self.upgrade_cost = 750
            self.bomb_subtype = BombSubType.SNOW
            self.is_nuclear = False
        elif self.type == TowerType.WITHER:
            self.range = TILE_SIZE * 3
            self.damage = 20
            self.fire_rate = 60
            self.cost = 175
            self.upgrade_cost = int(175 * 1.5)

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
        elif self.type == TowerType.POISON:
            self.damage += 15
            self.range += TILE_SIZE // 2
            self.fire_rate = max(30, self.fire_rate - 6)
        elif self.type == TowerType.BOMB:
            self.damage += 100
            self.range += int(TILE_SIZE * 0.2)
            self.fire_rate = 120
            if self.level >= 11:
                self.is_nuclear = True
                self.range = 0
                self.fire_rate = 1200
        elif self.type == TowerType.WITHER:
            self.damage += 15
            self.range += TILE_SIZE // 2
            self.fire_rate = max(30, self.fire_rate - 6)

        self.update_sprite()

    def update_sprite(self):
        if self.type == TowerType.BOMB:
            if self.level >= 11:
                img = "tower/999.png"
            elif self.level >= 6:
                sub_map = {BombSubType.SNOW: "91", BombSubType.ICE: "92", BombSubType.FLAME: "93", BombSubType.POISON: "94", BombSubType.WITHER_TNT: "95"}
                img = f"tower/{sub_map[self.bomb_subtype]}.png"
            else:
                img = "tower/9.png"
        elif self.type == TowerType.WITHER:
            if self.level >= 11:
                img = "tower/000.png"
            elif self.level >= 6:
                img = "tower/00.png"
            else:
                img = "tower/0.png"
        else:
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

        if self.type == TowerType.PRODUCTION:
            return []

        if self.type == TowerType.BOMB and self.is_nuclear:
            if self.game.enemies:
                missile = NuclearMissile(self.rect.centerx, self.rect.centery,
                                         MAP_CENTER_X, MAP_CENTER_Y,
                                         self.damage, self.level, self.game)
                return [missile]
            return []

        check_range = self.get_effective_range() + TILE_SIZE // 2
        tc = self.rect.centerx // TILE_SIZE
        tr = self.rect.centery // TILE_SIZE
        cr = int(check_range // TILE_SIZE) + 1
        has_target = False
        grid = self.game.enemy_grid
        for dc in range(-cr, cr + 1):
            for dr in range(-cr, cr + 1):
                for e in grid.get((tc + dc, tr + dr), ()):
                    dx = e.rect.centerx - self.rect.centerx
                    dy = e.rect.centery - self.rect.centery
                    if (dx * dx + dy * dy) <= check_range * check_range:
                        has_target = True
                        break
                if has_target:
                    break
            if has_target:
                break
        if not has_target:
            return []

        if self.type == TowerType.WITHER:
            directions = [(0, -1), (0, 1), (-1, 0), (1, 0)]
            bullets = []
            for dx, dy in directions:
                bullet = WitherBullet(
                    self.rect.centerx, self.rect.centery,
                    dx, dy, self.get_effective_range(),
                    self.damage, self.level, self.game)
                bullets.append(bullet)
            return bullets

        if self.type == TowerType.BOMB:
            directions = [(0, -1), (0, 1), (-1, 0), (1, 0)]
            bullets = []
            for dx, dy in directions:
                bullet = BombBullet(
                    self.rect.centerx, self.rect.centery,
                    dx, dy, self.get_effective_range(),
                    self.damage, self.level,
                    self.bomb_subtype if not self.is_nuclear else None,
                    self.game)
                bullets.append(bullet)
            return bullets
            return []

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
            if self.type == TowerType.POISON:
                if self.level >= 11:
                    bullet.poison_stacks = self.level * 4
                else:
                    bullet.poison_stacks = self.level
            bullets.append(bullet)
        return bullets

    def draw_range(self, surface):
        if self.type != TowerType.PRODUCTION and not (self.type == TowerType.BOMB and self.is_nuclear):
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
        self.poison_stacks = 0

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
        if self.game.weather == Weather.MAGNETIC_STORM:
            ldmg *= 2
        return int(ldmg)

    def update(self):
        self.x += self.dx * self.speed
        self.y += self.dy * self.speed
        self.traveled += self.speed
        self.rect.center = (self.x, self.y)

        if self.traveled >= self.max_distance:
            self.kill()
            return

        col = int(self.x) // TILE_SIZE
        row = int(self.y) // TILE_SIZE
        grid = self.game.enemy_grid
        for dc in (-1, 0, 1):
            for dr in (-1, 0, 1):
                for enemy in grid.get((col + dc, row + dr), ()):
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
        elif self.tower_type == TowerType.POISON:
            return GREEN
        return RED

    def on_hit(self, enemy):
        final_dmg = self.calculate_final_damage()

        if self.tower_type == TowerType.ICE and self.tower_level >= 11 and enemy.freeze_time > 0:
            bonus = int(self.game.temperature * 3 * (self.tower_level - 10))
            final_dmg += bonus

        if self.tower_type == TowerType.TELEPORT and self.tower_level >= 11:
            hp_ratios = {11: 0.01, 12: 0.0125, 13: 0.015, 14: 0.0175, 15: 0.02}
            hp_bonus = int(enemy.max_health * hp_ratios.get(self.tower_level, 0))
            final_dmg += hp_bonus

        if enemy.enemy_type in (EnemyType.GOLD_ARMORED, EnemyType.ENDLESS_ARMORED) and self.tower_level >= 6:
            if self.tower_type in (TowerType.PHYSICAL, TowerType.TRIDENT):
                final_dmg = self.damage

        if self.tower_type == TowerType.TELEPORT and self.tower_level >= 11 and self.execute_threshold > 0:
            threshold_ratio = self.execute_threshold / 100.0
            if enemy.health <= enemy.max_health * threshold_ratio:
                reward = enemy.take_damage(9999999, color=RED, scale=1.2)
                self.game.coins += reward
                self.kill()
                return

        color = self.get_damage_color()
        reward = enemy.take_damage(final_dmg, color=color)
        self.game.coins += reward
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
                exp = IceExplosion(enemy.rect.centerx, enemy.rect.centery, self.damage, freeze_frames_for_exp, self.game)
                self.game.ice_explosions.append(exp)
        if self.tower_type == TowerType.TELEPORT:
            if self.game.weather != Weather.MAGNETIC_STORM and random.random() < self.teleport_chance:
                enemy.teleport_to_start()
                if assets.teleport_sound:
                    assets.teleport_sound.play()
            if random.random() < self.oneshot_chance:
                reward = enemy.take_damage(9999999, color=RED, scale=1.2)
                self.game.coins += reward
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
            gold_bonus = int(self.game.coins * 0.01) if self.tower_level >= 6 else 0
            for e in self.game.enemies:
                e_col = e.rect.centerx // TILE_SIZE
                if e_col == col and e.health > 0:
                    dmg = lightning_dmg
                    if e.enemy_type in (EnemyType.GOLD_ARMORED, EnemyType.ENDLESS_ARMORED):
                        dmg = self.lightning_damage
                    reward = e.take_damage(dmg, color=GOLD)
                    self.game.coins += reward
                    e.apply_burn(self.game.temperature, 240)
            is_golden = self.tower_level >= 6
            self.game.add_lightning(enemy.rect.centerx, 800, is_golden)
            if self.tower_level >= 11:
                row = enemy.rect.centery // TILE_SIZE
                h_lightning_dmg = self.calculate_lightning_damage()
                for e in self.game.enemies:
                    e_row = e.rect.centery // TILE_SIZE
                    if e_row == row and e.health > 0:
                        dmg = h_lightning_dmg
                        if e.enemy_type in (EnemyType.GOLD_ARMORED, EnemyType.ENDLESS_ARMORED):
                            dmg = self.lightning_damage
                        reward = e.take_damage(dmg, color=GOLD)
                        self.game.coins += reward
                h_effect = HorizontalLightningEffect(1024, row * TILE_SIZE + TILE_SIZE // 2, not is_golden)
                self.game.horizontal_lightning_effects.append(h_effect)
        if self.tower_type == TowerType.WIND:
            if self.source_tower:
                enemy.apply_knockback(self.source_tower.wind_knockback)
                if self.tower_level >= 6 and enemy.enemy_type not in (EnemyType.ARMORED, EnemyType.GOLD_ARMORED, EnemyType.DIAMOND_ARMORED, EnemyType.ENDLESS_ARMORED):
                    enemy.wind_mark_tower = self.source_tower
                if self.tower_level >= 11:
                    stun_frames = {11: 6, 12: 12, 13: 18, 14: 24, 15: 30}
                    enemy.apply_stun(stun_frames.get(self.tower_level, 6))
        if self.tower_type == TowerType.POISON and self.poison_stacks > 0:
            enemy.apply_poison(self.poison_stacks)
            if self.tower_level >= 6:
                splash = PoisonSplash(enemy.rect.centerx, enemy.rect.centery, self.damage, self.poison_stacks, self.game)
                self.game.poison_splashes.append(splash)


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
    def __init__(self, x, y, damage, freeze_time, game):
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
                reward = enemy.take_damage(damage, color=ICE_BLUE, scale=0.8)
                game.coins += reward
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
        dmg_mult = (tower_level - 10) * 10
        dmg = int(temperature * dmg_mult)
        for enemy in game.enemies:
            if enemy.health <= 0:
                continue
            dx = enemy.rect.centerx - self.x
            dy = enemy.rect.centery - self.y
            if (dx * dx + dy * dy) <= self.radius * self.radius:
                reward = enemy.take_damage(dmg, color=PURPLE, scale=0.7)
                game.coins += reward
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


class HorizontalLightningEffect:
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
        frames = assets.golden_lightning_h_frames if self.is_golden else assets.white_lightning_h_frames
        if frames and self.frame < len(frames):
            img = frames[self.frame]
            rect = img.get_rect(center=(self.x, self.y))
            screen.blit(img, rect)


class PoisonSplash:
    def __init__(self, x, y, damage, stacks, game):
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
                reward = enemy.take_damage(damage, color=GREEN, scale=0.8)
                game.coins += reward
                enemy.apply_poison(stacks)

    def update(self):
        self.duration -= 1
        return self.duration > 0

    def draw(self, screen):
        alpha = int(80 * self.duration / 6)
        s = pygame.Surface((self.radius * 2, self.radius * 2), pygame.SRCALPHA)
        pygame.draw.circle(s, (0, 255, 0, alpha), (self.radius, self.radius), self.radius)
        screen.blit(s, (self.x - self.radius, self.y - self.radius))


class BombBullet(pygame.sprite.Sprite):
    def __init__(self, x, y, dx, dy, max_distance, damage, tower_level, bomb_subtype, game):
        super().__init__()
        self.x = x
        self.y = y
        self.dx = dx
        self.dy = dy
        self.speed = 12
        self.max_distance = max_distance
        self.traveled = 0
        self.damage = damage
        self.tower_level = tower_level
        self.bomb_subtype = bomb_subtype
        self.game = game
        self.enemies = game.enemies

        if tower_level >= 11:
            img = "tower/999.png"
        elif tower_level >= 6:
            sub_map = {BombSubType.SNOW: "91", BombSubType.ICE: "92", BombSubType.FLAME: "93", BombSubType.POISON: "94", BombSubType.WITHER_TNT: "95"}
            img = f"tower/{sub_map[bomb_subtype]}.png"
        else:
            img = "tower/9.png"
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

    def update(self):
        self.x += self.dx * self.speed
        self.y += self.dy * self.speed
        self.traveled += self.speed
        self.rect.center = (self.x, self.y)

        if self.traveled >= self.max_distance:
            self.kill()
            return

        col = int(self.x) // TILE_SIZE
        row = int(self.y) // TILE_SIZE
        grid = self.game.enemy_grid
        for dc in (-1, 0, 1):
            for dr in (-1, 0, 1):
                for enemy in grid.get((col + dc, row + dr), ()):
                    if self.rect.colliderect(enemy.rect):
                        self.explode()
                        self.kill()
                        return

    def explode(self):
        explosion = TNTExplosion(self.rect.centerx, self.rect.centery,
                                 self.damage, self.tower_level, self.bomb_subtype, self.game)
        self.game.tnt_explosions.append(explosion)


class TNTExplosion:
    def __init__(self, x, y, damage, tower_level, bomb_subtype, game):
        self.x = x
        self.y = y
        self.damage = damage
        self.tower_level = tower_level
        self.bomb_subtype = bomb_subtype
        self.game = game
        self.frame = 0
        self.frame_timer = 0
        self.frame_duration = 6
        self.max_frames = 5
        self.done = False

        radius_px = TILE_SIZE * 2
        for enemy in game.enemies:
            if enemy.health <= 0:
                continue
            dx = enemy.rect.centerx - x
            dy = enemy.rect.centery - y
            if (dx * dx + dy * dy) <= radius_px * radius_px:
                reward = enemy.take_damage(damage, color=RED, scale=1.0)
                game.coins += reward
                if bomb_subtype is not None:
                    if bomb_subtype == BombSubType.SNOW:
                        enemy.apply_slow(0.5, 720)
                    elif bomb_subtype == BombSubType.ICE:
                        freeze_s = {6: 0.6, 7: 0.7, 8: 0.8, 9: 0.9, 10: 1.0}
                        enemy.apply_freeze(int(freeze_s.get(tower_level, 0.6) * 60))
                    elif bomb_subtype == BombSubType.FLAME:
                        enemy.apply_burn(game.temperature, 480)
                    elif bomb_subtype == BombSubType.POISON:
                        stacks = {6: 12, 7: 14, 8: 16, 9: 18, 10: 20}
                        enemy.apply_poison(stacks.get(tower_level, 12))
                    elif bomb_subtype == BombSubType.WITHER_TNT:
                        enemy.apply_wither(300)

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
        if self.done or self.frame >= len(assets.tnt_explosion_frames):
            return
        img = assets.tnt_explosion_frames[self.frame]
        rect = img.get_rect(center=(self.x, self.y))
        screen.blit(img, rect)


class NuclearMissile(pygame.sprite.Sprite):
    def __init__(self, x, y, target_x, target_y, damage, tower_level, game):
        super().__init__()
        self.x = x
        self.y = y
        self.target_x = target_x
        self.target_y = target_y
        self.speed = 8
        self.damage = damage
        self.tower_level = tower_level
        self.game = game
        self.raw_img = assets.load_image("tower/999.png", (TILE_SIZE // 2, TILE_SIZE // 2))
        self.image = self.raw_img
        self.rect = self.image.get_rect(center=(x, y))

    def update(self):
        dx = self.target_x - self.x
        dy = self.target_y - self.y
        dist = (dx * dx + dy * dy) ** 0.5
        if dist < self.speed:
            explosion = MushroomExplosion(MAP_CENTER_X, MAP_CENTER_Y,
                                          self.damage, self.tower_level, self.game)
            self.game.mushroom_explosions.append(explosion)
            shockwave = NuclearShockwave(MAP_CENTER_X, MAP_CENTER_Y, self.game)
            self.game.shockwave_effects.append(shockwave)
            self.kill()
            return
        self.x += (dx / dist) * self.speed
        self.y += (dy / dist) * self.speed
        self.rect.center = (self.x, self.y)


class MushroomExplosion:
    def __init__(self, x, y, damage, tower_level, game):
        self.x = x
        self.y = y
        self.damage = damage
        self.tower_level = tower_level
        self.game = game
        self.frame = 0
        self.frame_timer = 0
        self.frame_duration = 3
        self.max_frames = 10
        self.done = False

        if assets.explode_sound:
            assets.explode_sound.play()

        final_damage = (20000 + 100 * game.temperature) * (tower_level - 10)
        for enemy in game.enemies:
            if enemy.health <= 0:
                continue
            reward = enemy.take_damage(final_damage, color=RED, scale=1.2)
            game.coins += reward
            enemy.apply_stun(120)
            enemy.apply_poison(tower_level * 10)

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
        if self.done or self.frame >= len(assets.mushroom_cloud_frames):
            return
        img = assets.mushroom_cloud_frames[self.frame]
        rect = img.get_rect(center=(self.x, self.y))
        screen.blit(img, rect)


class NuclearShockwave:
    def __init__(self, x, y, game):
        self.x = x
        self.y = y
        self.game = game
        self.radius = 0
        self.max_radius = int(SCREEN_WIDTH * 0.75)
        self.duration = 45
        self.timer = 0
        self.done = False

    def update(self):
        if self.done:
            return
        self.timer += 1
        self.radius = int(self.max_radius * (self.timer / self.duration))
        if self.timer >= self.duration:
            self.done = True

    def draw(self, screen):
        if self.done:
            return
        alpha = max(0, 120 - int(120 * self.timer / self.duration))
        color = (255, 0, 0, alpha)
        s = pygame.Surface((self.radius * 2, self.radius * 2), pygame.SRCALPHA)
        pygame.draw.circle(s, color, (self.radius, self.radius), self.radius)
        screen.blit(s, (self.x - self.radius, self.y - self.radius))


class WitherBullet(pygame.sprite.Sprite):
    def __init__(self, x, y, dx, dy, max_distance, damage, tower_level, game):
        super().__init__()
        self.x = x
        self.y = y
        self.dx = dx
        self.dy = dy
        self.speed = 12
        self.max_distance = max_distance
        self.traveled = 0
        self.damage = damage
        self.tower_level = tower_level
        self.game = game
        self.enemies = game.enemies

        if tower_level >= 11:
            img = "tower/000.png"
        elif tower_level >= 6:
            img = "tower/00.png"
        else:
            img = "tower/0.png"
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

    def update(self):
        self.x += self.dx * self.speed
        self.y += self.dy * self.speed
        self.traveled += self.speed
        self.rect.center = (self.x, self.y)

        if self.traveled >= self.max_distance:
            self.kill()
            return

        col = int(self.x) // TILE_SIZE
        row = int(self.y) // TILE_SIZE
        grid = self.game.enemy_grid
        for dc in (-1, 0, 1):
            for dr in (-1, 0, 1):
                for enemy in grid.get((col + dc, row + dr), ()):
                    if self.rect.colliderect(enemy.rect):
                        self.on_hit(enemy)
                        return

    def on_hit(self, enemy):
        if self.tower_level >= 11:
            wither_duration = 720
        else:
            wither_duration = 300
        final_dmg = self.damage

        reward = enemy.take_damage(final_dmg, color=(100, 0, 100))
        self.game.coins += reward

        if self.tower_level >= 6:
            splash = WitherSplash(self.rect.centerx, self.rect.centery, final_dmg, wither_duration, self.game)
            self.game.wither_splashes.append(splash)
        else:
            enemy.apply_wither(wither_duration)

        self.kill()


class WitherSplash:
    def __init__(self, x, y, damage, wither_duration, game):
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
                reward = enemy.take_damage(damage, color=(100, 0, 100), scale=0.8)
                game.coins += reward
                enemy.apply_wither(wither_duration)

    def update(self):
        self.duration -= 1
        return self.duration > 0

    def draw(self, screen):
        alpha = int(80 * self.duration / 6)
        s = pygame.Surface((self.radius * 2, self.radius * 2), pygame.SRCALPHA)
        pygame.draw.circle(s, (0, 0, 0, alpha), (self.radius, self.radius), self.radius)
        screen.blit(s, (self.x - self.radius, self.y - self.radius))
