import pygame
import math
import random
import assets
from config import *
from effects import CreeperExplosion, PoisonContractExplosion
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
        if enemy_key == "HEROBRINE":
            self.max_health = config["health"]
            self.health = self.max_health
            self.total_layers = 18
            self.current_layer = 18
        elif enemy_key in ("CREEPER", "CHARGED_CREEPER"):
            self.max_health = config["health"] * (1.2 ** game.wave_manager.current_wave)
            self.health = self.max_health
            self.total_layers = 1
            self.current_layer = 1
            self.charged = enemy_key == "CHARGED_CREEPER"
        else:
            self.max_health = config["health"] * (1.2 ** game.wave_manager.current_wave)
            self.health = self.max_health
            self.total_layers = 1
            self.current_layer = 1
        self.creeper_explode_timer = 900 if enemy_key in ("CREEPER", "CHARGED_CREEPER") else -1
        self.reward = config["reward"]
        self.base_speed = self.speed

        self.stun_time = 0
        self.freeze_time = 0
        self.slow_time = 0
        self.burn_time = 0
        self.burn_damage = 0
        self.broken = False
        self.ice_broken = False
        self.wind_mark_tower = None
        self.contaminated = False
        self.contaminated_timer = 0
        self.wither_time = 0
        self.wither_timer = 0

        self.weather_slowed = False
        self.freeze_resistance = 0.0
        self.stun_resistance = 0.0
        self.last_freeze_time = -9999
        self.last_stun_time = -9999
        if game.weather == Weather.TAILWIND:
            self.speed *= 1.5
            self.base_speed = self.speed
            self.tailwind_boosted = True
        else:
            self.tailwind_boosted = False

        if game.weather == Weather.HEADWIND:
            self.speed *= 0.5
            self.base_speed = self.speed
            self.weather_slowed = True

        if game.weather == Weather.ENDLESS_NIGHT:
            if self.enemy_type not in (EnemyType.GHOST, EnemyType.WITHER):
                self.speed *= 0.5
                self.base_speed = self.speed
                self.weather_slowed = True

        if game.weather == Weather.SCORCHING_SUN:
            if game.temperature > 0 and self.enemy_type not in (EnemyType.MAGMA_CUBE, EnemyType.MAGMA_CUBE_SMALL):
                self.burn_damage = max(self.burn_damage, game.temperature)
                self.burn_time = max(self.burn_time, 999999)
        if game.weather == Weather.FIRE_RAIN:
            if game.temperature > 0 and self.enemy_type not in (EnemyType.MAGMA_CUBE, EnemyType.MAGMA_CUBE_SMALL):
                self.burn_damage = max(self.burn_damage, game.temperature)
                self.burn_time = max(self.burn_time, 999999)

        self.poison_stacks = 0
        self.poison_timer = 0
        if game.weather == Weather.ACID_RAIN:
            self.apply_poison(10)
        if game.weather == Weather.MAGNETIC_STORM:
            if self.enemy_type in (EnemyType.IRON_ARMORED, EnemyType.GOLD_ARMORED, EnemyType.DIAMOND_ARMORED, EnemyType.NETHERITE_ARMORED):
                self.broken = True

        self.image = assets.load_image(f"enemy/{config['image']}")
        if self.enemy_type in (EnemyType.SLIMELING, EnemyType.MAGMA_CUBE_SMALL):
            self.image = pygame.transform.smoothscale(
                self.image, (self.image.get_width() // 2, self.image.get_height() // 2))

        self.rect = self.image.get_rect()
        start_x, start_y = self.path[self.path_index]
        self.pos_x = start_x * TILE_SIZE + TILE_SIZE // 2
        self.pos_y = start_y * TILE_SIZE + TILE_SIZE // 2
        self.rect.center = (self.pos_x, self.pos_y)

        if self.enemy_type in (EnemyType.GHOST, EnemyType.WITHER):
            ex, ey = self.path[-1]
            self.ghost_target = (ex * TILE_SIZE + TILE_SIZE // 2, ey * TILE_SIZE + TILE_SIZE // 2)

    def apply_slow(self, slow_factor, duration):
        # 天气本身不再减速（雨天/雷暴/酸雨/极寒都取消），所以冰系减速一律正常生效
        self.speed = self.base_speed * slow_factor
        self.slow_time = duration

    def apply_burn(self, damage, duration):
        if self.enemy_type in (EnemyType.MAGMA_CUBE, EnemyType.MAGMA_CUBE_SMALL):
            return
        if self.game.temperature <= 0:
            return
        if self.game.weather in (Weather.RAINY, Weather.THUNDERSTORM, Weather.ACID_RAIN):
            if Enchantment.RAIN_FIRE not in self.game.enchantments:
                return
        self.burn_damage = max(self.burn_damage, damage)
        self.burn_time = max(self.burn_time, duration)

    def apply_stun(self, duration):
        effective = int(duration * (1.0 - self.stun_resistance))
        self.stun_time = max(self.stun_time, effective)
        self.stun_resistance = min(0.90, self.stun_resistance + 0.10)
        self.last_stun_time = self.game.game_time

    def apply_freeze(self, duration):
        if self.game.temperature < 0:
            duration = int(duration * (1 + abs(self.game.temperature) / 100))
        effective = int(duration * (1.0 - self.freeze_resistance))
        self.freeze_time = max(self.freeze_time, effective)
        self.freeze_resistance = min(0.90, self.freeze_resistance + 0.10)
        self.last_freeze_time = self.game.game_time

    def apply_poison(self, stacks):
        if self.game.weather == Weather.ACID_RAIN:
            stacks *= 2
        self.poison_stacks += stacks

    def apply_contaminate(self):
        self.contaminated = True

    def apply_wither(self, duration):
        if duration > self.wither_time:
            self.wither_time = duration
            self.wither_timer = 0

    def resistance(self):
        """当前抗性（可以为负）。

        盔甲类敌人的基础抗性见 ARMOR_RESISTANCE；「抗性降低」(broken)
        只把抗性减 20 个百分点，非盔甲怪因此变成 -20%（受伤 ×1.2）。
        """
        res = ARMOR_RESISTANCE.get(self.enemy_type, 0.0)
        if self.broken:
            res -= BROKEN_RESIST_DOWN
        return res

    def apply_ice_broken(self):
        """冰系破甲：永久生效，受到的冰系伤害 +100%。

        和「抗性降低」(broken) 不同：这条不碰抗性，而是往增伤乘区里加 +100%，
        且只对冰系伤害生效。
        """
        self.ice_broken = True

    def on_lightning_hit(self):
        if self.enemy_type == EnemyType.CREEPER and not self.charged:
            self.charged = True
            self.creeper_explode_timer //= 2
            try:
                self.image = assets.load_image("enemy/charged_creeper.png")
            except Exception:
                pass

    def creeper_explode(self):
        is_charged = self.charged or self.enemy_type == EnemyType.CHARGED_CREEPER
        size = 5 if is_charged else 3
        half = size // 2
        cx = self.rect.centerx // TILE_SIZE
        cy = self.rect.centery // TILE_SIZE
        for t in list(self.game.towers):
            if abs(t.x - cx) <= half and abs(t.y - cy) <= half:
                if t.in_pulse():
                    continue
                if getattr(t, 'has_shield', False):
                    t.break_shield()
                    self.game.notify_tower_hit(t)
                elif t.is_invincible():
                    self.game.notify_tower_hit(t)   # 炸不死，但能量照加
                else:
                    self.game.notify_tower_hit(t)
                    t.kill()
        for wall in list(self.game.ice_walls):
            if abs(wall.x - cx) <= half and abs(wall.y - cy) <= half:
                self.game.destroy_ice_wall(wall)
        self.game.creeper_explosions.append(
            CreeperExplosion(self.rect.centerx, self.rect.centery, self.game, charged=is_charged))
        self.kill()

    def apply_speed(self, speed_factor, duration):
        self.speed = self.base_speed * speed_factor
        self.slow_time = duration

    def apply_wind(self, knockback):
        if self.path_index >= len(self.path):
            return
        tx = self.path[self.path_index][0] * TILE_SIZE + TILE_SIZE // 2
        ty = self.path[self.path_index][1] * TILE_SIZE + TILE_SIZE // 2
        dx = tx - self.pos_x
        dy = ty - self.pos_y
        dist = math.sqrt(dx * dx + dy * dy)
        if dist > 0:
            dx /= dist
            dy /= dist
            self.pos_x -= dx * knockback
            self.pos_y -= dy * knockback
            self.rect.center = (self.pos_x, self.pos_y)

    def _tick_resistances(self):
        if self.game.game_time - self.last_freeze_time > 600:
            self.freeze_resistance = 0.0
        if self.game.game_time - self.last_stun_time > 600:
            self.stun_resistance = 0.0

    def update_status_effects(self):
        """推进减益计时（眩晕/冰冻/减速/燃烧/中毒/凋零）。

        返回 True 表示这一帧被控制住、无法行动。最终 BOSS 会把控制类减益
        重写成空实现，但依然复用这里的持续伤害结算。
        """
        if self.stun_time > 0:
            self.stun_time -= 1
            return True
        if self.freeze_time > 0:
            self.freeze_time -= 1
            return True
        if self.slow_time > 0:
            self.slow_time -= 1
        else:
            self.speed = self.base_speed
        if self.burn_time > 0:
            self.burn_time -= 1
            if self.burn_time % 30 == 0:
                # 燃烧跳伤 = 温度 × 烈焰粉 × 高温燃烧 × 灯火通明 × (1 + 火系伤害加成)
                dmg = self.game.burn_tick_damage(self.burn_damage)
                reward = self.take_damage(dmg, color=ORANGE, scale=1.0, element="fire")
                self.game.coins += reward

        if self.poison_stacks > 0:
            self.poison_timer += 1
            if self.poison_timer >= 75:
                self.poison_timer = 0
                # 中毒跳伤 = (基础毒伤 + 中毒层数) × (1 + 毒系伤害加成)
                poison_damage = int((self.game.poison_base_damage + self.poison_stacks) * self.game.get_element_damage_multiplier("poison"))
                reward = self.take_damage(poison_damage, color=GREEN, scale=1.0, element="poison")
                self.game.coins += reward

        if self.wither_time > 0:
            self.wither_time -= 1
            self.wither_timer += 1
            if self.wither_timer >= 120:
                self.wither_timer = 0
                wither_pct = 0.01
                if self.game.wither_rose_active():
                    wither_pct += 0.001
                dmg = int(self.max_health * wither_pct)
                # 凋零伤害统一归入毒系
                reward = self.take_damage(dmg, color=(100, 0, 100), scale=1.0,
                                          ignore_armor=True, element="poison")
                self.game.coins += reward
        return False

    def update(self):
        if self.health <= 0:
            return False

        self._tick_resistances()

        if self.creeper_explode_timer > 0:
            self.creeper_explode_timer -= 1
            if self.creeper_explode_timer == 0:
                self.creeper_explode()
                return False

        if self.update_status_effects():
            return False

        if self.health <= 0:
            self.kill()
            return False

        if self.enemy_type in (EnemyType.GHOST, EnemyType.WITHER):
            tx, ty = self.ghost_target
            dx = tx - self.pos_x
            dy = ty - self.pos_y
            dist = (dx * dx + dy * dy) ** 0.5
            if dist < self.speed:
                self.kill()
                return True
            self.pos_x += (dx / dist) * self.speed
            self.pos_y += (dy / dist) * self.speed
            self.rect.center = (self.pos_x, self.pos_y)
            return False

        for wall in self.game.ice_walls:
            if self.rect.colliderect(wall.rect):
                return False

        if self.path_index >= len(self.path) - 1:
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
        if self.ice_broken:
            buff_list.append("ice_broken")
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
        if self.wither_time > 0:
            buff_list.append("wither")
        return buff_list

    def teleport_to_start(self):
        self.path_index = 0
        start_x, start_y = self.path[self.path_index]
        self.pos_x = start_x * TILE_SIZE + TILE_SIZE // 2
        self.pos_y = start_y * TILE_SIZE + TILE_SIZE // 2
        self.rect.center = (self.pos_x, self.pos_y)

    def apply_knockback(self, distance):
        if self.enemy_type in (EnemyType.IRON_ARMORED, EnemyType.GOLD_ARMORED, EnemyType.DIAMOND_ARMORED, EnemyType.NETHERITE_ARMORED):
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

    def take_damage(self, damage, color=RED, scale=1.0, ignore_armor=False, element=None,
                    text_speed_x=0.0):
        if self.health <= 0:
            return 0

        if ignore_armor:
            # 真实伤害：抗性与增伤乘区都不参与
            final_dmg = damage
        else:
            # 统一口径：最终伤害 = 基础伤害区 × (1 + 增伤乘区) × (1 - 抗性)
            resistance = self.resistance()
            bonus = 0.0
            if self.ice_broken and (element or getattr(self.game, "damage_element", None)) == "ice":
                bonus += ICE_BROKEN_BONUS
            final_dmg = damage * (1.0 + bonus) * (1.0 - resistance)
        # 用 round 而不是直接 int：1000 * (1-0.8) 在浮点下是 199.99997，截断会白丢 1 点
        final_dmg = int(round(final_dmg))
        self.health -= final_dmg

        if self.game:
            self.game.spawn_damage_text(final_dmg, self.rect.center, color=color, scale=scale,
                                        speed_x=text_speed_x)
            if final_dmg > 0 and getattr(self.game, "damage_stats", None) is not None:
                elem = element or getattr(self.game, "damage_element", None)
                self.game.damage_stats.add(elem, final_dmg)

        if self.health <= 0:
            if self.enemy_type == EnemyType.HEROBRINE:
                self.current_layer -= 1
                if self.current_layer > 0:
                    self.health = self.max_health
                    phase_group = (self.total_layers - self.current_layer) % 3 + 1
                    self.game.herobrine_phase = phase_group
                    if phase_group == 1:
                        for _ in range(5):
                            self.game.herobrine_summon_queue.append(EnemyType.SLIME)
                        for _ in range(5):
                            self.game.herobrine_summon_queue.append(EnemyType.MAGMA_CUBE)
                    elif phase_group == 2:
                        for _ in range(5):
                            self.game.herobrine_summon_queue.append(EnemyType.NETHERITE_ARMORED)
                    elif phase_group == 3:
                        for _ in range(15):
                            self.game.herobrine_summon_queue.append(EnemyType.GHOST)
                        for _ in range(5):
                            self.game.herobrine_summon_queue.append(EnemyType.WITHER)
                    return 0
            if self.enemy_type == EnemyType.SLIME:
                for _ in range(3):
                    child = Enemy(self.path, EnemyType.SLIMELING, self.game)
                    child.path_index = self.path_index
                    child.pos_x = self.pos_x
                    child.pos_y = self.pos_y
                    child.rect.center = (child.pos_x, child.pos_y)
                    self.game.enemies.add(child)
            if self.enemy_type == EnemyType.MAGMA_CUBE:
                for _ in range(3):
                    child = Enemy(self.path, EnemyType.MAGMA_CUBE_SMALL, self.game)
                    child.path_index = self.path_index
                    child.pos_x = self.pos_x
                    child.pos_y = self.pos_y
                    child.rect.center = (child.pos_x, child.pos_y)
                    self.game.enemies.add(child)
            if self.wind_mark_tower is not None:
                t = self.wind_mark_tower
                exp_dmg = 5000 if Enchantment.WIND_BURST in self.game.enchantments else t.damage
                exp_dmg = int(exp_dmg * self.game.get_element_damage_multiplier("wind"))
                exp = WindExplosion(self.rect.centerx, self.rect.centery,
                                   exp_dmg, t.wind_knockback, self.game, element="wind")
                self.game.wind_explosions.append(exp)
                self.wind_mark_tower = None
            if self.poison_stacks > 0 and self.game.poison_contract_active():
                # 10% 概率触发，期望约等于「本波敌人数 / 10」层
                if random.random() < POISON_CONTRACT_TRIGGER_CHANCE:
                    exp = PoisonContractExplosion(self.rect.centerx, self.rect.centery,
                                                  self.game, self.poison_stacks)
                    self.game.poison_splashes.append(exp)
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
    def __init__(self, text, x, y, color=RED, duration=45, speed_y=-2, scale=1.0, speed_x=0.0):
        super().__init__()
        self.text = str(text)
        self.color = color
        self.duration = duration
        self.timer = 0
        self.speed_y = speed_y
        self.speed_x = speed_x
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
        self.pos_x += self.speed_x
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
