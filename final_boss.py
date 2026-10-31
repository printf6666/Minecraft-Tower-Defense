"""第 100 波最终 BOSS：终焉奥米伽 (OMEGA)。

与第 50 波的 Herobrine 不同，奥米伽**不沿路径行走**：
它悬浮在战场上空，像泰拉瑞亚的猪龙鱼公爵 / 光之女皇 / 石巨人那样，
自由选择落点、冲刺、瞬移，用一条条“指令”改写战场。

本模块包含 BOSS 本体 AI、技能特效与所有表现层数据，
只通过 game 上的少量钩子接入主循环（见 game.py 中的 boss_* 字段）。
"""

import math
import random

import pygame

import assets
import audio
from config import *
from enemy import Enemy
from effects import TNTExplosion

CORE_SIZE = FINAL_BOSS_CORE_SIZE
# 以最初 256px 版本为基准的缩放系数（1.5 倍）
S = CORE_SIZE / 256.0
VISUALS = {}

# 伤害飘字点位表（相对 BOSS 中心）：(左右, x 起点, y)
#   左右：-1 左 / 1 右 / 0 正上方居中
#   第 1、2 行为左右交替的两行；第 5 个点位在正上方居中
DMG_TEXT_SLOTS = [
    (-1, 85, -155),
    (1, 85, -155),
    (-1, 120, -50),
    (1, 120, -50),
    (0, 0, -220),
]
DMG_TEXT_BAND_W = 50


# ==========================================================================================
#  预渲染资源（只做一次，避免每帧缩放）
# ==========================================================================================

def _radial_glow(radius, color, max_alpha=110):
    size = radius * 2
    surf = pygame.Surface((size, size), pygame.SRCALPHA)
    steps = 24
    for i in range(steps):
        r = int(radius * (1 - i / steps))
        a = int(max_alpha * (i / steps) ** 1.7)
        if r > 0 and a > 0:
            pygame.draw.circle(surf, (*color, a), (radius, radius), r)
    return surf


def _build_core():
    size = CORE_SIZE
    surf = pygame.Surface((size, size), pygame.SRCALPHA)
    cx = cy = size // 2

    # 外层八边形装甲
    outer = [(cx + 124 * S * math.cos(math.radians(22.5 + 45 * i)),
              cy + 124 * S * math.sin(math.radians(22.5 + 45 * i))) for i in range(8)]
    pygame.draw.polygon(surf, (16, 7, 28), outer)
    pygame.draw.polygon(surf, (104, 44, 178), outer, max(3, int(5 * S)))
    pygame.draw.polygon(surf, (60, 24, 104), outer, 1)

    # 内层装甲
    inner = [(cx + 101 * S * math.cos(math.radians(22.5 + 45 * i)),
              cy + 101 * S * math.sin(math.radians(22.5 + 45 * i))) for i in range(8)]
    pygame.draw.polygon(surf, (38, 14, 60), inner)
    pygame.draw.polygon(surf, (168, 84, 244), inner, max(1, int(2 * S)))

    # 命令方块核心（染上一层虚空紫，和普通命令方块区分开）
    cb_size = int(152 * S)
    cb = pygame.transform.scale(assets.command_block_img, (cb_size, cb_size))
    cb_x = cx - cb_size // 2
    surf.blit(cb, (cb_x, cb_x))
    tint = pygame.Surface((cb_size, cb_size), pygame.SRCALPHA)
    tint.fill((120, 40, 200, 78))
    surf.blit(tint, (cb_x, cb_x))
    pygame.draw.rect(surf, (226, 170, 255), (cb_x, cb_x, cb_size, cb_size), max(2, int(4 * S)))
    outer_pad = int(8 * S)
    pygame.draw.rect(surf, (90, 30, 140),
                     (cb_x - outer_pad, cb_x - outer_pad, cb_size + outer_pad * 2, cb_size + outer_pad * 2), 2)

    # 裂纹
    margin = int(28 * S)
    crack_reach = int(46 * S)
    for _ in range(16):
        x1 = random.randint(margin, size - margin)
        y1 = random.randint(margin, size - margin)
        x2 = x1 + random.randint(-crack_reach, crack_reach)
        y2 = y1 + random.randint(-crack_reach, crack_reach)
        pygame.draw.line(surf, (206, 156, 255), (x1, y1), (x2, y2), max(1, int(2 * S)))

    # 四角锚点
    anchor = int(96 * S)
    for dx, dy in ((-anchor, -anchor), (anchor, -anchor), (-anchor, anchor), (anchor, anchor)):
        half = int(7 * S)
        pygame.draw.rect(surf, (255, 255, 255), (cx + dx - half, cy + dy - half, half * 2, half * 2))
        pygame.draw.rect(surf, (120, 60, 200),
                         (cx + dx - half - 3, cy + dy - half - 3, half * 2 + 6, half * 2 + 6), 2)

    # 两只“眼睛”
    eye_dx = int(38 * S)
    for dx in (-eye_dx, eye_dx):
        pygame.draw.rect(surf, (255, 255, 255),
                         (cx + dx - int(12 * S), cy - int(8 * S), int(24 * S), int(9 * S)))
    return surf


def _build_shard():
    side = max(30, int(46 * S))
    chunk_side = max(20, int(34 * S))
    pad = (side - chunk_side) // 2
    surf = pygame.Surface((side, side), pygame.SRCALPHA)
    chunk = pygame.transform.scale(assets.command_block_img, (chunk_side, chunk_side))
    surf.blit(chunk, (pad, pad))
    pygame.draw.rect(surf, (210, 150, 255), (pad, pad, chunk_side, chunk_side), 2)
    return surf


def _ensure_visuals():
    if VISUALS:
        return
    VISUALS["core"] = _build_core()
    VISUALS["shard"] = _build_shard()
    VISUALS["glow"] = _radial_glow(int(300 * S), (150, 60, 255), 105)
    VISUALS["glow_red"] = _radial_glow(int(340 * S), (255, 70, 50), 120)
    VISUALS["flash"] = pygame.Surface((CORE_SIZE, CORE_SIZE), pygame.SRCALPHA)
    VISUALS["flash"].fill((255, 255, 255, 70))


# ==========================================================================================
#  战斗特效
# ==========================================================================================

class BossShockwave:
    def __init__(self, x, y, radius=260, duration=30, color=(170, 90, 255), width=4):
        self.x = int(x)
        self.y = int(y)
        self.max_radius = radius
        self.duration = max(1, duration)
        self.timer = 0
        self.color = color
        self.width = width

    def update(self):
        self.timer += 1
        return self.timer < self.duration

    def draw(self, screen):
        p = self.timer / self.duration
        radius = int(self.max_radius * p)
        if radius <= 0:
            return
        width = max(1, int(self.width * (1.0 - p)) + 1)
        pygame.draw.circle(screen, self.color, (self.x, self.y), radius, width)


class BossRune:
    """向外飞散的指令碎片，纯表现。"""

    def __init__(self, x, y, speed=None, angle=None, color=None):
        self.x = float(x)
        self.y = float(y)
        angle = random.uniform(0, math.tau) if angle is None else angle
        speed = random.uniform(3.0, 8.0) if speed is None else speed
        self.vx = math.cos(angle) * speed
        self.vy = math.sin(angle) * speed
        self.life = random.randint(34, 64)
        self.timer = 0
        self.color = color or random.choice([(190, 120, 255), (255, 120, 220), (150, 200, 255)])

    def update(self):
        self.x += self.vx
        self.y += self.vy
        self.vx *= 0.97
        self.vy *= 0.97
        self.timer += 1
        return self.timer < self.life

    def draw(self, screen):
        a = 1.0 - self.timer / self.life
        size = 3 + int(7 * a)
        pygame.draw.rect(screen, self.color,
                         (int(self.x) - size, int(self.y) - size, size * 2, size * 2), 2)


class BossPortal:
    """召唤门：延迟后从传送门里爬出一只小怪。"""

    def __init__(self, col, row, game, delay, enemy_type, path_index):
        self.col = col
        self.row = row
        self.x = col * TILE_SIZE + TILE_SIZE // 2
        self.y = row * TILE_SIZE + TILE_SIZE // 2
        self.game = game
        self.timer = max(1, delay)
        self.enemy_type = enemy_type
        self.path_index = path_index
        self.spawned = False
        self.fade = 30

    def update(self):
        if not self.spawned:
            self.timer -= 1
            if self.timer <= 0:
                self._spawn()
            return True
        self.fade -= 1
        return self.fade > 0

    def _spawn(self):
        self.spawned = True
        boss = getattr(self.game, "final_boss", None)
        if boss is None or getattr(boss, "dying", False):
            # BOSS 已经消失，传送门自然失效
            return
        path = self.game.path
        idx = max(0, min(self.path_index, len(path) - 2))
        enemy = Enemy(path, self.enemy_type, self.game)
        enemy.path_index = idx
        enemy.pos_x = float(self.x)
        enemy.pos_y = float(self.y)
        enemy.rect.center = (self.x, self.y)
        phase = boss.phase if boss is not None else 1
        # 召唤物血量表跟随 BOSS（奥米伽 / 阿尔法各有一套，均不套波数膨胀）
        table = getattr(boss, "minion_health_table", FINAL_BOSS_MINION_HEALTH)
        hp = table.get(self.enemy_type, 60_000_000)
        hp = int(hp * (1.0 + 0.2 * (phase - 1)))
        enemy.max_health = hp
        enemy.health = hp
        self.game.enemies.add(enemy)
        self.game.boss_shockwaves.append(
            BossShockwave(self.x, self.y, radius=110, duration=18, color=(190, 110, 255), width=3))

    def draw(self, screen):
        if self.spawned:
            p = self.fade / 30.0
            radius = int(70 * (0.4 + 0.6 * p))
        else:
            p = 1.0 - self.timer / 60.0
            radius = int(12 + 58 * min(1.0, max(0.0, p)))
        if radius <= 0:
            return
        color = (170, 80, 255)
        pygame.draw.circle(screen, color, (self.x, self.y), radius, 3)
        pygame.draw.circle(screen, (255, 210, 255), (self.x, self.y), max(2, radius // 3), 2)
        for i in range(4):
            ang = self.game.game_time * 0.06 + i * math.pi / 2
            px = self.x + math.cos(ang) * radius
            py = self.y + math.sin(ang) * radius
            pygame.draw.rect(screen, (230, 180, 255), (int(px) - 4, int(py) - 4, 8, 8))


class BossStrike:
    """指令·执行：在炮塔头顶标记符文，读条结束后落雷裁决。"""

    def __init__(self, col, row, game, delay=150):
        self.col = col
        self.row = row
        self.x = col * TILE_SIZE + TILE_SIZE // 2
        self.y = row * TILE_SIZE + TILE_SIZE // 2
        self.game = game
        self.timer = max(1, delay)
        self.delay = self.timer
        self.state = "warn"
        self.after = 26

    def update(self):
        if self.state == "warn":
            self.timer -= 1
            if self.timer <= 0:
                self._resolve()
                self.state = "flash"
            return True
        self.after -= 1
        return self.after > 0

    def _resolve(self):
        self.game.add_lightning(self.x, 800, True)
        tower = self.game.get_tower_at(self.col, self.row)
        self.game.boss_shockwaves.append(
            BossShockwave(self.x, self.y, radius=150, duration=22, color=(255, 90, 70), width=5))
        if tower is None:
            return
        if tower.in_pulse():
            return
        if getattr(tower, "has_shield", False):
            tower.break_shield()
            self.game.trigger_shield_burst(tower)
            self.game.notify_tower_hit(tower)
            return
        if tower.is_invincible():
            self.game.notify_tower_hit(tower)   # 免疫也要算挨打
            return                     # 卧龙免疫锁定
        # 指令·执行只“锁定”炮塔，真正永久删除留给抹除线与世界重载
        tower.disabled_timer = max(getattr(tower, "disabled_timer", 0), 12 * 60)
        self.game.notify_tower_hit(tower)
        self.game.tnt_explosions.append(TNTExplosion(self.x, self.y, 0, 0, None, self.game))

    def draw(self, screen):
        if self.state == "warn":
            p = 1.0 - self.timer / self.delay
            radius = int(TILE_SIZE * (1.0 - 0.55 * p))
            color = (255, 60, 60)
            pygame.draw.circle(screen, color, (self.x, self.y), radius, 3)
            pygame.draw.circle(screen, (255, 200, 120), (self.x, self.y), max(6, radius // 3), 2)
            for i in range(4):
                ang = self.game.game_time * 0.08 + i * math.pi / 2
                px = self.x + math.cos(ang) * radius
                py = self.y + math.sin(ang) * radius
                pygame.draw.rect(screen, color, (int(px) - 5, int(py) - 5, 10, 10))
        else:
            alpha = self.after / 26.0
            radius = int(TILE_SIZE * 1.1 * (1.0 - alpha) + 40)
            pygame.draw.circle(screen, (255, 220, 180), (self.x, self.y), radius, 3)


class DeleteBeam:
    """指令·抹除：横贯或纵贯整张地图的删除线。"""

    def __init__(self, game, vertical, index, telegraph=90):
        self.game = game
        self.vertical = vertical
        self.index = index
        self.timer = max(1, telegraph)
        self.telegraph = self.timer
        self.state = "warn"
        self.after = 34
        if vertical:
            self.x = index * TILE_SIZE + TILE_SIZE // 2
            self.y = (1 + GRID_HEIGHT) * TILE_SIZE // 2
        else:
            self.x = GRID_WIDTH * TILE_SIZE // 2
            self.y = index * TILE_SIZE + TILE_SIZE // 2

    def update(self):
        if self.state == "warn":
            self.timer -= 1
            if self.timer <= 0:
                self._resolve()
                self.state = "fire"
            return True
        self.after -= 1
        return self.after > 0

    def _resolve(self):
        victims = []
        for tower in list(self.game.towers):
            hit = (tower.x == self.index) if self.vertical else (tower.y == self.index)
            if hit:
                victims.append(tower)
        random.shuffle(victims)
        destroyed = 0
        for tower in victims:
            if tower.in_pulse():
                continue
            if getattr(tower, "has_shield", False):
                tower.break_shield()
                self.game.trigger_shield_burst(tower)
                self.game.notify_tower_hit(tower)
                continue
            if tower.is_invincible():
                self.game.notify_tower_hit(tower)
                continue               # 卧龙免疫抹除与锁定
            if destroyed < 3:
                # 一条删除线最多抹除 3 座炮塔，其余只被锁定，避免一波清空防线
                self.game.notify_tower_hit(tower)
                self.game.destroy_tower_by_boss(tower)
                destroyed += 1
            else:
                tower.disabled_timer = max(getattr(tower, "disabled_timer", 0), 8 * 60)
                self.game.notify_tower_hit(tower)
        if self.vertical:
            for row in range(1, GRID_HEIGHT + 1, 2):
                self.game.add_lightning(self.x, row * TILE_SIZE + TILE_SIZE // 2, True)
        else:
            for col in range(0, GRID_WIDTH, 2):
                self.game.add_lightning(col * TILE_SIZE + TILE_SIZE // 2, self.y, True)
        self.game.boss_shockwaves.append(
            BossShockwave(self.x, self.y, radius=420, duration=30, color=(255, 70, 60), width=6))

    def draw(self, screen):
        if self.state == "warn":
            p = 1.0 - self.timer / self.telegraph
            color = (255, 40, 40)
            width = 2 + int(3 * p)
            if self.vertical:
                x = self.index * TILE_SIZE + TILE_SIZE // 2
                pygame.draw.line(screen, color, (x, TILE_SIZE), (x, (1 + GRID_HEIGHT) * TILE_SIZE), width)
                pygame.draw.rect(screen, (255, 120, 120),
                                 (x - TILE_SIZE // 2, TILE_SIZE, TILE_SIZE, GRID_HEIGHT * TILE_SIZE), 1)
            else:
                y = self.index * TILE_SIZE + TILE_SIZE // 2
                pygame.draw.line(screen, color, (0, y), (GRID_WIDTH * TILE_SIZE, y), width)
                pygame.draw.rect(screen, (255, 120, 120),
                                 (0, y - TILE_SIZE // 2, GRID_WIDTH * TILE_SIZE, TILE_SIZE), 1)
        else:
            fade = self.after / 34.0
            width = max(2, int(26 * fade))
            color = (255, 235, 220)
            if self.vertical:
                x = self.index * TILE_SIZE + TILE_SIZE // 2
                pygame.draw.line(screen, (255, 90, 70), (x, TILE_SIZE),
                                 (x, (1 + GRID_HEIGHT) * TILE_SIZE), width + 10)
                pygame.draw.line(screen, color, (x, TILE_SIZE), (x, (1 + GRID_HEIGHT) * TILE_SIZE), width)
            else:
                y = self.index * TILE_SIZE + TILE_SIZE // 2
                pygame.draw.line(screen, (255, 90, 70), (0, y),
                                 (GRID_WIDTH * TILE_SIZE, y), width + 10)
                pygame.draw.line(screen, color, (0, y), (GRID_WIDTH * TILE_SIZE, y), width)


class SeedFireball:
    """阿尔法·下界阶段：恶魂火球。从 BOSS 中心直线飞向目标炮塔。

    命中：护盾挡下（碎盾）→ 脉冲免疫 → 卧龙免疫 → 否则锁定 4 秒 + 爆炸。
    """

    def __init__(self, game, sx, sy, tx, ty, frames=45):
        self.game = game
        self.sx, self.sy = float(sx), float(sy)
        self.tx, self.ty = float(tx), float(ty)
        self.frames = max(1, frames)
        self.timer = 0
        self.x, self.y = self.sx, self.sy
        self.trail = []

    def update(self):
        self.timer += 1
        p = min(1.0, self.timer / self.frames)
        self.x = self.sx + (self.tx - self.sx) * p
        self.y = self.sy + (self.ty - self.sy) * p
        self.trail.append((self.x, self.y))
        if len(self.trail) > 8:
            self.trail.pop(0)
        if self.timer >= self.frames:
            self._resolve()
            return False
        return True

    def _resolve(self):
        col = int(self.tx) // TILE_SIZE
        row = int(self.ty) // TILE_SIZE
        tower = self.game.get_tower_at(col, row)
        self.game.tnt_explosions.append(
            TNTExplosion(int(self.tx), int(self.ty), 0, 0, None, self.game))
        self.game.boss_shockwaves.append(
            BossShockwave(int(self.tx), int(self.ty), radius=150, duration=22,
                          color=(255, 140, 60), width=5))
        if tower is None:
            return
        if tower.in_pulse():
            return
        if getattr(tower, "has_shield", False):
            tower.break_shield()
            self.game.trigger_shield_burst(tower)
            self.game.notify_tower_hit(tower)
            return
        if tower.is_invincible():
            self.game.notify_tower_hit(tower)
            return
        tower.disabled_timer = max(getattr(tower, "disabled_timer", 0), 4 * 60)
        self.game.notify_tower_hit(tower)

    def draw(self, screen):
        n = len(self.trail)
        for i, (x, y) in enumerate(self.trail):
            a = (i + 1) / max(1, n)
            pygame.draw.circle(screen, (255, int(90 + 90 * a), 30),
                               (int(x), int(y)), int(4 + 10 * a))
        pygame.draw.circle(screen, (255, 220, 120), (int(self.x), int(self.y)), 14)
        pygame.draw.circle(screen, (255, 255, 220), (int(self.x), int(self.y)), 6)


class EndCrystalEnemy(Enemy):
    """末影水晶：阿尔法第 3 阶段的可攻击召唤物。

    站在 BOSS 附近不动，只要有一颗活着，每 10 秒为阿尔法回复一层血。
    可以被普攻 / DoT 击碎（奖励 0），不会移动、不存在「走到终点」。
    """

    def __init__(self, path, game, x, y):
        super().__init__(path, EnemyType.END_CRYSTAL, game)
        self.max_health = ALPHA_END_CRYSTAL_HEALTH
        self.health = self.max_health
        self.reward = 0
        self.speed = 0
        self.base_speed = 0
        self.pos_x = float(x)
        self.pos_y = float(y)
        self.rect.center = (int(x), int(y))

    def update(self):
        if self.health <= 0:
            return False
        # 复用 DoT 结算（燃烧 / 中毒 / 凋零都能磨水晶），但不移动、不推进路径
        self.update_status_effects()
        return False


# ==========================================================================================
#  BOSS 本体
# ==========================================================================================

class FinalBoss(Enemy):
    # 第 100/150 波 BOSS 免疫一切控制（击退/减速/冰冻/眩晕）。
    # apply_slow/apply_speed/apply_freeze/apply_stun/apply_knockback/apply_wind
    # 均已重写为空实现；game 里少数效果会绕过 apply_* 直接写
    # freeze_time/stun_time，写入前须检查此标记（见 game.apply_hard_freeze /
    # apply_hard_stun）。
    CONTROL_IMMUNE = True

    MOVE_INTERVAL = {1: 150, 2: 120, 3: 95, 4: 75}
    CAST_COOLDOWN = {1: 235, 2: 195, 3: 165, 4: 130}

    def __init__(self, path, enemy_type, game):
        super().__init__(path, enemy_type, game)
        _ensure_visuals()

        self.max_health = FINAL_BOSS_LAYER_HEALTH
        self.health = self.max_health
        self.total_layers = FINAL_BOSS_LAYERS
        self.current_layer = FINAL_BOSS_LAYERS
        self.phase = 1
        self.reward = 0
        self.speed = 2.0
        self.base_speed = 2.0
        self.is_boss = True

        self.image = VISUALS["core"]
        self.rect = self.image.get_rect()

        self.pos_x = float(GRID_WIDTH * TILE_SIZE // 2)
        self.pos_y = float((1 + GRID_HEIGHT) * TILE_SIZE // 2)
        self.anchor = (self.pos_x, self.pos_y)
        self.rect.center = (int(self.pos_x), int(self.pos_y))

        self.move_timer = 90
        self.bob_phase = 0.0
        self.spin = 0.0
        self.dmg_text_slot = -1
        self._dmg_text_vy = -2.0
        self.dash_timer = 0
        self.dash_vx = 0.0
        self.dash_vy = 0.0
        self.dash_cooldown = 0
        self.contact_cooldown = 0
        self.trail = []
        self.teleport_flash = 0

        self.cast_cooldown = 200
        self.cast_name = ""
        self.last_skill = None

        self.reloading = False
        self.reload_timer = 0
        self.reload_total = 0
        self.stun_timer = 0
        self.invuln_timer = 90
        self.hit_flash = 0
        self.layer_flash = 0
        self.acid_cooldown = 8 * 60

        self.dying = False
        self.death_timer = 0

    # ------------------------------------------------------------------ 更新

    def update(self):
        if self.dying:
            self._update_death()
            return False
        if self.health <= 0:
            return False

        # 无敌帧必须无条件倒计时：换阶段/破层给的无敌若因控制减益提前
        # return 而停止倒数，BOSS 会表现为永久锁血（历史 bug）。
        self.invuln_timer = max(0, self.invuln_timer - 1)

        if super().update_status_effects():
            return False

        self.spin += 0.02
        self.hit_flash = max(0, self.hit_flash - 1)
        self.layer_flash = max(0, self.layer_flash - 1)
        self.teleport_flash = max(0, self.teleport_flash - 1)
        self.contact_cooldown = max(0, self.contact_cooldown - 1)
        self.acid_cooldown = max(0, self.acid_cooldown - 1)

        if self.stun_timer > 0:
            # 被打断后的硬直：停在原地，不移动也不放技能
            self.stun_timer -= 1
            self._sync_rect()
            return False

        self._update_movement()
        self._update_casting()
        return False

    def _sync_rect(self):
        bob = 0 if (self.dash_timer > 0 or self.reloading) else math.sin(self.bob_phase) * 12
        self.pos_x = max(FINAL_BOSS_ARENA_LEFT, min(FINAL_BOSS_ARENA_RIGHT, self.pos_x))
        self.pos_y = max(FINAL_BOSS_ARENA_TOP, min(FINAL_BOSS_ARENA_BOTTOM, self.pos_y))
        self.rect.center = (int(self.pos_x), int(self.pos_y + bob))

    def _hover_speed(self):
        return 1.1 + 0.35 * self.phase

    def _update_movement(self):
        self.bob_phase += 0.045

        if self.dash_timer > 0:
            self.dash_timer -= 1
            self.pos_x += self.dash_vx
            self.pos_y += self.dash_vy
            self.trail.append([self.pos_x, self.pos_y, 16])
            if len(self.trail) > 9:
                self.trail.pop(0)
            self._contact_damage()
        elif not self.reloading and self.stun_timer <= 0:
            if self.move_timer > 0:
                self.move_timer -= 1
            else:
                self._choose_move()
            ax, ay = self.anchor
            dx = ax - self.pos_x
            dy = ay - self.pos_y
            dist = math.hypot(dx, dy)
            speed = self._hover_speed()
            if dist > speed:
                self.pos_x += dx / dist * speed
                self.pos_y += dy / dist * speed
            else:
                self.pos_x, self.pos_y = ax, ay

        for i in range(len(self.trail) - 1, -1, -1):
            self.trail[i][2] -= 1
            if self.trail[i][2] <= 0:
                self.trail.pop(i)

        self._sync_rect()

    def _choose_move(self):
        self.move_timer = self.MOVE_INTERVAL[self.phase]
        roll = random.random()
        if self.phase == 1:
            self._set_anchor()
        elif self.phase == 2:
            if roll < 0.45:
                self._start_dash()
            else:
                self._set_anchor()
        elif self.phase == 3:
            if roll < 0.34:
                self._teleport()
            elif roll < 0.75:
                self._start_dash()
            else:
                self._set_anchor()
        else:
            if roll < 0.44:
                self._teleport()
            elif roll < 0.9:
                self._start_dash()
            else:
                self._set_anchor()

    def _random_anchor(self):
        if self.game.towers and random.random() < 0.55:
            tower = random.choice(list(self.game.towers))
            ax = tower.rect.centerx + random.randint(-2, 2) * TILE_SIZE
            ay = tower.rect.centery - random.randint(1, 3) * TILE_SIZE
        else:
            ax = random.randint(FINAL_BOSS_ARENA_LEFT, FINAL_BOSS_ARENA_RIGHT)
            ay = random.randint(FINAL_BOSS_ARENA_TOP, FINAL_BOSS_ARENA_BOTTOM)
        ax = max(FINAL_BOSS_ARENA_LEFT, min(FINAL_BOSS_ARENA_RIGHT, ax))
        ay = max(FINAL_BOSS_ARENA_TOP, min(FINAL_BOSS_ARENA_BOTTOM, ay))
        return float(ax), float(ay)

    def _set_anchor(self):
        self.anchor = self._random_anchor()

    def _start_dash(self):
        target_x, target_y = self._random_anchor()
        dx = target_x - self.pos_x
        dy = target_y - self.pos_y
        dist = math.hypot(dx, dy)
        if dist < 1:
            return
        speed = 15.0 + self.phase * 2.5
        self.dash_vx = dx / dist * speed
        self.dash_vy = dy / dist * speed
        self.dash_timer = int(max(12, min(46, dist / speed)))
        self.anchor = (target_x, target_y)
        self.move_timer = 30

    def _teleport(self):
        old_x, old_y = self.pos_x, self.pos_y
        self.anchor = self._random_anchor()
        self.pos_x, self.pos_y = self.anchor
        self.teleport_flash = 18
        self.game.boss_shockwaves.append(
            BossShockwave(old_x, old_y, radius=220, duration=26, color=(150, 80, 255), width=5))
        self.game.boss_shockwaves.append(
            BossShockwave(self.pos_x, self.pos_y, radius=260, duration=26, color=(255, 120, 255), width=5))
        if assets.teleport_sound:
            assets.teleport_sound.play()
        self._disable_nearby_towers(self.pos_x, self.pos_y, radius=TILE_SIZE * 2.1, frames=100)

    def _disable_nearby_towers(self, x, y, radius, frames=90):
        for tower in self.game.towers:
            dx = tower.rect.centerx - x
            dy = tower.rect.centery - y
            if dx * dx + dy * dy <= radius * radius:
                if tower.in_pulse():
                    continue
                if tower.is_invincible():
                    self.game.notify_tower_hit(tower)
                    continue           # 卧龙免疫禁魔
                tower.disabled_timer = max(getattr(tower, "disabled_timer", 0), frames)
                self.game.notify_tower_hit(tower)

    def _contact_damage(self):
        if self.contact_cooldown > 0:
            return
        self.contact_cooldown = 18
        self._disable_nearby_towers(self.pos_x, self.pos_y, radius=TILE_SIZE * 1.4, frames=90)

    # ------------------------------------------------------------------ 技能

    def _update_casting(self):
        if self.reloading:
            self.reload_timer -= 1
            if self.reload_timer <= 0:
                self._finish_reload()
            return
        self.cast_cooldown -= 1
        if self.cast_cooldown <= 0:
            self._cast()

    def _skill_pool(self):
        if self.phase == 1:
            return ["summon", "fill", "execute"]
        acid = [] if self.acid_cooldown > 0 else ["acid_rain"]
        if self.phase == 2:
            return ["summon", "fill", "execute", "beam", "tp", "charm"] + acid
        if self.phase == 3:
            return ["summon", "fill", "execute", "beam", "freeze", "charm", "gamerule"] + acid
        return ["summon", "execute", "beam", "freeze", "charm", "gamerule", "reload"] + acid

    def _cast(self):
        pool = self._skill_pool()
        choices = [s for s in pool if s != self.last_skill] or pool
        skill = random.choice(choices)
        self.last_skill = skill
        self.cast_cooldown = self.CAST_COOLDOWN[self.phase]
        getattr(self, "_skill_" + skill)()
        if skill == "acid_rain":
            # 酸雨是全团降级，冷却额外拉长，避免连续两发把防线直接洗没
            self.cast_cooldown += 180

    def _announce(self, text, frames=150):
        self.cast_name = text
        if hasattr(self.game, "set_boss_banner"):
            self.game.set_boss_banner(text, frames)

    def _skill_summon(self):
        self._announce("指令-召唤  /summon")
        audio.play_sound(assets.portal_sound)
        count = {1: 3, 2: 4, 3: 5, 4: 6}[self.phase]
        pool = FINAL_BOSS_SUMMON_POOL[self.phase]
        path = self.game.path
        n = max(1, len(path))
        for i in range(count):
            if random.random() < 0.5:
                idx = random.randint(0, max(0, n // 2))
            else:
                idx = random.randint(n // 3, max(0, n - 2))
            col, row = path[idx]
            self.game.boss_portals.append(
                BossPortal(col, row, self.game, 26 + i * 12, random.choice(pool), idx))

    def _skill_fill(self):
        self._announce("指令-填充  /fill")
        audio.play_sound(assets.fill_sound)
        count = {1: 2, 2: 3, 3: 4, 4: 5}[self.phase]
        candidates = [t for t in self.game.towers if not t.in_pulse()]
        if not candidates:
            return
        for tower in random.sample(candidates, min(count, len(candidates))):
            # radius=0：只炸掉脚下一格，不会像第50波的命令方块那样掀掉 3×3
            self.game.command_blocks.append({
                "x": tower.x,
                "y": tower.y,
                "timer": 0,
                "max_timer": 150,
                "boss": True,
                "radius": 0,
            })

    def _skill_execute(self):
        self._announce("指令-执行  /execute")
        audio.play_sound(assets.execute_sound)
        count = {1: 2, 2: 3, 3: 4, 4: 5}[self.phase]
        candidates = [t for t in self.game.towers if not t.in_pulse()]
        if not candidates:
            return
        for tower in random.sample(candidates, min(count, len(candidates))):
            self.game.boss_strikes.append(BossStrike(tower.x, tower.y, self.game, delay=150))

    def _skill_charm(self):
        """指令-魅惑：随机魅惑 2 座炮塔，它们的攻击在 12 秒内全部变成等量治疗。"""
        self._announce("指令-魅惑  /effect @e[type=Tower] charm")
        audio.play_sound(assets.charm_sound)
        towers = [t for t in self.game.towers if not t.in_pulse()]
        if not towers:
            return
        for tower in random.sample(towers, min(BOSS_CHARM_TOWERS, len(towers))):
            if getattr(tower, "has_shield", False):
                # 护盾可以挡：破盾，不被魅惑
                tower.break_shield()
                self.game.trigger_shield_burst(tower)
                self.game.notify_tower_hit(tower)
                continue
            if tower.is_invincible():
                # 卧龙免疫魅惑，但这一下仍然算「自身被攻击」，能量照加
                self.game.notify_tower_hit(tower)
                continue
            tower.charm_timer = max(getattr(tower, "charm_timer", 0), BOSS_CHARM_FRAMES)
            self.game.notify_tower_hit(tower)
            # 一层粉色光环，让玩家立刻注意到「这两座塔在奶敌人」
            self.game.boss_shockwaves.append(BossShockwave(
                tower.x * TILE_SIZE + TILE_SIZE // 2,
                tower.y * TILE_SIZE + TILE_SIZE // 2,
                radius=90, duration=24, color=(255, 90, 170), width=4))

    def _skill_beam(self):
        self._announce("指令-抹除  /kill @e[type=tower]")
        vertical = random.random() < 0.5
        towers = list(self.game.towers)
        if vertical:
            counts = [0] * GRID_WIDTH
            for tower in towers:
                if 0 <= tower.x < GRID_WIDTH:
                    counts[tower.x] += 1
            best = max(range(GRID_WIDTH), key=lambda i: counts[i])
            index = best + random.choice([-1, 0, 0, 1])
            index = max(0, min(GRID_WIDTH - 1, index))
        else:
            counts = [0] * (GRID_HEIGHT + 2)
            for tower in towers:
                if 0 <= tower.y <= GRID_HEIGHT:
                    counts[tower.y] += 1
            best = max(range(1, GRID_HEIGHT + 1), key=lambda i: counts[i])
            index = best + random.choice([-1, 0, 0, 1])
            index = max(1, min(GRID_HEIGHT, index))
        self.game.boss_beams.append(DeleteBeam(self.game, vertical, index, telegraph=90))

    def _skill_freeze(self):
        self._announce("指令-时停  /tick freeze")
        self.game.boss_time_frozen = 3 * 60
        self.game.boss_flash = 45
        for i in range(18):
            self.game.boss_runes.append(
                BossRune(self.rect.centerx, self.rect.centery,
                         angle=i * math.tau / 18, speed=random.uniform(4, 9)))

    def _skill_gamerule(self):
        rule, label = random.choice([
            ("attack_speed", "攻速-50%"),
            ("range", "射程-30%"),
            ("gold", "金币产量归零"),
        ])
        self.game.boss_rule = {"type": rule, "timer": 12 * 60}
        self._announce(f"指令-覆写  /gamerule  [{label}]", 180)
        self.game.boss_flash = 30

    def _skill_tp(self):
        self._announce("指令-相移  /tp")
        self._teleport()

    def _skill_acid_rain(self):
        self._announce("指令-酸雨  /weather acid_rain", 220)
        self.acid_cooldown = 15 * 60
        self.game.boss_acid_timer = 220
        self.game.boss_flash = 45
        # 酸雨粒子（直接塞进天气粒子列表，落地后自动清理）
        for _ in range(220):
            x = random.randint(0, GRID_WIDTH * TILE_SIZE)
            y = random.randint(-320, 0)
            self.game.weather_particles.append(
                [x, y, random.randint(14, 22), random.randint(8, 16), "acid_rain"])
        if assets.explode_sound:
            assets.explode_sound.play()

        if Enchantment.WAX in self.game.enchantments:
            # 蜜脾：酸雨无法侵蚀炮塔，也不会破盾；
            # 改为和普通酸雨完全一致的效果——从终点向地图内扇形召唤 10 波、每波 5 只蜜蜂。
            # 蜜蜂会自动寻找场上敌人（第 100 波主要就是 BOSS 本体）。
            self.game.set_boss_banner("蜜脾生效：酸雨无法侵蚀炮塔，终点蜂群反扑奥米伽！", 220)
            self.game.bee_spawn_remaining = 10
            self.game.bee_spawn_timer = 0
            return

        affected = self.game.apply_acid_rain_downgrade()
        self.game.set_boss_banner(
            f"指令-酸雨  /weather acid_rain —— {affected} 座炮塔被侵蚀，等级 -1", 220)

    def _skill_reload(self):
        self._announce("终焉-世界重载  /reload —— 12 秒内击破任意一层血即可打断！", 720)
        audio.play_sound(assets.reload_sound)
        self.reloading = True
        self.reload_total = 12 * 60
        self.reload_timer = self.reload_total
        self.game.boss_flash = 60
        if assets.explode_sound:
            assets.explode_sound.play()

    def _interrupt_reload(self):
        self.reloading = False
        self.reload_timer = 0
        self.stun_timer = 3 * 60
        self.invuln_timer = 30
        self.game.boss_flash = 90
        self._announce("指令被打断！世界重载失败 —— 奥米伽陷入硬直", 240)
        self.cast_cooldown = 90

    def _finish_reload(self):
        self.reloading = False
        self.reload_timer = 0
        self.game.boss_flash = 140
        removed = 0
        for tower in list(self.game.towers):
            if tower.in_pulse():
                continue
            if getattr(tower, "has_shield", False):
                tower.break_shield()
                self.game.trigger_shield_burst(tower)
                self.game.notify_tower_hit(tower)
                continue
            if tower.is_invincible():
                self.game.notify_tower_hit(tower)
                continue               # 卧龙免疫世界重载
            self.game.notify_tower_hit(tower)
            self.game.destroy_tower_by_boss(tower)
            removed += 1
        self.game.boss_shockwaves.append(
            BossShockwave(self.rect.centerx, self.rect.centery,
                          radius=900, duration=70, color=(255, 60, 50), width=8))
        self._announce(f"世界重载完成：{removed} 座炮塔被从代码中抹除", 240)
        self.cast_cooldown = 120

    # ------------------------------------------------------------------ 受伤与死亡

    def _next_dmg_text_slot(self):
        """伤害飘字点位：左右交替的两行 + 正上方一个，共 5 个点位轮转。

        点位坐标相对 BOSS 中心，全部落在本体范围内（不再往外飘）。
        """
        self.dmg_text_slot = (self.dmg_text_slot + 1) % len(DMG_TEXT_SLOTS)
        side, base_x, base_y = DMG_TEXT_SLOTS[self.dmg_text_slot]
        if side == 0:
            # 正上方居中：只做小幅抖动
            offset_x = random.randint(-40, 40)
            drift_x = random.uniform(-0.3, 0.3)
        else:
            offset_x = side * random.randint(base_x, base_x + DMG_TEXT_BAND_W)
            drift_x = side * random.uniform(0.2, 0.7)
        offset_y = base_y + random.randint(-25, 25)
        # 上浮速度各不相同，同一点位连续冒出的数字会自己拉开，不会糊成一团
        self._dmg_text_vy = random.uniform(-2.9, -1.2)
        return (self.rect.centerx + offset_x,
                self.rect.centery + offset_y,
                drift_x)

    def take_damage(self, damage, color=RED, scale=1.0, ignore_armor=False, layers=1, element=None,
                    text_speed_x=0.0, dot=False):
        """layers>1 会无视当前层剩余血量直接击穿多层（现版本已无调用方，陨石改为只打穿 1 层）。

        dot=True 表示这是燃烧/中毒/凋零的持续伤害跳，供阿尔法的幽匿护甲区分直伤。
        """
        if self.dying or self.health <= 0:
            return 0
        if self.invuln_timer > 0:
            return 0

        final_dmg = max(0, int(damage))
        if self.reloading:
            # 咏唱期间是破绽窗口：受到 1.5 倍伤害，便于玩家打断
            final_dmg = int(final_dmg * 1.5)
        self.health -= final_dmg
        self.hit_flash = 4
        if self.game:
            tx, ty, tvx = self._next_dmg_text_slot()
            self.game.spawn_damage_text(final_dmg, (tx, ty), color=color, scale=scale,
                                        speed_x=tvx + text_speed_x,
                                        speed_y=self._dmg_text_vy, boss=True)
            if final_dmg > 0 and getattr(self.game, "damage_stats", None) is not None:
                elem = element or getattr(self.game, "damage_element", None)
                self.game.damage_stats.add(elem, final_dmg)

        if layers > 1:
            return self._pierce_layers(int(layers))

        if self.health > 0:
            return 0

        self.current_layer -= 1
        if self.current_layer <= 0:
            self.health = 0
            self._start_death()
            return 0

        self.health = self.max_health
        self._on_layer_break()
        return 0

    def _pierce_layers(self, count):
        """无视当前这层剩余血量，直接击穿 count 层。"""
        for _ in range(count):
            if self.dying or self.current_layer <= 0:
                break
            self.current_layer -= 1
            if self.current_layer <= 0:
                self.health = 0
                self._start_death()
                break
            self.health = self.max_health
            self.layer_flash = 14
            self._on_layer_break()
        return 0

    def _on_layer_break(self):
        self.layer_flash = 14
        self.game.boss_flash = max(self.game.boss_flash, 36)
        audio.play_sound_cool(assets.layer_break_sound, 150)
        self.game.boss_shockwaves.append(
            BossShockwave(self.rect.centerx, self.rect.centery,
                          radius=320, duration=30, color=(255, 180, 255), width=5))

        if self.reloading:
            self._interrupt_reload()
            return

        broken = FINAL_BOSS_LAYERS - self.current_layer
        new_phase = min(4, broken // FINAL_BOSS_LAYERS_PER_PHASE + 1)
        if new_phase != self.phase:
            self.phase = new_phase
            self.invuln_timer = 90
            self._teleport()
            self.game.boss_flash = 100
            self.game.set_boss_banner(
                f"阶段 {new_phase} : {FINAL_BOSS_PHASE_NAMES[new_phase - 1]}", 240)
            for i in range(24):
                self.game.boss_runes.append(
                    BossRune(self.rect.centerx, self.rect.centery,
                             angle=i * math.tau / 24, speed=random.uniform(5, 11)))
            self.cast_cooldown = min(self.cast_cooldown, 90)
            return

        if broken % 6 == 0:
            # 每崩解六层，立刻追加一次指令（爆发输出时也不能让玩家完全无压力）
            self.cast_cooldown = 0
        else:
            self.game.set_boss_banner(f"第 {self.current_layer} 层血 崩解  *{self.current_layer}", 90)

    def _start_death(self):
        self.dying = True
        self.reloading = False
        self.health = 1
        self.death_timer = 4 * 60
        self.dash_timer = 0
        self.stun_timer = 0
        self.game.final_boss = self
        self.game.set_boss_banner("终焉-奥米伽 —— 世界正在删除它……", 240)
        self.game.boss_flash = 150
        if assets.explode_sound:
            assets.explode_sound.play()
        # 它召唤出来的一切随它一起消失
        for enemy in list(self.game.enemies):
            if enemy is not self:
                enemy.kill()
        # 清空所有还没结算的指令，避免 BOSS 死后仍在抹除炮塔 / 召唤小怪
        self.game.boss_portals.clear()
        self.game.boss_strikes.clear()
        self.game.boss_beams.clear()
        self.game.boss_rule = None
        self.game.boss_time_frozen = 0

    def _update_death(self):
        self.death_timer -= 1
        self.game.boss_flash = max(self.game.boss_flash, 40)
        if self.death_timer % 7 == 0:
            x = self.rect.centerx + random.randint(int(-240 * S), int(240 * S))
            y = self.rect.centery + random.randint(int(-240 * S), int(240 * S))
            self.game.tnt_explosions.append(TNTExplosion(x, y, 0, 0, None, self.game))
            self.game.boss_shockwaves.append(
                BossShockwave(x, y, radius=random.randint(int(120 * S), int(220 * S)), duration=20,
                              color=random.choice([(255, 200, 120), (220, 120, 255)])))
        self._sync_rect()
        if self.death_timer <= 0:
            self.health = 0
            self.dying = False
            if self.game.final_boss is self:
                self.game.final_boss = None

    # ------------------------------------------------------------------ 免疫与表现

    def update_status_effects(self):
        """BOSS 免疫一切控制：只结算持续伤害（燃烧/中毒/凋零），永不返回 True。

        基类的眩晕/冰冻分支会返回 True 令 update() 提前返回——而无敌帧
        递减在其后，一旦被控制（例如绕过 apply_* 直接写字段的代码），
        换阶段设置的无敌就会停在原地，表现为永久锁血。
        apply_slow/apply_freeze/apply_stun/apply_knockback/apply_wind 均已
        重写为空实现，这里再兜底一层：即使控制减益漏进来也不影响 BOSS 行动。
        """
        super().update_status_effects()
        return False

    def apply_slow(self, *args, **kwargs):
        return

    def apply_speed(self, *args, **kwargs):
        return

    def apply_freeze(self, *args, **kwargs):
        return

    def apply_stun(self, *args, **kwargs):
        return

    def apply_knockback(self, *args, **kwargs):
        return

    def apply_wind(self, *args, **kwargs):
        return

    def teleport_to_start(self):
        return

    def on_lightning_hit(self):
        return

    def get_active_buffs(self):
        return []

    def draw_health_bar(self, screen):
        # 顶部有专属的 72 层血条
        return

    def draw_overlay(self, screen):
        if not VISUALS:
            _ensure_visuals()
        cx, cy = self.rect.center
        t = self.game.game_time
        phase_color = FINAL_BOSS_PHASE_COLORS[self.phase - 1]

        # 冲刺残影
        for x, y, life in self.trail:
            radius = int((20 + 16 * (life / 16.0)) * S)
            pygame.draw.circle(screen, (150, 90, 240), (int(x), int(y)), radius, 2)

        # 光晕
        glow = VISUALS["glow_red"] if self.phase == 4 else VISUALS["glow"]
        glow.set_alpha(85 + int(35 * math.sin(t * 0.08)) + (90 if self.reloading else 0))
        screen.blit(glow, glow.get_rect(center=(cx, cy)))

        # 紧贴核心的脉冲环
        pulse = 4 + int(3 * math.sin(t * 0.16))
        pygame.draw.circle(screen, phase_color, (cx, cy), int(132 * S) + pulse, 2)
        if self.phase == 4:
            for i in range(4):
                ang = t * 0.11 + i * math.pi / 2
                x1 = cx + math.cos(ang) * 138 * S
                y1 = cy + math.sin(ang) * 138 * S
                x2 = x1 + math.cos(ang + 0.5) * 34 * S
                y2 = y1 + math.sin(ang + 0.5) * 34 * S
                pygame.draw.line(screen, (255, 90, 60), (int(x1), int(y1)), (int(x2), int(y2)), 3)

        # 三重符文环
        for i in range(3):
            radius_x = int(168 * S) + i * int(44 * S)
            radius_y = int(128 * S) + i * int(36 * S)
            rect = pygame.Rect(0, 0, radius_x * 2, radius_y * 2)
            rect.center = (cx, cy)
            start = self.spin * (0.6 + 0.25 * i) + i * 2.1
            pygame.draw.arc(screen, phase_color, rect, start, start + 1.7, 3)
            pygame.draw.arc(screen, phase_color, rect, start + math.pi, start + math.pi + 1.1, 2)

        # 环绕的指令碎片
        shard = VISUALS["shard"]
        count = 6 + self.phase * 2
        for i in range(count):
            ang = t * 0.03 + i * math.tau / count
            radius = (150 + 20 * math.sin(t * 0.05 + i)) * S
            px = cx + math.cos(ang) * radius
            py = cy + math.sin(ang) * radius * 0.62
            rotated = pygame.transform.rotate(shard, math.degrees(ang) + t)
            screen.blit(rotated, rotated.get_rect(center=(int(px), int(py))))

        # 命中闪白
        if self.hit_flash > 0:
            screen.blit(VISUALS["flash"], self.rect.topleft)

        # 世界重载的充能环
        if self.reloading:
            p = 1.0 - self.reload_timer / self.reload_total
            radius = int((120 + 300 * p) * S)
            pygame.draw.circle(screen, (255, 80, 60), (cx, cy), radius, 5)
            pygame.draw.circle(screen, (255, 220, 190), (cx, cy), max(10, int(radius * 0.86)), 2)
            for i in range(8):
                ang = t * 0.08 + i * math.tau / 8
                px = cx + math.cos(ang) * radius
                py = cy + math.sin(ang) * radius
                pygame.draw.rect(screen, (255, 160, 120), (int(px) - 7, int(py) - 7, 14, 14))

        # 硬直星星
        if self.stun_timer > 0:
            for i in range(5):
                ang = t * 0.15 + i * math.tau / 5
                px = cx + math.cos(ang) * 120 * S
                py = cy - 130 * S + math.sin(ang) * 26 * S
                pygame.draw.rect(screen, (255, 240, 140), (int(px) - 6, int(py) - 6, 12, 12))


# ==========================================================================================
#  第 150 波真·最终 BOSS —— 原初·阿尔法 (ALPHA)，世界种子
#  复用奥米伽的全部管线（移动 / 施法 / 层血 / 死亡演出），只换数值、外观、
#  技能池与五个维度阶段的专属机制。
# ==========================================================================================

ALPHA_VISUALS = {}
AS = ALPHA_CORE_SIZE / 256.0   # 以 256px 基准的缩放系数（1.75 倍）


def _build_seed_core():
    """巨型种子水晶：基岩色六边形荚壳 + 幽绿内壳 + 世界种子核心。"""
    size = ALPHA_CORE_SIZE
    surf = pygame.Surface((size, size), pygame.SRCALPHA)
    cx = cy = size // 2

    # 外层六边形种子荚壳
    outer = [(cx + 126 * AS * math.cos(math.radians(60 * i - 30)),
              cy + 126 * AS * math.sin(math.radians(60 * i - 30))) for i in range(6)]
    pygame.draw.polygon(surf, (26, 24, 22), outer)
    pygame.draw.polygon(surf, (116, 98, 78), outer, max(3, int(5 * AS)))

    # 内层荚壳（幽绿）
    inner = [(cx + 100 * AS * math.cos(math.radians(60 * i - 30)),
              cy + 100 * AS * math.sin(math.radians(60 * i - 30))) for i in range(6)]
    pygame.draw.polygon(surf, (14, 40, 28), inner)
    pygame.draw.polygon(surf, (92, 220, 140), inner, max(1, int(2 * AS)))

    # 核心：世界种子贴图
    core_size = int(148 * AS)
    core_img = assets.world_seed_img or assets.command_block_img
    core = pygame.transform.scale(core_img, (core_size, core_size))
    core_x = cx - core_size // 2
    surf.blit(core, (core_x, core_x))
    pygame.draw.rect(surf, (190, 255, 210),
                     (core_x, core_x, core_size, core_size), max(2, int(4 * AS)))

    # 裂纹
    margin = int(30 * AS)
    crack_reach = int(46 * AS)
    for _ in range(16):
        x1 = random.randint(margin, size - margin)
        y1 = random.randint(margin, size - margin)
        x2 = x1 + random.randint(-crack_reach, crack_reach)
        y2 = y1 + random.randint(-crack_reach, crack_reach)
        pygame.draw.line(surf, (150, 240, 180), (x1, y1), (x2, y2), max(1, int(2 * AS)))

    # 四角锚点（金色，区别于奥米伽的白色）
    anchor = int(96 * AS)
    for dx, dy in ((-anchor, -anchor), (anchor, -anchor), (-anchor, anchor), (anchor, anchor)):
        half = int(7 * AS)
        pygame.draw.rect(surf, (255, 215, 0), (cx + dx - half, cy + dy - half, half * 2, half * 2))
        pygame.draw.rect(surf, (120, 90, 30),
                         (cx + dx - half - 3, cy + dy - half - 3, half * 2 + 6, half * 2 + 6), 2)

    # 两只「眼睛」
    eye_dx = int(38 * AS)
    for dx in (-eye_dx, eye_dx):
        pygame.draw.rect(surf, (240, 255, 240),
                         (cx + dx - int(12 * AS), cy - int(8 * AS), int(24 * AS), int(9 * AS)))
    return surf


def _build_seed_shard():
    """环绕碎片：草方块（上绿下棕），呼应「世界由方块组成」。"""
    side = max(30, int(46 * AS))
    chunk = max(20, int(34 * AS))
    pad = (side - chunk) // 2
    surf = pygame.Surface((side, side), pygame.SRCALPHA)
    half = chunk // 2
    pygame.draw.rect(surf, (58, 124, 52), (pad, pad, chunk, half))          # 草皮
    pygame.draw.rect(surf, (120, 82, 50), (pad, pad + half, chunk, chunk - half))  # 泥土
    pygame.draw.rect(surf, (140, 226, 120), (pad, pad, chunk, chunk), 2)
    return surf


def _ensure_alpha_visuals():
    if ALPHA_VISUALS:
        return
    ALPHA_VISUALS["core"] = _build_seed_core()
    ALPHA_VISUALS["shard"] = _build_seed_shard()
    ALPHA_VISUALS["glow"] = _radial_glow(int(320 * AS), (100, 220, 140), 105)
    ALPHA_VISUALS["glow_void"] = _radial_glow(int(360 * AS), (190, 70, 255), 120)
    ALPHA_VISUALS["flash"] = pygame.Surface((ALPHA_CORE_SIZE, ALPHA_CORE_SIZE), pygame.SRCALPHA)
    ALPHA_VISUALS["flash"].fill((255, 255, 255, 70))


class WorldSeedBoss(FinalBoss):
    """原初·阿尔法（ALPHA）：320 层 = 5 阶段 × 64 层，总血量 4800 亿。

    阶段即维度：主世界（教学）→ 下界（圣火 + 温度拉锯）→ 末地（水晶回层 +
    幻影 Herobrine）→ 深暗（幽匿护甲 + 灵波 + 黑暗）→ 虚空（奥米伽全技能 + /stop）。
    """

    MOVE_INTERVAL = ALPHA_MOVE_INTERVAL
    CAST_COOLDOWN = ALPHA_CAST_COOLDOWN

    def __init__(self, path, enemy_type, game):
        super().__init__(path, enemy_type, game)
        _ensure_alpha_visuals()

        self.max_health = ALPHA_LAYER_HEALTH
        self.health = self.max_health
        self.total_layers = ALPHA_LAYERS
        self.current_layer = ALPHA_LAYERS
        self.phase = 1

        self.image = ALPHA_VISUALS["core"]
        self.rect = self.image.get_rect()
        self.pos_x = float(GRID_WIDTH * TILE_SIZE // 2)
        self.pos_y = float((1 + GRID_HEIGHT) * TILE_SIZE // 2)
        self.anchor = (self.pos_x, self.pos_y)
        self.rect.center = (int(self.pos_x), int(self.pos_y))

        # 供 BossPortal / ui 读取的表现层数据（奥米伽读模块常量，阿尔法读实例属性）
        self.display_name = ALPHA_BOSS_NAME
        self.display_en = ALPHA_BOSS_EN_NAME
        self.display_title = ALPHA_BOSS_TITLE
        self.phase_names = ALPHA_PHASE_NAMES
        self.phase_colors = ALPHA_PHASE_COLORS
        self.minion_health_table = ALPHA_MINION_HEALTH
        self.summon_pools = ALPHA_SUMMON_POOL
        self.reload_label = "/stop 停服"

        self.darkness = False                # P4：强制黑暗（提灯克制）
        self.temp_pull_timer = ALPHA_NETHER_PULL_INTERVAL
        self.crystal_heal_timer = ALPHA_END_CRYSTAL_HEAL_FRAMES
        self.sonic_timer = 0
        self.sonic_total = ALPHA_SONIC_WARN_FRAMES
        self.phantom_spawned = False

    # ------------------------------------------------------------------ 阶段机制

    def _alive_end_crystals(self):
        return sum(1 for e in self.game.enemies
                   if e.enemy_type == EnemyType.END_CRYSTAL and e.health > 0)

    def _heal_one_layer(self):
        """末影水晶回层：先补满当前层，再重生一层，上限 320。"""
        if self.dying:
            return
        if self.health < self.max_health:
            self.health = self.max_health
        elif self.current_layer < self.total_layers:
            self.current_layer += 1
            self.layer_flash = 14
            self.game.boss_shockwaves.append(BossShockwave(
                self.rect.centerx, self.rect.centery, radius=300, duration=30,
                color=(230, 180, 255), width=4))
            self.game.set_boss_banner(
                f"末影水晶闪烁：阿尔法重生成了 1 层血（{self.current_layer}/{self.total_layers}）", 120)

    def _spawn_phantom_herobrine(self):
        """彩蛋：末地阶段把 50 波的鬼故事重新讲一遍。"""
        self._announce("它想起了 50 波的鬼故事 —— 幻影·Herobrine 沿路走来！", 260)
        phantom = Enemy(self.game.path, EnemyType.HEROBRINE, self.game)
        phantom.max_health = ALPHA_LAYER_HEALTH
        phantom.health = phantom.max_health
        phantom.total_layers = ALPHA_PHANTOM_LAYERS
        phantom.current_layer = ALPHA_PHANTOM_LAYERS
        phantom.speed = phantom.base_speed = ALPHA_PHANTOM_SPEED
        phantom.reward = 0
        self.game.enemies.add(phantom)

    def _resolve_sonic_boom(self):
        """灵波落地：无视护盾锁全场炮塔 6 秒（脉冲免疫、卧龙免疫）。"""
        self.sonic_timer = 0
        self.game.boss_flash = 90
        self.game.boss_shockwaves.append(BossShockwave(
            self.rect.centerx, self.rect.centery, radius=1200, duration=40,
            color=(120, 240, 255), width=8))
        for tower in list(self.game.towers):
            if tower.in_pulse():
                continue
            if tower.is_invincible():
                self.game.notify_tower_hit(tower)
                continue
            tower.disabled_timer = max(getattr(tower, "disabled_timer", 0), ALPHA_SONIC_LOCK_FRAMES)
            self.game.notify_tower_hit(tower)
        self._announce("灵波震荡！全场炮塔被震慑 6 秒", 150)

    def update(self):
        if self.dying or self.health <= 0:
            return super().update()

        # P2 下界：温度被世界种子向上拉（冰塔照常往回拉，形成拉锯）
        if self.phase == 2 and self.game.temperature < ALPHA_NETHER_TEMP:
            self.temp_pull_timer -= 1
            if self.temp_pull_timer <= 0:
                self.temp_pull_timer = ALPHA_NETHER_PULL_INTERVAL
                self.game.temperature += 1

        # P4 灵波读秒
        if self.sonic_timer > 0:
            self.sonic_timer -= 1
            if self.sonic_timer <= 0:
                self._resolve_sonic_boom()

        # P3 起末影水晶回层
        if self.phase >= 3 and self._alive_end_crystals() > 0:
            self.crystal_heal_timer -= 1
            if self.crystal_heal_timer <= 0:
                self.crystal_heal_timer = ALPHA_END_CRYSTAL_HEAL_FRAMES
                self._heal_one_layer()

        self.darkness = (self.phase == 4)
        return super().update()

    # ------------------------------------------------------------------ 移动

    def _hover_speed(self):
        return 1.1 + 0.3 * self.phase

    def _choose_move(self):
        self.move_timer = self.MOVE_INTERVAL[self.phase]
        roll = random.random()
        if self.phase == 1:
            self._set_anchor()
        elif self.phase == 2:
            if roll < 0.40:
                self._start_dash()
            else:
                self._set_anchor()
        elif self.phase == 3:
            if roll < 0.45:
                self._teleport()
            elif roll < 0.80:
                self._start_dash()
            else:
                self._set_anchor()
        elif self.phase == 4:
            if roll < 0.30:
                self._teleport()
            elif roll < 0.70:
                self._start_dash()
            else:
                self._set_anchor()
        else:
            if roll < 0.50:
                self._teleport()
            elif roll < 0.92:
                self._start_dash()
            else:
                self._set_anchor()

    # ------------------------------------------------------------------ 技能

    def _skill_pool(self):
        if self.phase == 1:
            # 主世界：教学期，外加「天候」随机改写天气
            return ["summon", "fill", "execute", "weather"]
        acid = [] if self.acid_cooldown > 0 else ["acid_rain"]
        if self.phase == 2:
            # 下界：圣火 + 恶魂火球
            return ["summon", "fill", "sacred_fire", "fireball", "execute"] + acid
        if self.phase == 3:
            # 末地：高频瞬移 + 水晶回层 + 魅惑
            pool = ["summon", "tp", "execute", "charm"]
            if self._alive_end_crystals() < ALPHA_END_CRYSTAL_CAP:
                pool.append("end_crystal")
            return pool
        if self.phase == 4:
            # 深暗：灵波震场
            return ["summon", "sonic_boom", "execute", "fill", "charm"]
        # 虚空：奥米伽的看家本领全套解禁 + /stop
        return ["summon", "beam", "freeze", "charm", "gamerule", "stop"] + acid

    def _cast(self):
        pool = self._skill_pool()
        choices = [s for s in pool if s != self.last_skill] or pool
        skill = random.choice(choices)
        self.last_skill = skill
        cd = self.CAST_COOLDOWN[self.phase]
        if self.current_layer <= ALPHA_BERSERK_LAYERS:
            # 最后 16 层狂暴：施法间隔 ×0.7
            cd = max(45, int(cd * 0.7))
        self.cast_cooldown = cd
        getattr(self, "_skill_" + skill)()
        if skill == "acid_rain":
            # 酸雨是全团降级，冷却额外拉长（与奥米伽同款）
            self.cast_cooldown += 180
        elif skill == "sonic_boom":
            # 灵波 3 秒预警 + 6 秒全屏锁塔，冷却额外拉长
            self.cast_cooldown += 300

    def _skill_summon(self):
        self._announce("指令-召唤  /summon")
        audio.play_sound(assets.portal_sound)
        count = {1: 4, 2: 6, 3: 8, 4: 8, 5: 10}[self.phase]
        pool = self.summon_pools[self.phase]
        path = self.game.path
        n = max(1, len(path))
        for i in range(count):
            if random.random() < 0.5:
                idx = random.randint(0, max(0, n // 2))
            else:
                idx = random.randint(n // 3, max(0, n - 2))
            col, row = path[idx]
            self.game.boss_portals.append(
                BossPortal(col, row, self.game, 26 + i * 12, random.choice(pool), idx))

    def _skill_weather(self):
        """指令-天候：随机改写一次天气（避开酸雨/永夜，防止和圣火/黑暗叠加过度）。

        地形群系由 boss 阶段决定（apply_alpha_terrain / ALPHA_PHASE_TERRAIN），
        改天气只换天空表现，不重置群系地形。
        """
        pool = [w for w in WEATHER_CONFIG
                if w not in (Weather.ACID_RAIN, Weather.ENDLESS_NIGHT)]
        weather = random.choice(pool)
        info = WEATHER_CONFIG[weather]
        self.game.weather = weather
        self.game.fog_visible = False
        self.game._build_background(
            gold_ore_positions=self.game.gold_ore_positions,
            terrain=ALPHA_PHASE_TERRAIN.get(self.phase, "overworld"))
        self.game.recompute_temperature()
        self.game.weather_banner_text = info["desc"]
        self.game.weather_banner_timer = 180
        self._announce(f"指令-天候  /weather {weather.name.lower()}  [{info['name']}]", 200)

    def _skill_sacred_fire(self):
        """群系侵蚀-圣火：随机两座炮塔附着圣火（40% miss / 每 16s 降级 / 四向蔓延）。

        护盾可以挡下附着（破盾不被点燃）；已经着火的塔再套盾无济于事。
        圣火没有时限，转阶段（世界重生成）时全部熄灭。
        """
        self._announce("群系侵蚀-圣火  /effect @e[type=Tower] sacred_fire", 220)
        audio.play_sound(assets.sacred_fire_sound)
        towers = [t for t in self.game.towers if not t.in_pulse()]
        if not towers:
            return
        for tower in random.sample(towers, min(SACRED_FIRE_TARGETS, len(towers))):
            self.game.apply_sacred_fire(tower)
            self.game.boss_shockwaves.append(BossShockwave(
                tower.x * TILE_SIZE + TILE_SIZE // 2,
                tower.y * TILE_SIZE + TILE_SIZE // 2,
                radius=110, duration=26, color=(255, 130, 40), width=4))

    def _skill_fireball(self):
        self._announce("指令-火球  /summon fireball", 200)
        audio.play_sound(assets.fireball_sound)
        candidates = [t for t in self.game.towers if not t.in_pulse()]
        if not candidates:
            return
        for tower in random.sample(candidates, min(2, len(candidates))):
            self.game.boss_fireballs.append(SeedFireball(
                self.game, self.rect.centerx, self.rect.centery,
                tower.x * TILE_SIZE + TILE_SIZE // 2,
                tower.y * TILE_SIZE + TILE_SIZE // 2))

    def _skill_end_crystal(self):
        self._announce("指令-水晶  /place end_crystal —— 击碎水晶，否则每 10 秒重生一层血！", 240)
        count = min(ALPHA_END_CRYSTAL_PER_CAST, ALPHA_END_CRYSTAL_CAP - self._alive_end_crystals())
        cx, cy = self.rect.centerx, self.rect.centery
        spots = [(cx - TILE_SIZE * 1.4, cy - TILE_SIZE * 0.9),
                 (cx + TILE_SIZE * 1.4, cy - TILE_SIZE * 0.9),
                 (cx, cy + TILE_SIZE * 1.2)]
        for i in range(max(0, count)):
            x, y = spots[i % len(spots)]
            self.game.enemies.add(EndCrystalEnemy(self.game.path, self.game, int(x), int(y)))
            self.game.boss_shockwaves.append(BossShockwave(
                int(x), int(y), radius=120, duration=24, color=(230, 150, 255), width=4))

    def _skill_sonic_boom(self):
        self._announce("指令-灵波  /playsound sonic_boom —— 3 秒后震荡全场，护盾无效！", 200)
        self.sonic_timer = self.sonic_total
        self.game.boss_flash = 40

    def _skill_acid_rain(self):
        """虚空阶段沿用奥米伽的酸雨技能，只把播报里的名字换成阿尔法。"""
        self._announce("指令-酸雨  /weather acid_rain", 220)
        self.acid_cooldown = 15 * 60
        self.game.boss_acid_timer = 220
        self.game.boss_flash = 45
        for _ in range(220):
            x = random.randint(0, GRID_WIDTH * TILE_SIZE)
            y = random.randint(-320, 0)
            self.game.weather_particles.append(
                [x, y, random.randint(14, 22), random.randint(8, 16), "acid_rain"])
        if assets.explode_sound:
            assets.explode_sound.play()

        if Enchantment.WAX in self.game.enchantments:
            self.game.set_boss_banner("蜜脾生效：酸雨无法侵蚀炮塔，终点蜂群反扑阿尔法！", 220)
            self.game.bee_spawn_remaining = 10
            self.game.bee_spawn_timer = 0
            return

        affected = self.game.apply_acid_rain_downgrade()
        self.game.set_boss_banner(
            f"指令-酸雨  /weather acid_rain —— {affected} 座炮塔被侵蚀，等级 -1", 220)

    def _skill_stop(self):
        """终焉-停服：世界重载的强化版，读条 15 秒，打破任一层即打断。"""
        self._announce("终焉-停服  /stop —— 15 秒内击破任意一层血即可打断！", 900)
        audio.play_sound(assets.reload_sound)
        self.reloading = True
        self.reload_total = ALPHA_STOP_CAST_FRAMES
        self.reload_timer = self.reload_total
        self.game.boss_flash = 60
        if assets.explode_sound:
            assets.explode_sound.play()

    def _interrupt_reload(self):
        self.reloading = False
        self.reload_timer = 0
        self.stun_timer = 3 * 60
        self.invuln_timer = 30
        self.game.boss_flash = 90
        self._announce("/stop 被打断！世界重新生成中止 —— 阿尔法陷入硬直", 240)
        self.cast_cooldown = 90

    def _finish_reload(self):
        super()._finish_reload()
        self.game.set_boss_banner("/stop 执行完毕 —— 服务器已停服，未受保护的炮塔被抹除", 240)

    # ------------------------------------------------------------------ 受伤与层血

    def take_damage(self, damage, color=RED, scale=1.0, ignore_armor=False, layers=1, element=None,
                    text_speed_x=0.0, dot=False):
        # P4 幽匿护甲：直接伤害 ×0.4；DoT（dot=True）与百分比真伤（ignore_armor）不减免
        if self.phase == 4 and not (ignore_armor or dot):
            damage = damage * ALPHA_SCULK_ARMOR_MULT
        return super().take_damage(damage, color=color, scale=scale, ignore_armor=ignore_armor,
                                   layers=layers, element=element,
                                   text_speed_x=text_speed_x, dot=dot)

    def _on_layer_break(self):
        self.layer_flash = 14
        self.game.boss_flash = max(self.game.boss_flash, 36)
        self.game.boss_shockwaves.append(BossShockwave(
            self.rect.centerx, self.rect.centery, radius=340, duration=30,
            color=self.phase_colors[self.phase - 1], width=5))

        if self.reloading:
            self._interrupt_reload()
            return

        broken = self.total_layers - self.current_layer
        new_phase = min(5, broken // ALPHA_LAYERS_PER_PHASE + 1)
        if new_phase != self.phase:
            old_phase = self.phase
            self.phase = new_phase
            self._on_phase_change(old_phase, new_phase)
            return

        if broken % 8 == 0:
            # 每崩解八层，立刻追加一次指令
            self.cast_cooldown = 0
        else:
            self.game.set_boss_banner(f"第 {self.current_layer} 层血 崩解  *{self.current_layer}", 90)

    def _on_phase_change(self, old_phase, new_phase):
        """世界重生成：转阶段无敌 + 瞬移 + 群系更替演出。"""
        self.invuln_timer = 90
        self._teleport()
        self.game.boss_flash = 100
        audio.play_sound(assets.phase_change_sound)
        # 群系地形改写：P2 下界 / P3 末地 / P4-P5 强制永夜（P1 主世界不变）
        self.game.apply_alpha_terrain(new_phase)
        banner = f"阶段 {new_phase} : {ALPHA_PHASE_NAMES[new_phase - 1]} —— 世界正在重新生成"
        terrain_note = ALPHA_PHASE_TERRAIN_DESC.get(new_phase)
        if terrain_note:
            banner += f"（{terrain_note}）"
        self.game.set_boss_banner(banner, 260)
        for i in range(24):
            self.game.boss_runes.append(
                BossRune(self.rect.centerx, self.rect.centery,
                         angle=i * math.tau / 24, speed=random.uniform(5, 11)))
        self.cast_cooldown = min(self.cast_cooldown, 90)
        # 群系更替清洗：离开下界时圣火全部熄灭、温度恢复原状
        if old_phase == 2:
            for t in self.game.towers:
                t.sacred_fire = False
            self.game.recompute_temperature()
        # 进入末地：幻影·Herobrine（一次性）
        if new_phase == 3 and not self.phantom_spawned:
            self.phantom_spawned = True
            self._spawn_phantom_herobrine()

    def _start_death(self):
        super()._start_death()
        self.game.set_boss_banner("原初·阿尔法 —— 种子正在失去光芒……", 240)
        # 种子熄灭：圣火与黑暗一并消散，被改写的地形恢复主世界原貌
        for t in self.game.towers:
            t.sacred_fire = False
        self.darkness = False
        self.game.apply_alpha_terrain(1)
        if self.game.weather == Weather.ENDLESS_NIGHT:
            self.game.weather = Weather.SUNNY
            self.game.recompute_temperature()
            self.game.weather_banner_text = WEATHER_CONFIG[self.game.weather]["desc"]

    # ------------------------------------------------------------------ 表现

    def draw_overlay(self, screen):
        if not ALPHA_VISUALS:
            _ensure_alpha_visuals()
        cx, cy = self.rect.center
        t = self.game.game_time
        phase_color = self.phase_colors[self.phase - 1]

        # 冲刺残影
        for x, y, life in self.trail:
            radius = int((20 + 16 * (life / 16.0)) * AS)
            pygame.draw.circle(screen, (90, 200, 130), (int(x), int(y)), radius, 2)

        # 光晕（虚空阶段换紫色）
        glow = ALPHA_VISUALS["glow_void"] if self.phase == 5 else ALPHA_VISUALS["glow"]
        glow.set_alpha(85 + int(35 * math.sin(t * 0.08)) + (90 if self.reloading else 0))
        screen.blit(glow, glow.get_rect(center=(cx, cy)))

        # 紧贴核心的脉冲环
        pulse = 4 + int(3 * math.sin(t * 0.16))
        pygame.draw.circle(screen, phase_color, (cx, cy), int(150 * AS) + pulse, 2)
        if self.phase == 5:
            for i in range(4):
                ang = t * 0.11 + i * math.pi / 2
                x1 = cx + math.cos(ang) * 158 * AS
                y1 = cy + math.sin(ang) * 158 * AS
                x2 = x1 + math.cos(ang + 0.5) * 36 * AS
                y2 = y1 + math.sin(ang + 0.5) * 36 * AS
                pygame.draw.line(screen, (200, 90, 255), (int(x1), int(y1)), (int(x2), int(y2)), 3)

        # 五重符文环（维度刻度）
        for i in range(5):
            radius_x = int(168 * AS) + i * int(34 * AS)
            radius_y = int(128 * AS) + i * int(28 * AS)
            rect = pygame.Rect(0, 0, radius_x * 2, radius_y * 2)
            rect.center = (cx, cy)
            start = self.spin * (0.6 + 0.22 * i) + i * 1.7
            pygame.draw.arc(screen, phase_color, rect, start, start + 1.6, 3)
            pygame.draw.arc(screen, phase_color, rect, start + math.pi, start + math.pi + 1.0, 2)

        # 环绕的草方块碎片
        shard = ALPHA_VISUALS["shard"]
        count = 6 + self.phase * 2
        for i in range(count):
            ang = t * 0.03 + i * math.tau / count
            radius = (150 + 20 * math.sin(t * 0.05 + i)) * AS
            px = cx + math.cos(ang) * radius
            py = cy + math.sin(ang) * radius * 0.62
            rotated = pygame.transform.rotate(shard, math.degrees(ang) + t)
            screen.blit(rotated, rotated.get_rect(center=(int(px), int(py))))

        # 灵波预警：从核心向外扩张的青色声环
        if self.sonic_timer > 0:
            p = 1.0 - self.sonic_timer / max(1, self.sonic_total)
            for i in range(3):
                radius = int(260 + 380 * p + i * 70)
                pygame.draw.circle(screen, (120, 240, 255), (cx, cy), radius, 3)

        # 命中闪白
        if self.hit_flash > 0:
            screen.blit(ALPHA_VISUALS["flash"], self.rect.topleft)

        # /stop 停服的充能环
        if self.reloading:
            p = 1.0 - self.reload_timer / self.reload_total
            radius = int((130 + 320 * p) * AS)
            pygame.draw.circle(screen, (255, 80, 60), (cx, cy), radius, 5)
            pygame.draw.circle(screen, (255, 220, 190), (cx, cy), max(10, int(radius * 0.86)), 2)
            for i in range(8):
                ang = t * 0.08 + i * math.tau / 8
                px = cx + math.cos(ang) * radius
                py = cy + math.sin(ang) * radius
                pygame.draw.rect(screen, (255, 160, 120), (int(px) - 7, int(py) - 7, 14, 14))

        # 硬直星星
        if self.stun_timer > 0:
            for i in range(5):
                ang = t * 0.15 + i * math.tau / 5
                px = cx + math.cos(ang) * 120 * AS
                py = cy - 130 * AS + math.sin(ang) * 26 * AS
                pygame.draw.rect(screen, (255, 240, 140), (int(px) - 6, int(py) - 6, 12, 12))
