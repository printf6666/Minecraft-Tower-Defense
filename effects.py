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
            final_damage = (20000 + 100 * game.temperature) * (tower_level - 10)
            for enemy in game.enemies:
                if enemy.health <= 0:
                    continue
                reward = enemy.take_damage(final_damage, color=RED, scale=1.2)
                game.coins += reward
                enemy.apply_stun(120)
                enemy.apply_poison(tower_level * 10)
        else:
            percent_damage = [0.04, 0.05, 0.06, 0.07, 0.08][tower_level - 11]
            fixed_damage = [2000, 4000, 6000, 8000, 10000][tower_level - 11]
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