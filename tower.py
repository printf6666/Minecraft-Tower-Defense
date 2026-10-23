import pygame
import random
import math
import assets
import stats
from config import *
from effects import WindExplosion, IceExplosion, DragonBreathPool, LightningEffect, HorizontalLightningEffect, PoisonSplash, TNTExplosion, MushroomExplosion, NuclearShockwave, WitherSplash, IceWall, HellRay, SwordSpin, StarWrath, FallingStar
from dragons import Dragon

MAP_CENTER_X = GRID_WIDTH * TILE_SIZE // 2
MAP_CENTER_Y = (1 + GRID_HEIGHT) * TILE_SIZE // 2

ICE_WALL_CHANCE = 0.04
ICE_WALL_DURATION = {11: 2, 12: 2.5, 13: 3, 14: 3.5, 15: 4}

# TNT 二阶子类型的贴图分支序号（对应 9-2-1 ~ 9-2-5）
BOMB_SUBTYPE_ORDER = [BombSubType.SNOW, BombSubType.ICE, BombSubType.FLAME,
                      BombSubType.POISON, BombSubType.WITHER_TNT]

# 每座塔在每个阶级实际存在的分支数。
# 用来 clamp 非法分支值：存档损坏、旧版本回退、或某个切换逻辑写错时，
# 不至于去 load 一个不存在的 png 直接崩掉游戏。
MAX_BRANCH = {
    TowerType.SHIELD:     {1: 1, 2: 1, 3: 3},
    TowerType.PHYSICAL:   {1: 1, 2: 1, 3: 3},
    TowerType.PRODUCTION: {1: 1, 2: 1, 3: 1},
    TowerType.ICE:        {1: 1, 2: 1, 3: 3},
    TowerType.TELEPORT:   {1: 2, 2: 2, 3: 2},
    TowerType.FLAME:      {1: 1, 2: 1, 3: 3},
    TowerType.TRIDENT:    {1: 1, 2: 1, 3: 2},
    TowerType.WIND:       {1: 1, 2: 1, 3: 2},
    TowerType.POISON:     {1: 2, 2: 2, 3: 3},
    TowerType.BOMB:       {1: 1, 2: 5, 3: 2},
    TowerType.TIME:       {1: 1, 2: 1, 3: 1},
    TowerType.SWORD:      {1: 1, 2: 3, 3: 2},
}


def tower_sprite_path(ttype, level, **br):
    """炮塔贴图路径，统一规则：tower/{塔序号}-{阶级}-{分支}.png

    阶级：1 = Lv1-5，2 = Lv6-10，3 = Lv11-15
    分支：从 1 开始，单分支塔恒为 1

    br 传各塔的分支属性，例如 physical_branch=2、bomb_subtype=BombSubType.ICE。
    这个函数被 Tower.update_sprite() 和三个弹幕类共用，避免多处重复判断。
    """
    stage = 3 if level >= 11 else (2 if level >= 6 else 1)
    b = 1
    if ttype == TowerType.PHYSICAL and stage == 3:
        b = br.get("physical_branch", 1)
    elif ttype == TowerType.ICE and stage == 3:
        b = br.get("ice_branch", 1)
    elif ttype == TowerType.FLAME and stage == 3:
        b = br.get("flame_branch", 1)
    elif ttype == TowerType.TRIDENT and stage == 3:
        b = br.get("trident_branch", 1)
    elif ttype == TowerType.WIND and stage == 3:
        b = br.get("wind_branch", 1)
    elif ttype == TowerType.SHIELD and stage == 3:
        b = br.get("shield_branch", 1)
    elif ttype == TowerType.POISON:
        # 毒系一阶就能切 2 个分支，三阶有 3 个
        pb = br.get("poison_branch", 1)
        b = pb if stage == 3 else min(pb, 2)
    elif ttype == TowerType.TELEPORT:
        # 传送三阶都是 2 个分支
        b = br.get("teleport_branch", 1)
    elif ttype == TowerType.BOMB:
        if stage == 2:
            sub = br.get("bomb_subtype", BombSubType.SNOW)
            b = BOMB_SUBTYPE_ORDER.index(sub) + 1
        elif stage == 3:
            b = br.get("bomb_branch", 1)
    elif ttype == TowerType.SWORD and stage >= 2:
        # 剑系一阶只有铁剑一种形态，二阶 3 分支、三阶 2 分支
        b = br.get("sword_branch", 1)
    # 兜底 clamp：任何非法分支值都退回合法范围，绝不去 load 不存在的 png
    b = min(max(1, int(b)), MAX_BRANCH.get(ttype, {}).get(stage, 1))
    return f"tower/{ttype.value}-{stage}-{b}.png"


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
        self.wind_knockback = 0

        self.dragon_breath_cooldown = 0
        self.shield_timer = 0
        self.shield_pulse_timer = 0

        self.physical_branch = 1
        self.wind_branch = 1
        self.ice_branch = 1
        self.flame_branch = 1
        self.poison_branch = 1
        self.bomb_branch = 1
        self.trident_branch = 1
        self.teleport_branch = 1
        self.shield_branch = 1
        self.sword_branch = 1
        self.sword_spinning = False     # 是否处于「有敌人可打」的持续旋转状态
        self.sword_spin = None          # SwordSpin 实例（视觉，挂在 game.sword_sweeps）
        self.ice_explosion_visual = 0

        self.attack_speed_buff = 0
        self.production_buff = 0.0
        self.disabled_timer = 0

        self.setup_tower()
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
            if self.teleport_branch == 2:
                self.range = TILE_SIZE * 3
                self.damage = 100
            else:
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
            self.damage = 20
            self.fire_rate = 60
            self.cost = 400
            self.upgrade_cost = 600
            self.lightning_damage = 50
        elif self.type == TowerType.WIND:
            self.range = int(TILE_SIZE * 1.5)
            self.damage = 5
            self.fire_rate = 60
            self.cost = 250
            self.upgrade_cost = 375
            self.wind_knockback = 12
        elif self.type == TowerType.SHIELD:
            self.range = 0
            self.damage = 0
            self.fire_rate = 0
            self.cost = 450
            self.upgrade_cost = 675
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
            self.ember_salvo = False
        elif self.type == TowerType.TIME:
            self.range = 0
            self.damage = 0
            self.fire_rate = 0
            self.cost = 125
            self.upgrade_cost = 190
            self.attack_speed_buff = 0
            self.production_buff = 0.0
        elif self.type == TowerType.SWORD:
            self.cost = 750
            self.upgrade_cost = 1125
            self._recalc_sword()

    def upgrade(self):
        if self.level >= 15:
            return
        self.level += 1
        self.upgrade_cost = int(self.upgrade_cost * 1.5)
        if self.type == TowerType.PRODUCTION:
            multiplier = 2 if self.is_on_gold_ore else 1
            self.game.gold_per_second += multiplier
            if self.level >= 6: self.game.gold_per_wave += multiplier
            if self.level >= 11:
                self.game.emerald_per_wave += EMERALD_PER_WAVE_BY_LEVEL.get(self.level, 3) - EMERALD_PER_WAVE_BY_LEVEL.get(self.level - 1, 0)
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
            if self.teleport_branch == 2:
                self.damage += 100
                self.range += TILE_SIZE // 2
                self.fire_rate = max(30, self.fire_rate - 6)
            else:
                self.damage += 5
                self.teleport_chance += 0.01
                self.range += TILE_SIZE // 4
                self.fire_rate = max(30, self.fire_rate - 6)
                if self.level >= 6: self.oneshot_chance += 0.01
        elif self.type == TowerType.FLAME:
            self.damage += 15
            self.range += TILE_SIZE // 4
            self.fire_rate = max(30, self.fire_rate - 6)
            if self.level >= 6: self.stun_time = round(self.stun_time + 0.1, 1)
        elif self.type == TowerType.TRIDENT:
            self.damage += 20
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
                self.fire_rate = 35 * 60

        if self.type in (TowerType.FLAME, TowerType.SWORD):
            self.recalculate_stats()

        self.update_sprite()

    def recalculate_stats(self):
        if self.type == TowerType.FLAME:
            self._recalc_flame()
            return
        if self.type == TowerType.SWORD:
            self._recalc_sword()
            return
        if self.type != TowerType.TELEPORT:
            return
        self.teleport_chance = 0.01
        self.oneshot_chance = 0
        if self.teleport_branch == 2:
            self.damage = 100 + (self.level - 1) * 100
            self.range = TILE_SIZE * 3 + (self.level - 1) * (TILE_SIZE // 2)
        else:
            self.damage = 5 + (self.level - 1) * 5
            self.range = TILE_SIZE * 1.5 + (self.level - 1) * (TILE_SIZE // 4)
            for i in range(self.level - 1):
                self.teleport_chance += 0.01
                if i >= 5:
                    self.oneshot_chance += 0.01
        self.fire_rate = max(30, 60 - (self.level - 1) * 6)

    def _recalc_flame(self):
        """火系数值按等级整体重算；分支 3（星焰提灯）走独立数值表。"""
        lv = self.level
        self.damage = 20 + 15 * (lv - 1)
        self.range = TILE_SIZE * 1.5 + (lv - 1) * (TILE_SIZE // 4)
        self.fire_rate = max(30, 60 - (lv - 1) * 6)
        self.stun_time = round(0.1 * max(0, lv - 5), 1) if lv >= 6 else 0
        if lv >= 11 and self.flame_branch == 3:
            self.range = int(TILE_SIZE * LANTERN_RANGE_TILES.get(lv, 3.5))
            self.fire_rate = LANTERN_FIRE_RATE
            self.stun_time = 0

    def is_lantern(self):
        """星焰提灯：火系 Lv11+ 分支 3。"""
        return (self.type == TowerType.FLAME and self.level >= 11
                and self.flame_branch == 3)

    def _recalc_sword(self):
        """剑系数值按等级整体重算（挥砍本体）。三阶两种弹幕的伤害另算。"""
        lv = self.level
        # 分支数随阶级变化：一阶只有铁剑，二阶 3 个，三阶 2 个。
        # 二阶升到三阶时 branch 可能是 3（草剑），必须夹到 2，
        # 否则 update_sprite 会去找不存在的 11-3-3.png 而崩。
        if lv >= 11:
            self.sword_branch = min(max(1, self.sword_branch), 2)
        elif lv >= 6:
            self.sword_branch = min(max(1, self.sword_branch), 3)
        else:
            self.sword_branch = 1
        self.damage = SWORD_BASE_DAMAGE + SWORD_DAMAGE_PER_LV * (lv - 1)
        # 射程恒定，不随等级增长：后期主要靠三阶弹幕输出，本体挥砍只是保底
        self.range = int(TILE_SIZE * SWORD_RANGE_TILES)
        self.fire_rate = max(SWORD_FIRE_RATE_MIN,
                             SWORD_FIRE_RATE - 2 * (lv - 1))

    def sword_beam_damage(self):
        """泰拉刃弹幕单次伤害（吃物理系附魔加成）。"""
        lv = self.level
        mult = self.game.get_enchant_damage_multiplier(TowerType.SWORD)
        return max(1, int((SWORD_BEAM_DAMAGE + SWORD_BEAM_PER_LV * (lv - 11)) * mult))

    def sword_star_damage(self):
        """狂星之怒单颗星星伤害（吃物理系附魔加成）。"""
        lv = self.level
        mult = self.game.get_enchant_damage_multiplier(TowerType.SWORD)
        return max(1, int((SWORD_STAR_DAMAGE + SWORD_STAR_PER_LV * (lv - 11)) * mult))

    def lantern_damage(self):
        """星焰提灯冲击波的单次伤害（含火系 / 均衡附魔加成）。

        注意：只有冲击波本体吃加成，附加的燃烧沿用原始温度，不吃任何伤害加成。
        """
        mult = self.game.get_enchant_damage_multiplier(TowerType.FLAME)
        return max(1, int((LANTERN_BASE_DAMAGE + self.game.temperature * LANTERN_TEMP_MULT)
                          * (self.level - 10) * mult))

    def update_sprite(self):
        img = tower_sprite_path(
            self.type, self.level,
            physical_branch=self.physical_branch,
            ice_branch=self.ice_branch,
            flame_branch=self.flame_branch,
            trident_branch=self.trident_branch,
            wind_branch=self.wind_branch,
            shield_branch=self.shield_branch,
            poison_branch=self.poison_branch,
            teleport_branch=self.teleport_branch,
            bomb_branch=self.bomb_branch,
            bomb_subtype=getattr(self, "bomb_subtype", BombSubType.SNOW),
            sword_branch=self.sword_branch,
        )
        self.image = assets.load_image(img)
        self.rect = self.image.get_rect()
        self.rect.topleft = (self.x * TILE_SIZE, self.y * TILE_SIZE)

    def can_attack(self, current_time):
        if self.disabled_timer > 0:
            return False
        if self.type == TowerType.PHYSICAL and self.level >= 11 and self.physical_branch == 3:
            return current_time - self.last_shot >= (19 - self.level) * 60
        total_bonus = self.attack_speed_buff
        if self.game.weather == Weather.AURORA and self.game.temperature < 0:
            total_bonus += abs(self.game.temperature)
        effective_fire_rate = self.fire_rate * 100 / max(1, 100 + total_bonus)
        if self.game.boss_rule and self.game.boss_rule.get("type") == "attack_speed":
            effective_fire_rate *= 1.5
        return current_time - self.last_shot >= effective_fire_rate

    def get_effective_range(self):
        if self.type == TowerType.BOMB and self.is_nuclear:
            return 0
        r = self.range
        if Enchantment.TELESCOPE in self.game.enchantments and self.range > 0:
            r += TILE_SIZE
        if self.game.weather == Weather.TAILWIND:
            r += int(self.range * 0.5)
        if self.game.weather == Weather.HEADWIND:
            r -= int(self.range * 0.5)
        if self.game.boss_rule and self.game.boss_rule.get("type") == "range":
            r = int(r * 0.7)
        return r

    def attack(self, current_time):
        if not self.can_attack(current_time):
            return []
        # 整个攻击流程（含直接结算的地狱射线、闪电、爆炸）都归属该塔的属性
        prev_element = self.game.damage_element
        self.game.damage_element = stats.tower_element(self.type)
        try:
            return self._attack_inner(current_time)
        finally:
            self.game.damage_element = prev_element

    def _attack_inner(self, current_time):
        prev_last_shot = self.last_shot
        self.last_shot = current_time

        if self.type in (TowerType.PRODUCTION, TowerType.TIME):
            return []

        if self.type == TowerType.BOMB and self.is_nuclear:
            if self.game.enemies or self.ember_salvo:
                self.ember_salvo = False
                missile = NuclearMissile(self.rect.centerx, self.rect.centery,
                                         MAP_CENTER_X, MAP_CENTER_Y,
                                         self.damage, self.level, self.game,
                                         self.bomb_branch)
                return [missile]
            self.last_shot = prev_last_shot
            return []

        if self.is_lantern():
            return self._lantern_attack()

        check_range = self.get_effective_range() + TILE_SIZE // 2

        # 剑系：一阶/二阶要求射程内有敌人，三阶只要场上有敌人就攻击
        # （放在九宫格 has_target 检测之前，顺便省掉这次扫描）
        if self.type == TowerType.SWORD:
            return self._sword_attack(check_range)

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

        if self.type == TowerType.PHYSICAL and self.physical_branch == 3 and self.level >= 11:
            er = check_range
            targets = [e for e in self.game.enemies
                       if e.health > 0
                       and (e.rect.centerx - self.rect.centerx) ** 2 + (e.rect.centery - self.rect.centery) ** 2 <= er * er]
            if targets:
                best = random.choice(targets)
                if best.enemy_type in (EnemyType.HEROBRINE, EnemyType.FINAL_BOSS):
                    dmg = int(best.max_health * 0.05)
                else:
                    dmg = 99999999
                reward = best.take_damage(dmg, color=RED, scale=1.4)
                self.game.coins += reward
                ray = HellRay(self.rect.centerx, self.rect.centery,
                              best.rect.centerx, best.rect.centery)
                self.game.hell_rays.append(ray)
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
            bullet.source_tower = self
            if self.type == TowerType.POISON:
                if self.poison_branch == 3:
                    bullet.poison_stacks = self.level * 9
                elif self.level >= 11:
                    bullet.poison_stacks = self.level * 4
                else:
                    bullet.poison_stacks = self.level
            bullets.append(bullet)

        if self.type == TowerType.WIND and self.level >= 11 and self.wind_branch == 2:
            self.game.resonance_counter += 1
            if self.game.resonance_counter >= 120:
                self.game.resonance_counter = 0
                self.game.trigger_resonance_storm()

        if self.type == TowerType.ICE and self.level >= 11 and self.ice_branch == 2:
            if random.random() < 0.02:
                dragon = Dragon(self.game.path, "ice", self.level, self.game)
                self.game.dragons.add(dragon)

        if self.type == TowerType.FLAME and self.level >= 11 and self.flame_branch == 2:
            if random.random() < 0.05:
                dragon = Dragon(self.game.path, "fire", self.level, self.game)
                self.game.dragons.add(dragon)

        if self.type == TowerType.TELEPORT and self.teleport_branch == 2:
            if self.level >= 11:
                directions = [(0, -1), (1, -1), (1, 0), (1, 1), (0, 1), (-1, 1), (-1, 0), (-1, -1)]
            else:
                directions = [(0, -1), (0, 1), (-1, 0), (1, 0)]
            bullets = []
            for dx, dy in directions:
                bullet = Bullet(
                    self.rect.centerx, self.rect.centery,
                    dx, dy, self.get_effective_range(),
                    self.damage, self.type, self.game,
                    0, self.penetrate,
                    self.freeze_time, self.oneshot_chance, self.stun_time,
                    self.game.enemies, self.level,
                    teleport_branch=self.teleport_branch)
                bullet.source_tower = self
                bullets.append(bullet)
            return bullets

        return bullets

    def _lantern_attack(self):
        """星焰提灯：以自身为中心释放冲击波，命中范围内全部敌人（类似保卫萝卜的太阳）。"""
        radius = self.get_effective_range()
        if radius <= 0:
            return []
        cx, cy = self.rect.centerx, self.rect.centery
        targets = [e for e in self.game.enemies
                   if e.health > 0
                   and (e.rect.centerx - cx) ** 2 + (e.rect.centery - cy) ** 2 <= radius * radius]
        if not targets:
            return []

        damage = self.lantern_damage()

        self.game.add_lantern_shockwave(cx, cy, radius)
        for enemy in targets:
            reward = enemy.take_damage(damage, color=(255, 205, 90), scale=1.3)
            self.game.coins += reward
            enemy.apply_burn(self.game.temperature, LANTERN_BURN_FRAMES)
        return []

    # ------------------------------------------------------------ 剑系
    def _remaining_to_end(self, e):
        """敌人距离终点的剩余路程（越小越靠近终点）。

        GHOST / WITHER 直线飞向终点、path_index 恒为 0；FinalBoss 不走路径，
        这三类必须改用「到终点的直线距离」，否则会被误判成离终点最远。
        """
        end_px = (self.game.end_point[0] * TILE_SIZE + TILE_SIZE // 2,
                  self.game.end_point[1] * TILE_SIZE + TILE_SIZE // 2)
        if (e.enemy_type in (EnemyType.GHOST, EnemyType.WITHER)
                or getattr(e, "is_boss", False)):
            return math.hypot(e.rect.centerx - end_px[0],
                              e.rect.centery - end_px[1])
        path = self.game.path
        n = len(path) - 1
        idx = getattr(e, "path_index", 0)
        if idx >= n:
            return math.hypot(e.rect.centerx - end_px[0],
                              e.rect.centery - end_px[1])
        nx = path[idx + 1][0] * TILE_SIZE + TILE_SIZE // 2
        ny = path[idx + 1][1] * TILE_SIZE + TILE_SIZE // 2
        return (math.hypot(e.rect.centerx - nx, e.rect.centery - ny)
                + (n - (idx + 1)) * TILE_SIZE)

    def _sword_attack(self, radius):
        """挥砍：整圆范围伤害，三阶追加弹幕。

        三阶（Lv11+）只要场上有敌人就攻击，不要求敌人进入 2.5 格射程——
        伤害主要靠剑气 / 星星，本体挥砍只是保底。

        伤害在攻击瞬间立即结算（不再延迟到动画某一帧）：剑现在是持续旋转的，
        没有「扫到某一帧」的概念，视觉与伤害频率解耦。
        """
        alive = [e for e in self.game.enemies if e.health > 0]
        if not alive:
            return []
        cx, cy = self.rect.centerx, self.rect.centery
        targets = [e for e in alive
                   if (e.rect.centerx - cx) ** 2 + (e.rect.centery - cy) ** 2 <= radius * radius]

        # 一阶 / 二阶：圈内没敌人就不攻击
        if self.level < 11 and not targets:
            return []

        # 有敌人可打 -> 进入持续旋转状态（三阶即使圈内没人也要转）
        self.sword_spinning = True
        self._ensure_sword_spin()

        if targets:
            self._apply_sword_damage(targets)

        # 二阶分支 1「星怒」：攻击时从天而降一颗星星
        if self.level < 11 and self.sword_branch == 1 and targets:
            best = min(targets, key=self._remaining_to_end)
            self.game.stars.append(FallingStar(
                best.rect.centerx, best.rect.centery,
                int(self.damage * SWORD_METEOR_DAMAGE_RATIO), self.game))

        # 三阶分支 1「泰拉刃」：向离终点最近的敌人发射穿透剑气（全场索敌）
        if self.level >= 11 and self.sword_branch == 1:
            best = min(alive, key=self._remaining_to_end)
            return [TerraBeam(cx, cy, best.rect.centerx, best.rect.centery,
                              self.sword_beam_damage(), self.game)]

        # 三阶分支 2「狂星之怒」：从地图右上角发射大量锁敌星星（全场索敌）
        elif self.level >= 11 and self.sword_branch == 2:
            sx = GRID_WIDTH * TILE_SIZE - 120
            sy = 96
            base = math.atan2((GRID_HEIGHT * TILE_SIZE) / 2 - sy,
                              (GRID_WIDTH * TILE_SIZE) / 2 - sx)
            dmg = self.sword_star_damage()
            for _ in range(SWORD_STAR_COUNT):
                ang = base + random.uniform(-0.6, 0.6)
                self.game.stars.append(StarWrath(sx, sy, ang, dmg, self.game,
                                                 self._remaining_to_end))
        return []

    def _apply_sword_damage(self, targets):
        """挥砍本体结算：整次攻击读一次倍率，结算完再按命中数加层。"""
        mult = self.game.sword_combo_mult()
        dmg = max(1, int(self.damage * mult))
        hits = 0
        prev = self.game.damage_element
        self.game.damage_element = "sword"
        try:
            for e in targets:
                if e.health <= 0 or not e.alive():
                    continue
                reward = e.take_damage(dmg, color=SWORD_DAMAGE_COLOR,
                                       scale=self.game.sword_text_scale(1.2),
                                       element="sword")
                self.game.coins += reward
                hits += 1
                # 燃烧 / 中毒不吃连击：派生 DoT 乘上去等于双重收益，
                # 而且燃烧在统计里归火系，乘连击会污染火系归因
                if self.level >= 6 and self.sword_branch == 2:
                    e.apply_burn(int(self.damage * SWORD_BURN_RATIO),
                                 SWORD_BURN_FRAMES)
                elif self.level >= 6 and self.sword_branch == 3:
                    e.apply_poison(SWORD_POISON_BASE
                                   + SWORD_POISON_PER_LV * (self.level - 6))
        finally:
            self.game.damage_element = prev
        self.game.register_sword_hits(hits)

    def _ensure_sword_spin(self):
        """确保旋转特效存在，且贴图与当前等级/分支一致。"""
        img = tower_sprite_path(self.type, self.level,
                                sword_branch=self.sword_branch)
        spin = self.sword_spin
        if spin is not None and spin.img_path == img:
            return
        if spin is not None and spin in self.game.sword_sweeps:
            self.game.sword_sweeps.remove(spin)
        # 用坐标做相位偏移，让多座剑塔的剑不同步，看起来更自然
        phase = (self.x * 37 + self.y * 61) % 360
        self.sword_spin = SwordSpin(self, self.game, img, phase)
        self.game.sword_sweeps.append(self.sword_spin)

    def update_sword_spin(self):
        """每帧检查：范围内有敌人（三阶：场上有敌人）就一直转。"""
        if self.type != TowerType.SWORD:
            return
        if self.level >= 11:
            has = any(e.health > 0 for e in self.game.enemies)
        else:
            r = self.get_effective_range()
            cx, cy = self.rect.centerx, self.rect.centery
            has = any(e.health > 0
                      and (e.rect.centerx - cx) ** 2 + (e.rect.centery - cy) ** 2 <= r * r
                      for e in self.game.enemies)
        if has:
            self.sword_spinning = True
            self._ensure_sword_spin()
        else:
            self.sword_spinning = False

    def draw_range(self, surface):
        if self.type == TowerType.SHIELD or self.type == TowerType.TIME:
            if self.type == TowerType.SHIELD and self.level >= 11:
                return
            if self.level <= 5:
                side = 384
            elif self.level <= 10:
                side = 640
            else:
                side = 896
            cx, cy = self.rect.center
            rect = pygame.Rect(0, 0, side, side)
            rect.center = (cx, cy)
            pygame.draw.rect(surface, (255, 255, 255, 50), rect, 2)
        elif self.type != TowerType.PRODUCTION and not (self.type == TowerType.BOMB and self.is_nuclear):
            pygame.draw.circle(surface, (255, 255, 255, 50), self.rect.center, self.get_effective_range(), 2)

    def in_pulse(self):
        if Enchantment.PULSE_SHIELD not in self.game.enchantments:
            return False
        return self.shield_pulse_timer > 0

    def break_shield(self):
        if not getattr(self, 'has_shield', False):
            return
        self.has_shield = False
        if Enchantment.PULSE_SHIELD in self.game.enchantments:
            self.shield_pulse_timer = 8 * 60

    def update_shield_tower(self):
        if self.shield_pulse_timer > 0:
            self.shield_pulse_timer -= 1
        if self.type != TowerType.SHIELD:
            return

        self.shield_timer += 1

        interval = (95 - self.level * 5) * 60

        if self.level >= 11:
            range_size = GRID_WIDTH
        elif self.level >= 6:
            range_size = 5
        else:
            range_size = 3
        if self.shield_timer >= interval:
            self.shield_timer = 0
            towers_without_shield = []
            for tower in self.game.towers:
                if not getattr(tower, 'has_shield', False) and not tower.in_pulse():
                    if self.level >= 11:
                        towers_without_shield.append(tower)
                    else:
                        dx = abs(tower.x - self.x)
                        dy = abs(tower.y - self.y)
                        if dx <= range_size // 2 and dy <= range_size // 2:
                            towers_without_shield.append(tower)

            if towers_without_shield:
                if self.level >= 6:
                    count = 3
                else:
                    count = 1
                selected = random.sample(towers_without_shield, min(count, len(towers_without_shield)))
                for tower in selected:
                    tower.has_shield = True


class Bullet(pygame.sprite.Sprite):
    def __init__(self, x, y, dx, dy, max_distance, damage, tower_type, game,
                 teleport_chance=0, penetrate=False,
                 freeze_time=0, oneshot_chance=0, stun_time=0, enemies=None, tower_level=1,
                 wind_branch=1, ice_branch=1, flame_branch=1, poison_branch=1, trident_branch=1,
                 teleport_branch=1):
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
        self.damage_element = getattr(game, "damage_element", None)
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
        self.teleport_branch = teleport_branch

        self.lightning_damage = 0
        self.source_tower = None
        self.poison_stacks = 0
        self.physical_branch = 1

        self.last_tile = (int(x) // TILE_SIZE, int(y) // TILE_SIZE)

        img = tower_sprite_path(
            self.tower_type, self.tower_level,
            physical_branch=self.physical_branch,
            ice_branch=self.ice_branch,
            flame_branch=self.flame_branch,
            trident_branch=self.trident_branch,
            wind_branch=self.wind_branch,
            poison_branch=self.poison_branch,
            teleport_branch=self.teleport_branch,
        )
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
            if Enchantment.DENSE in self.game.enchantments:
                branch = self.wind_branch
                if self.source_tower is not None:
                    branch = self.source_tower.wind_branch
                if self.tower_level >= 11:
                    if branch in (1, 2):
                        dmg += int(self.traveled * 5)
                elif branch == 1:
                    dmg += int(self.traveled * 5)

        if self.tower_type == TowerType.TELEPORT and self.teleport_branch == 2:
            dmg = random.randint(0, self.damage * 2)

        mult = self.game.get_enchant_damage_multiplier(self.tower_type)
        if self.tower_type == TowerType.PHYSICAL and Enchantment.FIRE_ARROW in self.game.enchantments:
            mult *= 2
        if self.tower_type == TowerType.PHYSICAL and Enchantment.POWER_V in self.game.enchantments:
            mult *= 2.25
        return int(dmg * mult)

    def calculate_lightning_damage(self):
        ldmg = self.lightning_damage
        if self.tower_type == TowerType.TRIDENT:
            if self.tower_level >= 6:
                gold_bonus = int(self.game.coins * 0.01)
                ldmg += gold_bonus
        if self.game.weather == Weather.MAGNETIC_STORM:
            ldmg *= 2
        # 闪电吃电系伤害加成
        ldmg *= self.game.get_element_damage_multiplier("electric")
        return int(ldmg)

    def update(self):
        self.x += self.dx * self.speed
        self.y += self.dy * self.speed
        self.traveled += self.speed
        self.rect.center = (self.x, self.y)

        if self.traveled >= self.max_distance:
            self.kill()
            return

        if self.tower_type == TowerType.ICE and self.tower_level >= 11 and self.ice_branch == 3:
            col = int(self.x) // TILE_SIZE
            row = int(self.y) // TILE_SIZE
            if (col, row) != self.last_tile:
                self.last_tile = (col, row)
                if random.random() < ICE_WALL_CHANCE:
                    self.spawn_ice_wall(col, row)

        col = int(self.x) // TILE_SIZE
        row = int(self.y) // TILE_SIZE
        grid = self.game.enemy_grid
        for dc in (-1, 0, 1):
            for dr in (-1, 0, 1):
                for enemy in grid.get((col + dc, row + dr), ()):
                    if self.rect.colliderect(enemy.rect):
                        self.on_hit(enemy)
                        return

    def spawn_ice_wall(self, col, row):
        if col < 0 or col >= GRID_WIDTH or row < 1 or row > GRID_HEIGHT:
            return
        if (col, row) not in self.game.path:
            return
        if (col, row) == self.game.start_point or (col, row) == self.game.end_point:
            return
        if self.game.get_tower_at(col, row):
            return
        for wall in self.game.ice_walls:
            if wall.x == col and wall.y == row:
                return
        duration = ICE_WALL_DURATION.get(self.tower_level, 2) * 60
        if self.game.weather == Weather.FIRE_RAIN:
            duration //= 2
        if self.game.frost_combo_active():
            duration *= 2
        wall = IceWall(col, row, self.game)
        wall.duration = duration
        self.game.ice_walls.append(wall)

    def get_damage_color(self):
        if self.tower_type == TowerType.PHYSICAL:
            return WHITE
        elif self.tower_type == TowerType.ICE:
            return ICE_BLUE
        elif self.tower_type == TowerType.TELEPORT:
            return WHITE
        elif self.tower_type == TowerType.FLAME:
            return ORANGE
        elif self.tower_type == TowerType.TRIDENT:
            return ELECTRIC_PURPLE
        elif self.tower_type == TowerType.WIND:
            return MINT
        elif self.tower_type == TowerType.POISON:
            return GREEN
        return RED

    def on_hit(self, enemy):
        prev_element = self.game.damage_element
        if self.damage_element is not None:
            self.game.damage_element = self.damage_element
        final_dmg = self.calculate_final_damage()
        mult = self.game.get_enchant_damage_multiplier(self.tower_type)

        if self.tower_type == TowerType.ICE and self.tower_level >= 11 and self.ice_branch == 1 and enemy.freeze_time > 0:
            bonus = int(abs(self.game.temperature) * 3 * (self.tower_level - 10))
            final_dmg += int(bonus * mult)

        if self.tower_type == TowerType.TELEPORT and self.tower_level >= 11 and self.teleport_branch == 1:
            hp_ratios = {11: 0.004, 12: 0.008, 13: 0.012, 14: 0.016, 15: 0.02}
            hp_bonus = int(enemy.max_health * hp_ratios.get(self.tower_level, 0))
            final_dmg += hp_bonus

        if self.tower_type == TowerType.WIND and self.tower_level >= 11 and self.wind_branch == 1:
            if self.max_distance - self.traveled <= self.speed:
                final_dmg += int(enemy.health * 0.25)

        color = self.get_damage_color()
        reward = enemy.take_damage(final_dmg, color=color)
        self.game.coins += reward
        self.apply_effects(enemy)
        if self.game.endless_greed_active():
            is_greed = self.tower_type in (TowerType.PHYSICAL, TowerType.TELEPORT) or \
                (self.tower_type == TowerType.WIND and self.wind_branch == 1) or \
                (self.tower_type == TowerType.TRIDENT and self.trident_branch == 1)
            if is_greed and random.random() < 0.05:
                self.game.endless_greed_explode(enemy.rect.centerx, enemy.rect.centery)
        self.kill()
        self.game.damage_element = prev_element

    def apply_effects(self, enemy):
        if self.tower_type == TowerType.ICE:
            rain_weathers = (Weather.RAINY, Weather.THUNDERSTORM, Weather.ACID_RAIN, Weather.EXTREME_COLD)
            if self.game.weather not in rain_weathers:
                enemy.apply_slow(0.5, 60)
            freeze_frames = int(self.freeze_time * 60)
            if self.game.frost_combo_active():
                freeze_frames += 30
            enemy.apply_freeze(freeze_frames)
            if self.tower_level >= 11 and self.ice_branch == 1:
                freeze_frames_for_exp = freeze_frames
                if self.freeze_time <= 0:
                    freeze_frames_for_exp = 60
                exp = IceExplosion(enemy.rect.centerx, enemy.rect.centery,
                                   int(self.damage * self.game.get_element_damage_multiplier("ice")),
                                   freeze_frames_for_exp, self.game)
                if self.source_tower is not None:
                    self.source_tower.ice_explosion_visual += 1
                    if self.source_tower.ice_explosion_visual % 2 == 1:
                        self.game.ice_explosions.append(exp)
                else:
                    self.game.ice_explosions.append(exp)
        if self.tower_type == TowerType.TELEPORT:
            if self.teleport_branch == 1:
                if self.game.weather != Weather.MAGNETIC_STORM and random.random() < self.teleport_chance:
                    enemy.teleport_to_start()
                    if assets.teleport_sound:
                        assets.teleport_sound.play()
                if enemy.enemy_type not in (EnemyType.HEROBRINE, EnemyType.FINAL_BOSS) and random.random() < self.oneshot_chance:
                    reward = enemy.take_damage(99999999, color=RED, scale=1.2)
                    self.game.coins += reward
            else:
                if self.tower_level >= 6 and self.tower_level < 11:
                    poison_chance = 0.02
                    poison_stacks = {6: 600, 7: 700, 8: 800, 9: 900, 10: 1000}
                    if random.random() < poison_chance:
                        enemy.apply_poison(poison_stacks.get(self.tower_level, 600))
                elif self.tower_level >= 11:
                    debuffs = ['burn', 'slow', 'speed', 'poison', 'wither', 'broken']
                    debuff = random.choice(debuffs)
                    if debuff == 'burn':
                        if self.game.temperature > 0:
                            rain_weathers = (Weather.RAINY, Weather.THUNDERSTORM, Weather.ACID_RAIN, Weather.EXTREME_COLD)
                            if self.game.weather not in rain_weathers:
                                enemy.apply_burn(self.game.temperature, 999999)
                    elif debuff == 'slow':
                        enemy.apply_slow(0.3, 999999)
                    elif debuff == 'speed':
                        enemy.apply_speed(0.5, 999999)
                    elif debuff == 'poison':
                        enemy.apply_poison(1)
                    elif debuff == 'wither':
                        enemy.apply_wither(999999)
                    elif debuff == 'broken':
                        enemy.broken = True
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
            if Enchantment.FIRE_ARROW in self.game.enchantments:
                enemy.apply_burn(self.game.temperature, 4 * 60)
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
                    reward = e.take_damage(dmg, color=ELECTRIC_PURPLE)
                    self.game.coins += reward
                    e.apply_burn(self.game.temperature, 240)
                    e.on_lightning_hit()
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
                            reward = e.take_damage(dmg, color=ELECTRIC_PURPLE)
                            self.game.coins += reward
                            e.on_lightning_hit()
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
            if self.source_tower and self.source_tower.wind_branch == 2 and self.tower_level >= 11:
                dmg_map = {11: 2000, 12: 4000, 13: 6000, 14: 8000, 15: 10000}
                lightning_dmg = dmg_map.get(self.tower_level, 2500)
                lightning_dmg = int(lightning_dmg * self.game.get_enchant_damage_multiplier(TowerType.WIND))
                col = enemy.rect.centerx // TILE_SIZE
                for e in self.game.enemies:
                    e_col = e.rect.centerx // TILE_SIZE
                    if e_col == col and e.health > 0:
                        reward = e.take_damage(lightning_dmg, color=ELECTRIC_PURPLE)
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
        self.damage_element = getattr(game, "damage_element", None)
        self.enemies = game.enemies
        img = tower_sprite_path(TowerType.BOMB, tower_level,
                                bomb_subtype=bomb_subtype)
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
        mult = self.game.get_enchant_damage_multiplier(TowerType.BOMB)
        prev_element = self.game.damage_element
        if self.damage_element is not None:
            self.game.damage_element = self.damage_element
        explosion = TNTExplosion(self.rect.centerx, self.rect.centery,
                                 int(self.damage * mult), self.tower_level, self.bomb_subtype, self.game)
        self.game.damage_element = prev_element
        self.game.tnt_explosions.append(explosion)
        self.game.try_spawn_crystal_near(self.rect.centerx, self.rect.centery)


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
        self.damage_element = getattr(game, "damage_element", None)
        # 核弹是三阶形态，贴图固定走 9-3-{branch}
        self.raw_img = assets.load_image(
            tower_sprite_path(TowerType.BOMB, 11, bomb_branch=bomb_branch),
            (TILE_SIZE // 2, TILE_SIZE // 2))
        self.image = self.raw_img
        self.rect = self.image.get_rect(center=(x, y))

    def update(self):
        dx = self.target_x - self.x
        dy = self.target_y - self.y
        dist = (dx * dx + dy * dy) ** 0.5
        if dist < self.speed:
            prev_element = self.game.damage_element
            if self.damage_element is not None:
                self.game.damage_element = self.damage_element
            explosion = MushroomExplosion(MAP_CENTER_X, MAP_CENTER_Y,
                                          self.damage, self.tower_level, self.game, self.bomb_branch)
            self.game.damage_element = prev_element
            self.game.mushroom_explosions.append(explosion)
            shockwave = NuclearShockwave(MAP_CENTER_X, MAP_CENTER_Y, self.game, self.bomb_branch)
            self.game.shockwave_effects.append(shockwave)
            self.game.spawn_crystals_fullmap()
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
        self.damage_element = getattr(game, "damage_element", None)
        self.enemies = game.enemies

        # 凋零弹固定是毒系分支 2 的形态
        img = tower_sprite_path(TowerType.POISON, tower_level, poison_branch=2)
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
        prev_element = self.game.damage_element
        if self.damage_element is not None:
            self.game.damage_element = self.damage_element
        if self.tower_level >= 11:
            wither_duration = 720
        else:
            wither_duration = 300
        # 凋零弹的本体伤害吃毒系伤害加成
        final_dmg = int(self.damage * self.game.get_element_damage_multiplier("poison"))

        reward = enemy.take_damage(final_dmg, color=(100, 0, 100))
        self.game.coins += reward

        if self.tower_level >= 6:
            splash = WitherSplash(self.rect.centerx, self.rect.centery, final_dmg, wither_duration, self.game)
            self.game.wither_splashes.append(splash)
        else:
            enemy.apply_wither(wither_duration)

        self.kill()
        self.game.damage_element = prev_element

class TerraBeam(pygame.sprite.Sprite):
    """泰拉刃的剑气弹幕：无限穿透、无衰减，对经过的敌人各结算一次。

    不继承 Bullet 的原因：Bullet.on_hit 结尾无条件 kill()（penetrate 是死代码），
    且构造里写死了给斜 45° 箭矢用的 rotate_angle = angle - 45，不适配竖版剑气图。
    """

    SPEED = SWORD_BEAM_SPEED
    HEAD_RADIUS = SWORD_BEAM_HEAD_RADIUS

    def __init__(self, x, y, tx, ty, damage, game):
        super().__init__()
        self.game = game
        self.x = float(x)
        self.y = float(y)
        dx, dy = tx - x, ty - y
        dist = math.hypot(dx, dy) or 1.0
        self.dx = dx / dist
        self.dy = dy / dist
        self.damage = damage
        self.traveled = 0.0
        self.max_distance = SWORD_BEAM_MAX_DIST
        self.hit_enemies = set()          # 去重，保证同一敌人只掉一次血
        self.damage_element = getattr(game, "damage_element", None)
        # 连击倍率：首次命中时冻结，整条剑气共用一个值。
        # 若每帧重读，剑气自己前面的命中会给后面的命中加伤，等于"边打边加"。
        self.combo_mult = None

        raw = assets.load_image("tower/terra_beam.png")
        # 剑气的【凸面】在原图的右侧，要让凸面朝向飞行方向：
        #   让局部向量 (1,0) 旋转后等于 (dx, dy)
        #   解方程 x'=cos(a)=dx, y'=-sin(a)=dy  =>  a = atan2(-dy, dx)
        # （pygame 正角为逆时针）。只在生成时转一次，之后只改 rect.center。
        self.image = pygame.transform.rotate(
            raw, math.degrees(math.atan2(-self.dy, self.dx)))
        self.rect = self.image.get_rect(center=(int(x), int(y)))

    def update(self):
        self.x += self.dx * self.SPEED
        self.y += self.dy * self.SPEED
        self.traveled += self.SPEED
        self.rect.center = (int(self.x), int(self.y))

        if (self.traveled >= self.max_distance
                or self.rect.right < -600 or self.rect.left > SCREEN_WIDTH + 600
                or self.rect.bottom < -600 or self.rect.top > SCREEN_HEIGHT + 600):
            self.kill()
            return

        col = int(self.x) // TILE_SIZE
        row = int(self.y) // TILE_SIZE
        grid = self.game.enemy_grid
        prev = self.game.damage_element
        self.game.damage_element = self.damage_element
        hits = 0
        try:
            for dc in (-1, 0, 1):
                for dr in (-1, 0, 1):
                    for enemy in grid.get((col + dc, row + dr), ()):
                        if enemy.health <= 0 or enemy in self.hit_enemies:
                            continue
                        # 只用弹头做圆判定：旋转后的 297x520 轴对齐包围盒太大，
                        # 会把剑气两侧一大片空气也判成命中
                        if math.hypot(enemy.rect.centerx - self.x,
                                      enemy.rect.centery - self.y) <= self.HEAD_RADIUS:
                            self.hit_enemies.add(enemy)
                            if self.combo_mult is None:
                                self.combo_mult = self.game.sword_combo_mult()
                            dmg = max(1, int(self.damage * self.combo_mult))
                            reward = enemy.take_damage(
                                dmg, color=SWORD_DAMAGE_COLOR,
                                scale=self.game.sword_text_scale(1.3),
                                element="sword")
                            self.game.coins += reward
                            hits += 1
        finally:
            self.game.damage_element = prev
        self.game.register_sword_hits(hits)
