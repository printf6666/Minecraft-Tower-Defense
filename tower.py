import pygame
import random
import math
import assets
from config import *
from effects import WindExplosion, IceExplosion, DragonBreathPool, LightningEffect, HorizontalLightningEffect, PoisonSplash, TNTExplosion, MushroomExplosion, NuclearShockwave, WitherSplash
from dragons import Dragon

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
        self.physical_branch = 1
        self.wind_branch = 1
        self.ice_branch = 1
        self.flame_branch = 1
        self.poison_branch = 1
        self.bomb_branch = 1
        self.trident_branch = 1
        self.update_sprite()

        self.rect = self.image.get_rect()
        self.rect.topleft = (x * TILE_SIZE, y * TILE_SIZE)
        self.is_production = (self.type == TowerType.PRODUCTION)
        self.is_on_gold_ore = (x, y) in self.game.gold_ore_positions

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
            self.poison_branch = 1
        elif self.type == TowerType.BOMB:
            self.range = int(TILE_SIZE * 2.2)
            self.damage = 100
            self.fire_rate = 120
            self.cost = 500
            self.upgrade_cost = 750
            self.bomb_subtype = BombSubType.SNOW
            self.is_nuclear = False

    def upgrade(self):
        if self.level >= 15:
            return
        self.level += 1
        self.upgrade_cost = int(self.upgrade_cost * 1.5)
        if self.type == TowerType.PRODUCTION:
            multiplier = 2 if self.is_on_gold_ore else 1
            self.game.gold_per_second += multiplier
            if self.level >= 6: self.game.gold_per_wave += multiplier
            if self.level >= 11: self.game.gold_profit_per_wave += 0.001 * multiplier
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
                if self.bomb_branch == 2:
                    self.fire_rate = 1200
                else:
                    self.fire_rate = 1200

        self.update_sprite()

    def update_sprite(self):
        if self.type == TowerType.BOMB:
            if self.level >= 11:
                img = f"tower/999-{self.bomb_branch}.png"
            elif self.level >= 6:
                sub_map = {BombSubType.SNOW: "99-1", BombSubType.ICE: "99-2", BombSubType.FLAME: "99-3", BombSubType.POISON: "99-4", BombSubType.WITHER_TNT: "99-5"}
                img = f"tower/{sub_map[self.bomb_subtype]}.png"
            else:
                img = "tower/9-1.png"
        elif self.type == TowerType.POISON:
            if self.level >= 11:
                if self.poison_branch == 3:
                    img = "tower/888-3.png"
                elif self.poison_branch == 2:
                    img = "tower/888-2.png"
                else:
                    img = "tower/888-1.png"
            elif self.level >= 6:
                if self.poison_branch == 2:
                    img = "tower/88-2.png"
                else:
                    img = "tower/88-1.png"
            else:
                if self.poison_branch == 2:
                    img = "tower/8-2.png"
                else:
                    img = "tower/8-1.png"
        elif self.type == TowerType.ICE:
            prefix = str(self.type.value)
            if self.level >= 11:
                if self.ice_branch == 2:
                    img = f"tower/{prefix}{prefix}{prefix}-2.png"
                else:
                    img = f"tower/{prefix}{prefix}{prefix}-1.png"
            elif self.level >= 6:
                img = f"tower/{prefix}{prefix}-1.png"
            else:
                img = f"tower/{prefix}-1.png"
        elif self.type == TowerType.FLAME:
            prefix = str(self.type.value)
            if self.level >= 11:
                if self.flame_branch == 2:
                    img = f"tower/{prefix}{prefix}{prefix}-2.png"
                else:
                    img = f"tower/{prefix}{prefix}{prefix}-1.png"
            elif self.level >= 6:
                img = f"tower/{prefix}{prefix}-1.png"
            else:
                img = f"tower/{prefix}-1.png"
        elif self.type == TowerType.TRIDENT:
            prefix = str(self.type.value)
            if self.level >= 11:
                if self.trident_branch == 2:
                    img = f"tower/{prefix}{prefix}{prefix}-2.png"
                else:
                    img = f"tower/{prefix}{prefix}{prefix}-1.png"
            elif self.level >= 6:
                img = f"tower/{prefix}{prefix}-1.png"
            else:
                img = f"tower/{prefix}-1.png"
        else:
            prefix = str(self.type.value)
            if self.level >= 11:
                if self.type == TowerType.PHYSICAL and self.physical_branch == 2:
                    img = f"tower/{prefix}{prefix}{prefix}-2.png"
                elif self.type == TowerType.WIND and self.wind_branch == 2:
                    img = f"tower/{prefix}{prefix}{prefix}-2.png"
                else:
                    img = f"tower/{prefix}{prefix}{prefix}-1.png"
            elif self.level >= 6:
                img = f"tower/{prefix}{prefix}-1.png"
            else:
                img = f"tower/{prefix}-1.png"
        self.image = assets.load_image(img, (TILE_SIZE, TILE_SIZE))
        self.rect = self.image.get_rect()
        self.rect.topleft = (self.x * TILE_SIZE, self.y * TILE_SIZE)

    def can_attack(self, current_time):
        return current_time - self.last_shot >= self.fire_rate

    def get_effective_range(self):
        if self.type == TowerType.BOMB and self.is_nuclear:
            return 0
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
                                         self.damage, self.level, self.game,
                                         self.bomb_branch)
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

        if self.type == TowerType.POISON and self.poison_branch == 2:
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

        if self.type == TowerType.PHYSICAL and self.physical_branch == 2 and self.level >= 11:
            directions = []
            for i in range(12):
                angle = math.radians(i * 30)
                directions.append((math.cos(angle), math.sin(angle)))
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
                bullet.physical_branch = 2
                bullets.append(bullet)
            return bullets

        directions = [(0, -1), (0, 1), (-1, 0), (1, 0)]
        bullets = []
        for dx, dy in directions:
            bullet = Bullet(
                self.rect.centerx, self.rect.centery,
                dx, dy, self.get_effective_range(),
                self.damage, self.type, self.game,
                self.teleport_chance, self.penetrate,
                self.freeze_time, self.oneshot_chance, self.stun_time,
                self.game.enemies, self.level,
                wind_branch=self.wind_branch,
                ice_branch=self.ice_branch,
                flame_branch=self.flame_branch,
                poison_branch=self.poison_branch,
                trident_branch=self.trident_branch)
            bullet.lightning_damage = self.lightning_damage
            bullet.execute_threshold = self.execute_threshold
            bullet.source_tower = self
            if self.type == TowerType.POISON:
                if self.poison_branch == 3:
                    bullet.poison_stacks = self.level * 9
                elif self.level >= 11:
                    bullet.poison_stacks = self.level * 4
                else:
                    bullet.poison_stacks = self.level
            bullets.append(bullet)

        if self.type == TowerType.ICE and self.level >= 11 and self.ice_branch == 2:
            if random.random() < 0.02:
                dragon = Dragon(self.game.path, "ice", self.level, self.game)
                self.game.dragons.add(dragon)

        if self.type == TowerType.FLAME and self.level >= 11 and self.flame_branch == 2:
            if random.random() < 0.05:
                dragon = Dragon(self.game.path, "fire", self.level, self.game)
                self.game.dragons.add(dragon)

        return bullets

    def draw_range(self, surface):
        if self.type != TowerType.PRODUCTION and not (self.type == TowerType.BOMB and self.is_nuclear):
            pygame.draw.circle(surface, (255, 255, 255, 50), self.rect.center, self.get_effective_range(), 2)


class Bullet(pygame.sprite.Sprite):
    def __init__(self, x, y, dx, dy, max_distance, damage, tower_type, game,
                 teleport_chance=0, penetrate=False,
                 freeze_time=0, oneshot_chance=0, stun_time=0, enemies=None, tower_level=1,
                 wind_branch=1, ice_branch=1, flame_branch=1, poison_branch=1, trident_branch=1):
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
        self.wind_branch = wind_branch
        self.ice_branch = ice_branch
        self.flame_branch = flame_branch
        self.poison_branch = poison_branch
        self.trident_branch = trident_branch

        self.lightning_damage = 0
        self.execute_threshold = 0
        self.source_tower = None
        self.poison_stacks = 0
        self.physical_branch = 1

        prefix = str(self.tower_type.value)
        if self.tower_level >= 11:
            if self.tower_type == TowerType.WIND and self.wind_branch == 2:
                img = f"tower/{prefix}{prefix}{prefix}-2.png"
            elif self.tower_type == TowerType.ICE and self.ice_branch == 2:
                img = f"tower/{prefix}{prefix}{prefix}-2.png"
            elif self.tower_type == TowerType.FLAME and self.flame_branch == 2:
                img = f"tower/{prefix}{prefix}{prefix}-2.png"
            elif self.tower_type == TowerType.POISON:
                img = f"tower/{prefix}{prefix}{prefix}-{self.poison_branch}.png"
            elif self.tower_type == TowerType.TRIDENT and self.trident_branch == 2:
                img = f"tower/{prefix}{prefix}{prefix}-2.png"
            else:
                img = f"tower/{prefix}{prefix}{prefix}-1.png"
        elif self.tower_level >= 6:
            if self.tower_type == TowerType.POISON:
                branch = self.poison_branch if self.poison_branch <= 2 else 2
                img = f"tower/{prefix}{prefix}-{branch}.png"
            else:
                img = f"tower/{prefix}{prefix}-1.png"
        else:
            if self.tower_type == TowerType.POISON:
                branch = self.poison_branch if self.poison_branch <= 2 else 2
                img = f"tower/{prefix}-{branch}.png"
            else:
                img = f"tower/{prefix}-1.png"

        self.raw_img = assets.load_image(img, (TILE_SIZE // 2, TILE_SIZE // 2))

        angle = math.degrees(math.atan2(-self.dy, self.dx))
        rotate_angle = angle - 45

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
            if self.tower_level >= 11 and (not self.source_tower or self.source_tower.wind_branch == 1):
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

        if self.tower_type == TowerType.ICE and self.tower_level >= 11 and self.ice_branch == 1 and enemy.freeze_time > 0:
            bonus = int(self.game.temperature * 3 * (self.tower_level - 10))
            final_dmg += bonus

        if self.tower_type == TowerType.TELEPORT and self.tower_level >= 11:
            hp_ratios = {11: 0.01, 12: 0.0125, 13: 0.015, 14: 0.0175, 15: 0.02}
            hp_bonus = int(enemy.max_health * hp_ratios.get(self.tower_level, 0))
            final_dmg += hp_bonus

        if enemy.enemy_type in (EnemyType.GOLD_ARMORED, EnemyType.NETHERITE_ARMORED) and self.tower_level >= 6:
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
            if self.tower_level >= 11 and self.ice_branch == 1:
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
            if self.tower_level >= 11 and self.flame_branch == 1:
                self.game.add_dragon_breath(
                    enemy.rect.centerx, enemy.rect.centery,
                    self.game.temperature, self.tower_level, self.stun_time)
        if self.tower_type == TowerType.PHYSICAL:
            if self.tower_level >= 11 and not enemy.broken and self.physical_branch == 1:
                enemy.broken = True
        if self.tower_type == TowerType.TRIDENT:
            col = enemy.rect.centerx // TILE_SIZE
            lightning_dmg = self.calculate_lightning_damage()
            gold_bonus = int(self.game.coins * 0.01) if self.tower_level >= 6 else 0
            for e in self.game.enemies:
                e_col = e.rect.centerx // TILE_SIZE
                if e_col == col and e.health > 0:
                    dmg = lightning_dmg
                    if e.enemy_type in (EnemyType.GOLD_ARMORED, EnemyType.NETHERITE_ARMORED):
                        dmg = self.lightning_damage
                    reward = e.take_damage(dmg, color=GOLD)
                    self.game.coins += reward
                    e.apply_burn(self.game.temperature, 240)
            is_golden = self.tower_level >= 6
            self.game.add_lightning(enemy.rect.centerx, 800, is_golden)
            if self.tower_level >= 11:
                if self.trident_branch == 1:
                    row = enemy.rect.centery // TILE_SIZE
                    h_lightning_dmg = self.calculate_lightning_damage()
                    for e in self.game.enemies:
                        e_row = e.rect.centery // TILE_SIZE
                        if e_row == row and e.health > 0:
                            dmg = h_lightning_dmg
                            if e.enemy_type in (EnemyType.GOLD_ARMORED, EnemyType.NETHERITE_ARMORED):
                                dmg = self.lightning_damage
                            reward = e.take_damage(dmg, color=GOLD)
                            self.game.coins += reward
                    h_effect = HorizontalLightningEffect(1024, row * TILE_SIZE + TILE_SIZE // 2, not is_golden)
                    self.game.horizontal_lightning_effects.append(h_effect)
                elif random.random() < 0.05:
                    dragon = Dragon(self.game.path, 'electric', self.tower_level, self.game)
                    self.game.dragons.add(dragon)
        if self.tower_type == TowerType.WIND:
            if self.source_tower:
                enemy.apply_knockback(self.source_tower.wind_knockback)
                if self.tower_level >= 6 and enemy.enemy_type not in (EnemyType.IRON_ARMORED, EnemyType.GOLD_ARMORED, EnemyType.DIAMOND_ARMORED, EnemyType.NETHERITE_ARMORED):
                    enemy.wind_mark_tower = self.source_tower
                if self.tower_level >= 11 and (not self.source_tower or self.source_tower.wind_branch == 1):
                    stun_frames = {11: 6, 12: 12, 13: 18, 14: 24, 15: 30}
                    enemy.apply_stun(stun_frames.get(self.tower_level, 6))
            if self.source_tower and self.source_tower.wind_branch == 2 and self.tower_level >= 11:
                dmg_map = {11: 2000, 12: 4000, 13: 6000, 14: 8000, 15: 10000}
                lightning_dmg = dmg_map.get(self.tower_level, 2500)
                col = enemy.rect.centerx // TILE_SIZE
                for e in self.game.enemies:
                    e_col = e.rect.centerx // TILE_SIZE
                    if e_col == col and e.health > 0:
                        reward = e.take_damage(lightning_dmg, color=GOLD)
                        self.game.coins += reward
                self.game.add_lightning(enemy.rect.centerx, 800, False)
        if self.tower_type == TowerType.POISON and self.poison_stacks > 0:
            enemy.apply_poison(self.poison_stacks)
            if self.tower_level >= 6 and (not self.source_tower or self.source_tower.poison_branch != 3):
                splash = PoisonSplash(enemy.rect.centerx, enemy.rect.centery, self.damage, self.poison_stacks, self.game)
                self.game.poison_splashes.append(splash)


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
            img = "tower/999-1.png"
        elif tower_level >= 6:
            sub_map = {BombSubType.SNOW: "99-1", BombSubType.ICE: "99-2", BombSubType.FLAME: "99-3", BombSubType.POISON: "99-4", BombSubType.WITHER_TNT: "99-5"}
            img = f"tower/{sub_map[bomb_subtype]}.png"
        else:
            img = "tower/9-1.png"
        self.raw_img = assets.load_image(img, (TILE_SIZE // 2, TILE_SIZE // 2))

        angle = math.degrees(math.atan2(-self.dy, self.dx))
        rotate_angle = angle - 45

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


class NuclearMissile(pygame.sprite.Sprite):
    def __init__(self, x, y, target_x, target_y, damage, tower_level, game, bomb_branch=1):
        super().__init__()
        self.x = x
        self.y = y
        self.target_x = target_x
        self.target_y = target_y
        self.speed = 8
        self.damage = damage
        self.tower_level = tower_level
        self.game = game
        self.bomb_branch = bomb_branch
        self.raw_img = assets.load_image(f"tower/999-{bomb_branch}.png", (TILE_SIZE // 2, TILE_SIZE // 2))
        self.image = self.raw_img
        self.rect = self.image.get_rect(center=(x, y))

    def update(self):
        dx = self.target_x - self.x
        dy = self.target_y - self.y
        dist = (dx * dx + dy * dy) ** 0.5
        if dist < self.speed:
            explosion = MushroomExplosion(MAP_CENTER_X, MAP_CENTER_Y,
                                          self.damage, self.tower_level, self.game, self.bomb_branch)
            self.game.mushroom_explosions.append(explosion)
            shockwave = NuclearShockwave(MAP_CENTER_X, MAP_CENTER_Y, self.game, self.bomb_branch)
            self.game.shockwave_effects.append(shockwave)
            self.kill()
            return
        self.x += (dx / dist) * self.speed
        self.y += (dy / dist) * self.speed
        self.rect.center = (self.x, self.y)


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
            img = "tower/888-2.png"
        elif tower_level >= 6:
            img = "tower/88-2.png"
        else:
            img = "tower/8-2.png"
        self.raw_img = assets.load_image(img, (TILE_SIZE // 2, TILE_SIZE // 2))

        angle = math.degrees(math.atan2(-self.dy, self.dx))
        rotate_angle = angle - 45

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