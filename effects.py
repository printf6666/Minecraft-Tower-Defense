import math
import random
import pygame
import assets
from config import *


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
                reward = enemy.take_damage(pct_dmg, color=WHITE, scale=1.0)
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
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.frame_index = 0
        self.frame_accum = 0

    def update(self):
        self.frame_accum += 1
        if self.frame_accum >= 3:
            self.frame_accum = 0
            self.frame_index += 1
        return self.frame_index < len(assets.resonance_storm_frames)

    def draw(self, surface):
        if self.frame_index >= len(assets.resonance_storm_frames):
            return
        img = assets.resonance_storm_frames[self.frame_index]
        surface.blit(img, img.get_rect(center=(self.x, self.y)))


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
                reward = enemy.take_damage(damage, color=ICE_BLUE, scale=0.8)
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


class PoisonContractExplosion:
    def __init__(self, x, y, game):
        self.x = x
        self.y = y
        self.duration = 6
        self.radius = 128
        game.poison_base_damage += 1
        for enemy in game.enemies:
            if enemy.health <= 0:
                continue
            dx = enemy.rect.centerx - x
            dy = enemy.rect.centery - y
            if (dx * dx + dy * dy) <= self.radius * self.radius:
                reward = enemy.take_damage(900, color=GREEN, scale=0.8)
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
            final_damage = (40000 + 400 * game.temperature) * (tower_level - 10)
            final_damage = int(final_damage * game.get_enchant_damage_multiplier(TowerType.BOMB))
            for enemy in game.enemies:
                if enemy.health <= 0:
                    continue
                reward = enemy.take_damage(final_damage, color=RED, scale=1.2)
                game.coins += reward
                enemy.apply_stun(120)
        else:
            percent_damage = [0.02, 0.04, 0.06, 0.08, 0.1][tower_level - 11]
            fixed_damage = [2000, 4000, 6000, 8000, 10000][tower_level - 11]
            if Enchantment.WITHER_ROSE in game.enchantments:
                percent_damage += 0.008
            for enemy in game.enemies:
                if enemy.health <= 0:
                    continue
                percent_dmg = int(enemy.max_health * percent_damage)
                reward = enemy.take_damage(percent_dmg, color=RED, scale=1.2)
                reward += enemy.take_damage(fixed_damage, color=RED, scale=1.2)
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


class IceWall:
    def __init__(self, x, y, game):
        self.x = x
        self.y = y
        self.game = game
        self.timer = 0
        self.duration = 0
        self.rect = pygame.Rect(x * TILE_SIZE, y * TILE_SIZE, TILE_SIZE, TILE_SIZE)
        self.image = assets.ice_wall_img
        game.temperature = max(-273, game.temperature - 5)

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