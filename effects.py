import math
import random
import pygame
import assets
from config import *

# 不稳定水晶引爆动画的缩放帧只做一次，避免每颗水晶各缩放一遍
_CRYSTAL_BLAST_FRAMES = None


class WindExplosion:
    def __init__(self, x, y, damage, knockback, game, element="wind"):
        self.x = x
        self.y = y
        self.duration = 6
        self.radius = 128
        self.element = element
        for enemy in game.enemies:
            if enemy.health <= 0:
                continue
            dx = enemy.rect.centerx - x
            dy = enemy.rect.centery - y
            if (dx * dx + dy * dy) <= self.radius * self.radius:
                reward = enemy.take_damage(damage, color=MINT, scale=0.8, element=self.element)
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


class EndlessGreedExplosion:
    def __init__(self, x, y, game):
        self.x = x
        self.y = y
        self.game = game
        self.frame_index = 0
        self.frame_accum = 0
        self.radius = 128
        for enemy in game.enemies:
            if enemy.health <= 0:
                continue
            dx = enemy.rect.centerx - x
            dy = enemy.rect.centery - y
            if (dx * dx + dy * dy) <= self.radius * self.radius:
                pct_dmg = max(1, int(enemy.max_health * 0.01))
                # 百分比伤害 = 真实伤害，不吃加成也不吃减伤
                reward = enemy.take_damage(pct_dmg, color=WHITE, scale=1.0,
                                           ignore_armor=True, element="explosion")
                game.coins += reward

    def update(self):
        self.frame_accum += 1
        if self.frame_accum >= 3:
            self.frame_accum = 0
            self.frame_index += 1
        return self.frame_index < len(assets.endless_greed_frames)

    def draw(self, surface):
        if self.frame_index >= len(assets.endless_greed_frames):
            return
        img = assets.endless_greed_frames[self.frame_index]
        surface.blit(img, img.get_rect(center=(self.x, self.y)))


class ResonanceStorm:
    """共振风暴 / 雷神之锤命中爆裂共用的闪电序列（resonance_storm01~12）。

    frames 可配：共振风暴触发用放大 4 倍的全屏版本；
    雷神之锤子弹命中爆裂用原尺寸帧（282x282），不缩放。

    对齐方式：这套素材是「雷从天上劈下来」，闪电落点不在图片正中，
    而在 y≈0.88H 处（第 3~7 帧的爆裂底部）。所以默认按「底边对齐命中点」
    绘制，让雷劈在敌人身上而不是敌人上方一屏处；锚点用 anchor_y 调。
    """

    # 落点在图片高度的比例（0=顶边，1=底边）。
    # 原尺寸帧（282px）实测：冲击光环最亮行在 y≈0.77H，半宽 127px。
    # 放大 4 倍的帧给全屏共振风暴用，本来就铺满地图、不需要对齐落点，
    # 用居中(0.5)避免整体上移出屏。
    ANCHOR_Y_RAW = 0.77
    ANCHOR_Y_BIG = 0.5

    def __init__(self, x, y, frames=None, frame_duration=3, anchor_y=None):
        self.x = x
        self.y = y
        self.frames = assets.resonance_storm_frames if frames is None else frames
        self.frame_duration = max(1, frame_duration)
        if anchor_y is not None:
            self.anchor_y = anchor_y
        elif self.frames is assets.resonance_storm_raw_frames:
            self.anchor_y = self.ANCHOR_Y_RAW
        else:
            self.anchor_y = self.ANCHOR_Y_BIG
        self.frame_index = 0
        self.frame_accum = 0

    def update(self):
        self.frame_accum += 1
        if self.frame_accum >= self.frame_duration:
            self.frame_accum = 0
            self.frame_index += 1
        return self.frame_index < len(self.frames)

    def draw(self, surface):
        if self.frame_index >= len(self.frames):
            return
        img = self.frames[self.frame_index]
        # 让图片的 anchor_y 高度处对准 (x, y)
        left = int(self.x) - img.get_width() // 2
        top = int(self.y) - int(img.get_height() * self.anchor_y)
        surface.blit(img, (left, top))


class HellRay:
    def __init__(self, x1, y1, x2, y2):
        self.x1 = x1
        self.y1 = y1
        self.x2 = x2
        self.y2 = y2
        self.duration = 15

    def update(self):
        self.duration -= 1
        return self.duration > 0

    def draw(self, screen):
        if self.duration <= 0:
            return
        sx = min(self.x1, self.x2)
        sy = min(self.y1, self.y2)
        s = pygame.Surface((abs(self.x2 - self.x1) + 4, abs(self.y2 - self.y1) + 4), pygame.SRCALPHA)
        s.set_alpha(int(17 * self.duration))
        pygame.draw.line(s, (0, 0, 0),
                         (self.x1 - sx + 2, self.y1 - sy + 2),
                         (self.x2 - sx + 2, self.y2 - sy + 2),
                         max(3, int(self.duration)))
        screen.blit(s, (sx - 2, sy - 2))


class IceExplosion:
    def __init__(self, x, y, damage, freeze_time, game):
        self.x = x
        self.y = y
        self.game = game
        self.w = 282
        self.h = 320
        self.frames = []
        for img in assets.ice_explosion_frames:
            if img.get_width() != self.w or img.get_height() != self.h:
                img = pygame.transform.smoothscale(img, (self.w, self.h))
            self.frames.append(img)
        self.frame_index = 0
        self.frame_accum = 0
        for enemy in game.enemies:
            if enemy.health <= 0:
                continue
            dx = enemy.rect.centerx - x
            dy = enemy.rect.centery - y
            if abs(dx) <= self.w // 2 and abs(dy) <= self.h // 2:
                reward = enemy.take_damage(damage, color=ICE_BLUE, scale=0.8,
                                           element=getattr(game, "damage_element", None) or "ice")
                game.coins += reward
                enemy.apply_freeze(freeze_time)

    def update(self):
        self.frame_accum += 1
        if self.frame_accum >= 3:
            self.frame_accum = 0
            self.frame_index += 1
        return self.frame_index < len(self.frames)

    def draw(self, screen):
        if self.frame_index >= len(self.frames):
            return
        img = self.frames[self.frame_index]
        screen.blit(img, img.get_rect(center=(self.x, self.y)))


class DragonBreathPool:
    def __init__(self, x, y, temperature, tower_level, stun_time, game):
        self.x = x
        self.y = y
        self.radius = 128
        self.duration = 10
        dmg_mult = (tower_level - 10) * 10
        # 取绝对值：高温、低温都能打出伤害。火系塔每级 +1 温度，玩低温流会丢掉燃烧
        # 和一堆火系附魔，这里只是让「强行压低温度」不再变成给敌人回血 / 零伤害。
        dmg = max(1, int(abs(temperature) * dmg_mult * game.get_element_damage_multiplier("fire")))
        for enemy in game.enemies:
            if enemy.health <= 0:
                continue
            dx = enemy.rect.centerx - self.x
            dy = enemy.rect.centery - self.y
            if (dx * dx + dy * dy) <= self.radius * self.radius:
                reward = enemy.take_damage(dmg, color=PURPLE, scale=0.7, element="fire")
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
        damage = int(damage * game.get_element_damage_multiplier("poison"))
        for enemy in game.enemies:
            if enemy.health <= 0:
                continue
            dx = enemy.rect.centerx - x
            dy = enemy.rect.centery - y
            if (dx * dx + dy * dy) <= self.radius * self.radius:
                reward = enemy.take_damage(damage, color=GREEN, scale=0.8, element="poison")
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


class PoisonContractExplosion:
    def __init__(self, x, y, game, stacks=0):
        self.x = x
        self.y = y
        self.duration = 6
        self.radius = 128
        self.stacks = max(0, int(stacks))
        # 用触发时（+1 之前）的基础毒伤结算，避免奖励层数反过来放大本次爆炸
        # 线性公式：(基础毒伤 + 层数) * 18 * (1 + 毒系伤害加成)，避免 base × stacks 的平方爆炸
        damage = int((game.poison_base_damage + self.stacks) * POISON_CONTRACT_BURST_MULT
                     * game.get_element_damage_multiplier("poison"))
        game.poison_base_damage += 1
        for enemy in game.enemies:
            if enemy.health <= 0:
                continue
            dx = enemy.rect.centerx - x
            dy = enemy.rect.centery - y
            if (dx * dx + dy * dy) <= self.radius * self.radius:
                reward = enemy.take_damage(damage, color=GREEN, scale=0.8, element="poison")
                game.coins += reward
                enemy.apply_stun(5 * 60)

    def update(self):
        self.duration -= 1
        return self.duration > 0

    def draw(self, screen):
        alpha = int(80 * self.duration / 6)
        s = pygame.Surface((self.radius * 2, self.radius * 2), pygame.SRCALPHA)
        pygame.draw.circle(s, (0, 255, 0, alpha), (self.radius, self.radius), self.radius)
        screen.blit(s, (self.x - self.radius, self.y - self.radius))


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
                reward = enemy.take_damage(damage, color=RED, scale=1.0,
                                           element=getattr(game, "damage_element", None))
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


class MushroomExplosion:
    def __init__(self, x, y, damage, tower_level, game, bomb_branch=1):
        self.x = x
        self.y = y
        self.damage = damage
        self.tower_level = tower_level
        self.game = game
        self.bomb_branch = bomb_branch
        self.frame = 0
        self.frame_timer = 0
        self.frame_duration = 3
        self.max_frames = 10
        self.done = False

        if assets.explode_sound:
            assets.explode_sound.play()

        if bomb_branch == 1:
            # 同样取绝对值：高温增伤、低温也增伤，避免极寒时伤害变成负数给敌人回血
            final_damage = (40000 + 400 * abs(game.temperature)) * (tower_level - 10)
            final_damage = int(final_damage * game.get_enchant_damage_multiplier(TowerType.BOMB))
            final_damage = max(1, final_damage)
            for enemy in game.enemies:
                if enemy.health <= 0:
                    continue
                reward = enemy.take_damage(final_damage, color=RED, scale=1.2,
                                           element=getattr(game, "damage_element", None))
                game.coins += reward
                enemy.apply_stun(120)
        else:
            percent_damage = [0.02, 0.04, 0.06, 0.08, 0.1][tower_level - 11]
            fixed_damage = [2000, 4000, 6000, 8000, 10000][tower_level - 11]
            if game.wither_rose_active():
                percent_damage += 0.008
            fixed_damage = int(fixed_damage * game.get_enchant_damage_multiplier(TowerType.BOMB))
            for enemy in game.enemies:
                if enemy.health <= 0:
                    continue
                percent_dmg = int(enemy.max_health * percent_damage)
                element = getattr(game, "damage_element", None)
                # 百分比部分 = 真实伤害，固定部分吃爆炸加成
                reward = enemy.take_damage(percent_dmg, color=RED, scale=1.2,
                                           ignore_armor=True, element=element)
                reward += enemy.take_damage(fixed_damage, color=RED, scale=1.2, element=element)
                game.coins += reward
                enemy.apply_stun(120)
                enemy.wither_timer = 600

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


class Meteor:
    def __init__(self, game):
        self.game = game
        self.x = SCREEN_WIDTH + 200
        self.y = -200
        self.target_x = GRID_WIDTH * TILE_SIZE // 2
        self.target_y = (1 + GRID_HEIGHT) * TILE_SIZE // 2
        dx = self.target_x - self.x
        dy = self.target_y - self.y
        dist = math.sqrt(dx * dx + dy * dy)
        self.vx = dx / dist * 18
        self.vy = dy / dist * 18
        self.done = False

    def update(self):
        self.x += self.vx
        self.y += self.vy
        tx = self.target_x - self.x
        ty = self.target_y - self.y
        if self.vx * tx + self.vy * ty <= 0:
            self.x = self.target_x
            self.y = self.target_y
            self.game.add_meteor_hit(self.target_x, self.target_y)
            self.done = True
        return not self.done

    def draw(self, screen):
        if assets.ember_meteor_img:
            screen.blit(assets.ember_meteor_img,
                        assets.ember_meteor_img.get_rect(center=(self.x, self.y)))


class NuclearShockwave:
    def __init__(self, x, y, game, bomb_branch=1):
        self.x = x
        self.y = y
        self.game = game
        self.bomb_branch = bomb_branch
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
        if self.bomb_branch == 2:
            color = (0, 0, 0, alpha)
        else:
            color = (255, 0, 0, alpha)
        s = pygame.Surface((self.radius * 2, self.radius * 2), pygame.SRCALPHA)
        pygame.draw.circle(s, color, (self.radius, self.radius), self.radius)
        screen.blit(s, (self.x - self.radius, self.y - self.radius))


class LanternShockwave:
    """星焰提灯的攻击表现：从塔中心向外扩散的金色光环。"""

    def __init__(self, x, y, radius):
        self.x = x
        self.y = y
        self.max_radius = int(radius)
        self.duration = 24
        self.timer = 0
        self.done = False

    def update(self):
        self.timer += 1
        if self.timer >= self.duration:
            self.done = True
        return not self.done

    def draw(self, screen):
        if self.done:
            return
        t = self.timer / self.duration
        radius = int(self.max_radius * (0.30 + 0.70 * t))
        if radius <= 0:
            return
        fade = 1.0 - t
        ring_width = max(4, int(18 * fade))
        pad = ring_width + 2
        size = radius * 2 + pad * 2
        surf = pygame.Surface((size, size), pygame.SRCALPHA)
        center = size // 2
        # 外扩的余晖填充 + 内层暖光
        pygame.draw.circle(surf, (255, 160, 50, int(42 * fade)),
                           (center, center), max(1, radius - ring_width // 2))
        pygame.draw.circle(surf, (255, 215, 110, int(58 * fade)),
                           (center, center), max(1, int((radius - ring_width) * 0.5)))
        # 亮环
        pygame.draw.circle(surf, (255, 240, 170, int(240 * fade)),
                           (center, center), radius, ring_width)
        screen.blit(surf, (self.x - center, self.y - center))


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
                reward = enemy.take_damage(damage, color=(100, 0, 100), scale=0.8, element="poison")
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


class IceWall:
    def __init__(self, x, y, game):
        self.x = x
        self.y = y
        self.game = game
        self.timer = 0
        self.duration = 0
        self.rect = pygame.Rect(x * TILE_SIZE, y * TILE_SIZE, TILE_SIZE, TILE_SIZE)
        self.image = assets.ice_wall_img
        game.temperature -= 5

    def update(self):
        self.timer += 1
        if self.timer >= self.duration:
            self.game.destroy_ice_wall(self)
            return False
        return True

    def draw(self, screen):
        screen.blit(self.image, (self.x * TILE_SIZE, self.y * TILE_SIZE))


class CreeperExplosion:
    def __init__(self, x, y, game, charged=False):
        self.x = x
        self.y = y
        self.game = game
        self.charged = charged
        self.frame = 0
        self.frame_timer = 0
        self.frame_duration = 6
        self.max_frames = 5
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
        if self.done or self.frame >= len(assets.tnt_explosion_frames):
            return
        img = assets.tnt_explosion_frames[self.frame]
        target = 640 if self.charged else 384
        if target != 384:
            img = pygame.transform.smoothscale(img, (target, target))
        rect = img.get_rect(center=(self.x, self.y))
        screen.blit(img, rect)


class Bee:
    SPEED = 5.0

    def __init__(self, x, y, game):
        self.x = float(x)
        self.y = float(y)
        self.game = game
        self.target = None
        self.done = False
        self.image = assets.bee_img

    def _pick_target(self):
        living = [e for e in self.game.enemies if e.health > 0]
        self.target = random.choice(living) if living else None

    def update(self):
        if self.done:
            return False
        if self.target is None or self.target.health <= 0:
            self._pick_target()
        for enemy in self.game.enemies:
            if enemy.health <= 0:
                continue
            if enemy.rect.collidepoint(self.x, self.y):
                # 百分比伤害，不吃毒系附魔加成
                dmg = max(1, int(enemy.max_health * 0.01))
                reward = enemy.take_damage(dmg, color=GREEN, ignore_armor=True, element="poison")
                self.game.coins += reward
                enemy.apply_poison(50)
                self.done = True
                return False
        if self.target is None:
            return True
        tx = self.target.rect.centerx
        ty = self.target.rect.centery
        dx = tx - self.x
        dy = ty - self.y
        dist = math.hypot(dx, dy)
        if dist <= self.SPEED:
            # 百分比伤害，不吃毒系附魔加成
            dmg = max(1, int(self.target.max_health * 0.01))
            reward = self.target.take_damage(dmg, color=GREEN, ignore_armor=True, element="poison")
            self.game.coins += reward
            self.target.apply_poison(50)
            self.done = True
            return False
        self.x += dx / dist * self.SPEED
        self.y += dy / dist * self.SPEED
        return True

    def draw(self, screen):
        if self.done or self.image is None:
            return
        screen.blit(self.image, self.image.get_rect(center=(int(self.x), int(self.y))))


class UnstableCrystal:
    def __init__(self, col, row, game):
        self.col = col
        self.row = row
        self.game = game
        self.x = col * TILE_SIZE + TILE_SIZE // 2
        self.y = row * TILE_SIZE + TILE_SIZE // 2
        self.rect = pygame.Rect(col * TILE_SIZE, row * TILE_SIZE,
                                UNSTABLE_CRYSTAL_SIZE, UNSTABLE_CRYSTAL_SIZE)
        img = assets.unstable_crystal_img
        if img is not None and img.get_size() != (UNSTABLE_CRYSTAL_SIZE, UNSTABLE_CRYSTAL_SIZE):
            img = pygame.transform.scale(img, (UNSTABLE_CRYSTAL_SIZE, UNSTABLE_CRYSTAL_SIZE))
        self.image = img
        self.exploding = False
        self.frame = 0
        self.frame_timer = 0
        self.frame_duration = 5
        self.max_frames = 5
        self.done = False
        self.age = 0

    def update(self):
        if self.done:
            return False
        if self.exploding:
            self.frame_timer += 1
            if self.frame_timer >= self.frame_duration:
                self.frame_timer = 0
                self.frame += 1
                if self.frame >= self.max_frames:
                    self.done = True
                    return False
            return True
        self.age += 1
        touched = False
        for enemy in self.game.enemies:
            if enemy.health <= 0:
                continue
            if enemy.rect.colliderect(self.rect):
                pct = max(1, int(enemy.max_health * 0.01))
                # 百分比伤害 = 真实伤害，不吃加成也不吃减伤
                reward = enemy.take_damage(pct, color=WHITE, scale=1.0,
                                           ignore_armor=True, element="explosion")
                self.game.coins += reward
                touched = True
        if touched:
            self.exploding = True
            self.frame = 0
            self.frame_timer = 0
        return True

    def draw(self, screen):
        if self.exploding:
            global _CRYSTAL_BLAST_FRAMES
            if _CRYSTAL_BLAST_FRAMES is None:
                _CRYSTAL_BLAST_FRAMES = [pygame.transform.smoothscale(f, (128, 128))
                                         for f in assets.tnt_explosion_frames]
            if self.frame < len(_CRYSTAL_BLAST_FRAMES):
                img = _CRYSTAL_BLAST_FRAMES[self.frame]
                screen.blit(img, img.get_rect(center=(self.x, self.y)))
        elif self.image:
            # 静态贴图：不再做上下浮动和紫色描边，避免水晶多时每帧额外绘制
            screen.blit(self.image, self.rect)

# ==========================================================================================
#  剑系（SWORD）特效
# ==========================================================================================
def rotated_about_pivot(image, deg_cw, pivot):
    """把 image 顺时针转 deg_cw 度，使其【左下角】精确落在 pivot 上。

    返回 (rotated_surface, topleft_x, topleft_y)。

    pygame.transform.rotate 正角是逆时针、且永远绕图心转，所以要自己反推图心位置：
      d  = 图心 -> 左下角 = (-w/2, +h/2)
      d' = R_cw(θ) · d
      图心必须放在 pivot - d'，再用 get_rect(center=...) 定位。
    """
    surf = pygame.transform.rotate(image, -deg_cw)   # 负号 = 顺时针
    w, h = image.get_size()
    W, H = surf.get_size()

    th = math.radians(deg_cw)
    c, s = math.cos(th), math.sin(th)
    dx, dy = -w / 2.0, h / 2.0
    rx = dx * c - dy * s
    ry = dx * s + dy * c
    return surf, pivot[0] - rx - W / 2.0, pivot[1] - ry - H / 2.0


class SwordSpin:
    """剑系的持续旋转表现。

    只要塔还处于「有敌人可打」的状态就一直转，角度连续累加、永不重置，
    所以视觉上是连续不停的一圈接一圈，不会转完一圈停一下。
    大小恒定（不缩放、不淡出）——用户明确要求旋转过程中尺寸不变。

    伤害不在这里结算：由 Tower._sword_attack 按 fire_rate 结算，
    视觉与伤害频率解耦，剑可以一直转，伤害仍按攻速跳。
    """

    SIZE = SWORD_SPIN_SIZE

    def __init__(self, tower, game, img_path, phase=0.0):
        self.tower = tower
        self.game = game
        self.img_path = img_path
        self.base = pygame.transform.scale(assets.load_image(img_path),
                                           (self.SIZE, self.SIZE))
        self.angle = phase % 360.0
        self._surf = None
        self._surf_angle = None

    def update(self):
        tower = self.tower
        # 塔被苦力怕炸掉 / 被 BOSS 抹除 / 被出售后会直接 kill()，
        # 之后 Game.update 的塔循环不再遍历它，sword_spinning 会永远停在 True。
        # 所以这里必须自己确认塔还活着，否则剑会留在原地一直转。
        if not tower.alive() or not getattr(tower, "sword_spinning", False):
            if getattr(tower, "sword_spin", None) is self:
                tower.sword_spin = None
            return False
        self.angle = (self.angle + SWORD_SPIN_SPEED) % 360.0
        return True

    def draw(self, screen):
        deg = self.angle + SWORD_ART_OFFSET
        if self._surf is None or self._surf_angle != deg:
            self._surf, self._ox, self._oy = rotated_about_pivot(
                self.base, deg, (0, 0))
            self._surf_angle = deg
        screen.blit(self._surf,
                    (int(self.tower.rect.centerx + self._ox),
                     int(self.tower.rect.centery + self._oy)))


class FallingStar:
    """星怒（剑系二阶分支 1）：从天而降一颗星星，落到目标点造成小范围伤害。"""

    def __init__(self, tx, ty, damage, game):
        self.tx = tx
        self.ty = ty
        self.x = float(tx)
        self.y = float(ty) - 520
        self.damage = damage
        self.game = game
        self.done = False
        self.speed = SWORD_METEOR_SPEED
        raw = assets.load_image("tower/star.png")
        self._img = pygame.transform.rotate(raw, 90)    # 竖直下落，拖尾朝上

    def update(self):
        if self.done:
            return False
        self.y += self.speed
        if self.y >= self.ty:
            self.y = self.ty
            self._impact()
            self.done = True
            return False
        return True

    def _impact(self):
        mult = self.game.sword_combo_mult()
        dmg = max(1, int(self.damage * mult))
        hits = 0
        prev = self.game.damage_element
        self.game.damage_element = "sword"
        try:
            for e in self.game.enemies:
                if e.health <= 0:
                    continue
                if math.hypot(e.rect.centerx - self.tx,
                              e.rect.centery - self.ty) <= TILE_SIZE:
                    reward = e.take_damage(dmg, color=SWORD_DAMAGE_COLOR,
                                           scale=self.game.sword_text_scale(),
                                           element="sword")
                    self.game.coins += reward
                    hits += 1
        finally:
            self.game.damage_element = prev
        self.game.register_sword_hits(hits)

    def draw(self, screen):
        screen.blit(self._img, self._img.get_rect(center=(int(self.x), int(self.y))))


class StarWrath:
    """狂星之怒（剑系三阶分支 2）：从地图右上角飞出、自动锁敌的星星。"""

    SPEED = SWORD_STAR_SPEED
    TURN_GAIN = SWORD_STAR_TURN_GAIN
    MAX_TURN = math.radians(SWORD_STAR_MAX_TURN)

    def __init__(self, x, y, angle, damage, game, remaining_fn):
        self.x = float(x)
        self.y = float(y)
        self.angle = angle
        self.damage = damage
        self.game = game
        self.remaining_fn = remaining_fn
        self.target = None
        self.done = False
        self.raw = assets.load_image("tower/star.png")
        self._img = None
        self._img_angle = None
        self._pick_target()

    def _pick_target(self):
        # 同一帧最多重算一次：一轮 10 颗星同帧创建，本来就会选同一个敌人
        self.target = self.game.sword_best_target(self.remaining_fn)

    def update(self):
        if self.done:
            return False
        if self.target is None or self.target.health <= 0:
            self._pick_target()

        if self.target is not None:
            tx, ty = self.target.rect.center
            desired = math.atan2(ty - self.y, tx - self.x)
            # 归一化到 (-π, π]：否则从 179° 转向 -179° 会绕一整圈
            diff = (desired - self.angle + math.pi) % (2 * math.pi) - math.pi
            # 比例项负责平滑，限幅项负责不发散，两者都要
            turn = max(-self.MAX_TURN, min(self.MAX_TURN, diff * self.TURN_GAIN))
            self.angle += turn

        self.x += math.cos(self.angle) * self.SPEED
        self.y += math.sin(self.angle) * self.SPEED

        if (self.x < -200 or self.x > SCREEN_WIDTH + 200
                or self.y < -200 or self.y > SCREEN_HEIGHT + 200):
            self.done = True
            return False

        # 只查所在格 + 周围 8 格，避免每帧对全场敌人做 collidepoint。
        # （_build_enemy_grid 会把大体型单位注册进它覆盖的每一格，不会漏）
        col = int(self.x) // TILE_SIZE
        row = int(self.y) // TILE_SIZE
        grid = self.game.enemy_grid
        for dc in (-1, 0, 1):
            for dr in (-1, 0, 1):
                for e in grid.get((col + dc, row + dr), ()):
                    if e.health <= 0 or not e.rect.collidepoint(self.x, self.y):
                        continue
                    mult = self.game.sword_combo_mult()
                    dmg = max(1, int(self.damage * mult))
                    prev = self.game.damage_element
                    self.game.damage_element = "sword"
                    try:
                        reward = e.take_damage(
                            dmg, color=SWORD_DAMAGE_COLOR,
                            scale=self.game.sword_text_scale(), element="sword")
                        self.game.coins += reward
                    finally:
                        self.game.damage_element = prev
                    self.game.register_sword_hits(1)
                    self.done = True
                    return False
        return True

    def draw(self, screen):
        deg = -math.degrees(self.angle)
        q = int(round(deg / 6.0)) * 6          # 角度量化，避免每帧 rotate
        if self._img is None or self._img_angle != q:
            self._img = pygame.transform.rotate(self.raw, q)
            self._img_angle = q
        screen.blit(self._img, self._img.get_rect(center=(int(self.x), int(self.y))))


class IceStarBurst:
    """神锅四芒星命中的小爆点：一圈冰蓝光环 + 四道向外射出的尖刺。

    刻意做得很轻：神锅 1 秒一发，如果照 IceExplosion 那种量级，
    铺两三座锅之后满屏都是爆炸，反而看不清弹道。
    """

    DURATION = 16

    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.timer = 0
        self.done = False

    def update(self):
        self.timer += 1
        if self.timer >= self.DURATION:
            self.done = True
        return not self.done

    def draw(self, screen):
        if self.done:
            return
        t = self.timer / self.DURATION
        fade = 1.0 - t
        radius = int(10 + 46 * t)
        alpha = int(235 * fade)
        surf = pygame.Surface((radius * 2 + 8, radius * 2 + 8), pygame.SRCALPHA)
        c = radius + 4
        # 冷色光晕（偏饱和的冰蓝，压在石砖背景上才看得见）
        pygame.draw.circle(surf, (70, 170, 255, int(alpha * 0.45)), (c, c), radius)
        pygame.draw.circle(surf, (170, 230, 255, int(alpha * 0.55)), (c, c),
                           max(1, int(radius * 0.55)))
        # 光环
        pygame.draw.circle(surf, (120, 210, 255, alpha), (c, c), radius,
                           max(1, int(5 * fade) + 1))
        # 四道尖刺（和四芒星的朝向一致）
        length = int(radius * 1.35)
        for dx, dy in ((0, -1), (0, 1), (-1, 0), (1, 0)):
            pygame.draw.line(surf, (225, 248, 255, alpha),
                             (c + dx * radius * 0.4, c + dy * radius * 0.4),
                             (c + dx * length, c + dy * length),
                             max(1, int(4 * fade) + 1))
        # 命中瞬间的中心闪白
        if t < 0.35:
            core = max(2, int(16 * (1 - t / 0.35)))
            pygame.draw.circle(surf, (255, 255, 255, 220), (c, c), core)
        screen.blit(surf, (self.x - c, self.y - c))


class MasterpieceShockwave:
    """「臻品呈现」大招落地时的全屏冲击波。

    节奏是「先放视频 → 放完从地图中心炸一下 → 炸的同时冒伤害飘字」。
    所以这个特效必须够大够亮：半径直接取到能覆盖屏幕四角，
    否则铺了 9 座锅、伤害数字又被别的东西糊住，玩家根本看不出是哪一下打出来的。

    实现上不画「半径大小的圆」再 blit —— 最大半径 1700+ 时那张 SRCALPHA 图要 46MB。
    这里改成一块屏幕大小的画布（16MB，实例内复用），圆心画到画布外也没关系，pygame 会自己裁。
    """

    DURATION = 40

    def __init__(self, x, y, max_radius):
        self.x = x
        self.y = y
        self.max_radius = max(1, int(max_radius))
        self.timer = 0
        self.done = False
        self._surf = None

    def update(self):
        self.timer += 1
        if self.timer >= self.DURATION:
            self.done = True
        return not self.done

    def draw(self, screen):
        if self.done:
            return
        w, h = screen.get_size()
        if self._surf is None:
            self._surf = pygame.Surface((w, h), pygame.SRCALPHA)
        surf = self._surf
        surf.fill((0, 0, 0, 0))

        t = self.timer / self.DURATION
        fade = 1.0 - t
        ease = 1 - (1 - t) ** 3          # 先快后慢：前 1/3 就冲到 70%
        radius = int(self.max_radius * (0.06 + 0.94 * ease))
        cx, cy = int(self.x), int(self.y)

        # 起手整屏冷色闪光
        if t < 0.4:
            surf.fill((150, 215, 255, int(70 * (1 - t / 0.4))))

        # 放射光条
        spokes = 16
        length = int(radius * 0.92)
        if length > 8:
            spoke_alpha = int(95 * fade)
            for i in range(spokes):
                ang = math.tau * i / spokes
                pygame.draw.line(
                    surf, (215, 245, 255, spoke_alpha),
                    (cx + math.cos(ang) * radius * 0.25, cy + math.sin(ang) * radius * 0.25),
                    (cx + math.cos(ang) * length, cy + math.sin(ang) * length),
                    max(1, int(6 * fade) + 1))

        # 主环 + 两道余波
        pygame.draw.circle(surf, (238, 251, 255, int(245 * fade)),
                           (cx, cy), radius, max(2, int(30 * fade) + 2))
        pygame.draw.circle(surf, (150, 220, 255, int(150 * fade)),
                           (cx, cy), max(1, int(radius * 0.86)), max(1, int(14 * fade) + 1))
        pygame.draw.circle(surf, (110, 195, 255, int(90 * fade)),
                           (cx, cy), max(1, int(radius * 0.70)), max(1, int(8 * fade) + 1))

        # 中心爆闪：柔光晕 + 高亮核心（不用一整块实心圆，太挡视野）
        if t < 0.3:
            k = 1 - t / 0.3
            pygame.draw.circle(surf, (170, 230, 255, int(70 * k)),
                               (cx, cy), max(1, int(320 * k)))
            pygame.draw.circle(surf, (255, 255, 255, int(235 * k)),
                               (cx, cy), max(1, int(130 * k)))

        screen.blit(surf, (0, 0))
