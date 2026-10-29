import pygame
import random
import math
import assets
import stats
from config import *
from effects import WindExplosion, IceExplosion, DragonBreathPool, LightningEffect, HorizontalLightningEffect, PoisonSplash, TNTExplosion, MushroomExplosion, NuclearShockwave, WitherSplash, IceWall, HellRay
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
    TowerType.ICE:        {1: 1, 2: 1, 3: 4},
    TowerType.TELEPORT:   {1: 2, 2: 2, 3: 2},
    TowerType.FLAME:      {1: 1, 2: 1, 3: 3},
    TowerType.TRIDENT:    {1: 1, 2: 1, 3: 3},
    TowerType.WIND:       {1: 1, 2: 1, 3: 2},
    TowerType.POISON:     {1: 2, 2: 2, 3: 3},
    TowerType.BOMB:       {1: 1, 2: 5, 3: 2},
    TowerType.TIME:       {1: 1, 2: 1, 3: 1},
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
        self.ice_explosion_visual = 0
        self.wind_storm_visual = 0      # 雷神之锤命中特效隔次播放计数器
        self.crouch_energy = 0          # 卧龙：八卦阵能量（满 100 放一座）
        self.hit_energy_cd = 0          # 卧龙：挨打加能量的冷却

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

        if self.type in (TowerType.FLAME, TowerType.ICE):
            self.recalculate_stats()

        self.update_sprite()

    def recalculate_stats(self):
        if self.type == TowerType.FLAME:
            self._recalc_flame()
            return
        if self.type == TowerType.ICE:
            self._recalc_ice()
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

    def is_holy_pot(self):
        """神锅：冰系 Lv11+ 分支 4（射程全屏、随机单体、附带永久冰系破甲）。"""
        return (self.type == TowerType.ICE and self.level >= 11
                and self.ice_branch == HOLY_POT_BRANCH)

    def _recalc_ice(self):
        """冰系数值按等级整体重算；分支 4（神锅）走独立数值表。

        神锅的伤害随温度变化，self.damage 只存「基础值」，
        真正结算时用 holy_pot_damage() 现算（温度每帧都可能变）。
        """
        lv = self.level
        self.damage = 5 + 5 * (lv - 1)
        self.range = TILE_SIZE * 1.5 + (lv - 1) * (TILE_SIZE // 4)
        self.fire_rate = max(30, 60 - (lv - 1) * 6)
        self.freeze_time = round(0.1 * max(0, lv - 5), 1) if lv >= 6 else 0
        if self.is_holy_pot():
            # 全屏射程：取整张地图的对角线，保证任何位置都算在范围内
            self.range = int(math.hypot(GRID_WIDTH * TILE_SIZE, GRID_HEIGHT * TILE_SIZE))
            self.fire_rate = HOLY_POT_FIRE_RATE
            self.freeze_time = 0          # 神锅本体不冻结，控场交给大招
            self.damage = HOLY_POT_DAMAGE_BASE.get(lv, 500)

    def holy_pot_damage(self):
        """神锅单次攻击伤害 = (基础值 + 系数 * |温度|) * 冰系伤害加成。"""
        lv = self.level
        raw = (HOLY_POT_DAMAGE_BASE.get(lv, 500)
               + HOLY_POT_DAMAGE_TEMP.get(lv, 10) * abs(self.game.temperature))
        return max(1, int(raw * self.game.get_enchant_damage_multiplier(TowerType.ICE)))

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
            bullets = self._attack_inner(current_time)
        finally:
            self.game.damage_element = prev_element
        # 卧龙：每打出一次攻击 +1 能量
        if bullets and self.is_crouch_dragon():
            self.gain_energy(CD_ENERGY_PER_ATTACK)
        return bullets

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

        if self.is_holy_pot():
            return self._holy_pot_attack()

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
            if self.game.resonance_counter >= RESONANCE_ATTACKS:
                self.game.resonance_counter = 0
                self.game.trigger_resonance_storm()

        if self.type == TowerType.ICE and self.level >= 11 and self.ice_branch == 2:
            if random.random() < DRAGON_SUMMON_CHANCE:
                dragon = Dragon(self.game.path, "ice", self.level, self.game)
                self.game.dragons.add(dragon)

        if self.type == TowerType.FLAME and self.level >= 11 and self.flame_branch == 2:
            if random.random() < DRAGON_SUMMON_CHANCE:
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
            reward = enemy.take_damage(damage, color=LANTERN_DAMAGE_COLOR, scale=1.3)
            self.game.coins += reward
            enemy.apply_burn(self.game.temperature, LANTERN_BURN_FRAMES)
        return []

    def _holy_pot_attack(self):
        """神锅：向全场随机 1 名敌人发射一枚冰系四芒星，命中后单体结算。

        不走常规的九宫格射程检测 —— 射程就是全屏，直接在全场活着的敌人里抽一个。
        """
        alive = [e for e in self.game.enemies if e.health > 0]
        if not alive:
            return []
        target = random.choice(alive)
        bolt = IceStarBolt(self.rect.centerx, self.rect.centery, target,
                           self.holy_pot_damage(), self.game)
        # 「臻品呈现」：场上所有神锅共用同一个计数，凑满 MASTERPIECE_ATTACKS 次就放大招。
        # 这里刻意对齐雷神之锤的 resonance_counter —— 按塔各算各的话，
        # 一座锅要自己打满 120 次（1 秒 1 发 = 2 分钟）才有反应，铺了 9 座也还是 2 分钟，
        # 体感就是「打了半天无事发生」。
        if self.game.masterpiece_active():
            self.game.masterpiece_counter += 1
            if self.game.masterpiece_counter >= MASTERPIECE_ATTACKS:
                self.game.masterpiece_counter = 0
                self.game.trigger_masterpiece_ultimate()
        return [bolt]

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
        elif self.is_holy_pot():
            # 射程就是全屏，画圆没意义（半径比屏幕还大），直接不画
            return
        elif self.type != TowerType.PRODUCTION and not (self.type == TowerType.BOMB and self.is_nuclear):
            pygame.draw.circle(surface, (255, 255, 255, 50), self.rect.center, self.get_effective_range(), 2)

    def in_pulse(self):
        if Enchantment.PULSE_SHIELD not in self.game.enchantments:
            return False
        return self.shield_pulse_timer > 0

    def is_crouch_dragon(self):
        """卧龙：三叉戟塔 Lv11+ 分支 3。"""
        return (self.type == TowerType.TRIDENT and self.level >= 11
                and self.trident_branch == CROUCH_DRAGON_BRANCH)

    def is_invincible(self):
        """卧龙自身免疫一切伤害（锁定 / 酸雨 / 爆炸），但护盾照常会被打破。"""
        return self.is_crouch_dragon()

    def gain_energy(self, amount):
        """加能量；每满 100 就在道路上放一座八卦阵（多余的继续留着）。"""
        if not self.is_crouch_dragon() or amount <= 0:
            return
        self.crouch_energy += amount
        while self.crouch_energy >= CD_ENERGY_FULL:
            self.crouch_energy -= CD_ENERGY_FULL
            self.game.spawn_bagua_array(self)

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
                # 冰霜炸弹的伤害全部走这次 AOE：基础攻击力 + 3/6/9/12/15 * |温度|
                bomb_dmg = self.damage + ICE_BOMB_TEMP_MULT.get(self.tower_level, 15) * abs(self.game.temperature)
                exp = IceExplosion(enemy.rect.centerx, enemy.rect.centery,
                                   max(1, int(bomb_dmg * self.game.get_element_damage_multiplier("ice"))),
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
                elif self.trident_branch == 2 and random.random() < DRAGON_SUMMON_CHANCE:
                    # 必须显式判断分支 2：原来只写 elif，卧龙（分支 3）会掉进这里召唤电龙
                    dragon = Dragon(self.game.path, 'electric', self.tower_level, self.game)
                    self.game.dragons.add(dragon)
        if self.tower_type == TowerType.WIND:
            if self.source_tower:
                enemy.apply_knockback(self.source_tower.wind_knockback)
                if self.tower_level >= 6 and enemy.enemy_type not in (EnemyType.IRON_ARMORED, EnemyType.GOLD_ARMORED, EnemyType.DIAMOND_ARMORED, EnemyType.NETHERITE_ARMORED):
                    enemy.wind_mark_tower = self.source_tower
            if self.source_tower and self.source_tower.wind_branch == 2 and self.tower_level >= 11:
                lightning_dmg = WIND_STORM_DAMAGE.get(self.tower_level, 2500)
                lightning_dmg = int(lightning_dmg * self.game.get_enchant_damage_multiplier(TowerType.WIND))
                # 落雷点是子弹命中的那名敌人，AOE 以它为圆心
                bx, by = enemy.rect.centerx, enemy.rect.centery
                radius_sq = WIND_STORM_RADIUS * WIND_STORM_RADIUS
                for e in self.game.enemies:
                    if e.health <= 0:
                        continue
                    if (e.rect.centerx - bx) ** 2 + (e.rect.centery - by) ** 2 > radius_sq:
                        continue
                    # 雷神之锤的闪电飘字用薄荷色，和风系伤害保持一致
                    # （不要用 ELECTRIC_PURPLE，那是三叉戟电系的颜色）
                    reward = e.take_damage(lightning_dmg, color=MINT, element="wind")
                    self.game.coins += reward
                # 雷神之锤的命中特效固定用 resonance_storm 原尺寸帧，不缩放。
                # 隔次播放（和冰霜炸弹同一个套路）：这套 12 帧 × 282px 的爆裂
                # 每次都放会明显掉帧，一半频率肉眼几乎看不出差别。
                self.source_tower.wind_storm_visual += 1
                # 每 N 次命中播一次：取余落在 1..N 中的首个周期时触发
                if (self.source_tower.wind_storm_visual - 1) % WIND_STORM_VISUAL_EVERY == 0:
                    self.game.add_resonance_burst(bx, by)
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

class IceStarBolt(pygame.sprite.Sprite):
    """神锅的冰系四芒星子弹：锁定单个目标飞行，命中后单体结算 + 永久冰系破甲。

    为什么不继承 Bullet：Bullet 是「给定方向直线飞行 + 射程耗尽自灭」的模型，
    而这里要的是追踪单个敌人、命中即结算，两者除了都用贴图之外没有共性。
    """

    MAX_LIFE = 300          # 5 秒还没命中就自毁，避免目标反复消失时子弹乱飞

    def __init__(self, x, y, target, damage, game):
        super().__init__()
        self.game = game
        self.x = float(x)
        self.y = float(y)
        self.target = target
        self.damage = damage
        self.speed = HOLY_POT_BOLT_SPEED
        self.spin = 0.0
        self.life = 0
        self.raw = assets.ice_star_img
        self.image = self.raw
        self.rect = self.image.get_rect(center=(int(x), int(y)))

    def _retarget(self):
        """原目标死了就改打最近的活敌人；一个都没有就返回 None。"""
        best, best_d = None, None
        for e in self.game.enemies:
            if e.health <= 0 or not e.alive():
                continue
            d = (e.rect.centerx - self.x) ** 2 + (e.rect.centery - self.y) ** 2
            if best_d is None or d < best_d:
                best, best_d = e, d
        return best

    def update(self):
        self.life += 1
        if self.life > self.MAX_LIFE:
            self.kill()
            return

        target = self.target
        if target is None or target.health <= 0 or not target.alive():
            target = self._retarget()
            self.target = target
        if target is None:
            self.kill()
            return

        tx, ty = target.rect.center
        dx = tx - self.x
        dy = ty - self.y
        dist = math.hypot(dx, dy)
        if dist <= self.speed + 10:
            self._hit(target)
            return

        self.x += dx / dist * self.speed
        self.y += dy / dist * self.speed
        self.spin = (self.spin + HOLY_POT_BOLT_SPIN) % 360
        self.image = pygame.transform.rotate(self.raw, self.spin)
        self.rect = self.image.get_rect(center=(int(self.x), int(self.y)))

    def _hit(self, enemy):
        prev_element = self.game.damage_element
        self.game.damage_element = "ice"
        try:
            reward = enemy.take_damage(self.damage, color=ICE_BLUE, scale=1.2,
                                       element="ice")
            self.game.coins += reward
            enemy.apply_ice_broken()
            self.game.add_ice_star_burst(enemy.rect.centerx, enemy.rect.centery)
        finally:
            self.game.damage_element = prev_element
        self.kill()
