"""巫师魅惑出来的召唤物：绵羊 / 山羊 / 粉色绵羊。

和龙（dragons.Dragon）是同一套玩法，区别只有两点：
  1. 龙从终点（家里）出发，绵羊 / 山羊从「被魅惑的那只怪原地」出发；
  2. 龙往起点走，绵羊 / 山羊同样往起点走，走完就消失。

所以这里复用 Dragon 的航点推进思路：把「被魅惑的位置 + 当前格 → 起点」串成
一条航点表，逐个走过去，路上撞到谁就给谁结算一次（每只怪只结算一次）。

伤害口径：
  · 绵羊 / 粉色绵羊：目标 1% 最大生命，ignore_armor 真实伤害（和龙的百分比真伤一致）；
  · 山羊：8000 点魔法伤害，吃魔法系加成与抗性，并击退地面单位 60px；
  · 粉色绵羊额外带魅惑：命中后按 15 级巫师（4%）的概率把目标再变成粉色绵羊，
    可以无限套娃，但同屏数量有上限（PINK_SHEEP_CAP），防止把帧率套炸。
"""

import math
import random

import pygame

import assets
from config import (TILE_SIZE, GOAT_DAMAGE, GOAT_KNOCKBACK, GOAT_SPEED,
                    SHEEP_HP_PCT, SHEEP_SPEED, PINK_SHEEP_CHARM_CHANCE,
                    PINK_SHEEP_CAP, MAGIC_PINK, is_charmable)


class CharmBeast(pygame.sprite.Sprite):
    def __init__(self, path, kind, start_x, start_y, path_index, tower_level, game):
        super().__init__()
        self.path = path
        self.kind = kind            # "sheep" / "goat" / "pink_sheep"
        self.game = game
        self.tower_level = tower_level

        if kind == "goat":
            self.image = assets.goat_img
            self.speed = GOAT_SPEED
        elif kind == "pink_sheep":
            self.image = assets.pink_sheep_img
            self.speed = SHEEP_SPEED
        else:
            self.image = assets.sheep_img
            self.speed = SHEEP_SPEED

        self.image_flipped = pygame.transform.flip(self.image, True, False)
        self.current_image = self.image
        self.rect = self.image.get_rect(center=(int(start_x), int(start_y)))

        self.x = float(start_x)
        self.y = float(start_y)

        # 航点：当前位置 → 所在格 → … → 起点
        self.path_idx = max(0, min(path_index, len(path) - 1))
        self.waypoints = [(self.x, self.y)]
        for i in range(self.path_idx, -1, -1):
            gx, gy = path[i]
            self.waypoints.append((gx * TILE_SIZE + TILE_SIZE // 2,
                                   gy * TILE_SIZE + TILE_SIZE // 2))
        self.wp_idx = 1

        self.done = False
        self.hit_enemies = set()
        self.last_direction = -1

    def update(self):
        if self.done:
            return
        if self.wp_idx >= len(self.waypoints):
            self.done = True
            return

        tx, ty = self.waypoints[self.wp_idx]
        dx = tx - self.x
        dy = ty - self.y
        dist = math.hypot(dx, dy)

        if dx > 1:
            current_dir = 1
        elif dx < -1:
            current_dir = -1
        else:
            current_dir = self.last_direction

        if current_dir != self.last_direction:
            self.last_direction = current_dir
            self.current_image = self.image_flipped if current_dir == 1 else self.image

        if dist <= self.speed:
            self.x = tx
            self.y = ty
            self.wp_idx += 1
            self.rect.center = (int(self.x), int(self.y))
            if self.wp_idx >= len(self.waypoints):
                self.done = True
                return
        else:
            self.x += dx / dist * self.speed
            self.y += dy / dist * self.speed
            self.rect.center = (int(self.x), int(self.y))

        self.check_collisions()

    def check_collisions(self):
        col = int(self.rect.centerx) // TILE_SIZE
        row = int(self.rect.centery) // TILE_SIZE
        grid = self.game.enemy_grid
        for dc in (-1, 0, 1):
            for dr in (-1, 0, 1):
                for enemy in grid.get((col + dc, row + dr), ()):
                    if enemy.health <= 0 or enemy in self.hit_enemies:
                        continue
                    if self.rect.colliderect(enemy.rect):
                        self.hit_enemies.add(enemy)
                        self.deal_damage(enemy)

    def deal_damage(self, enemy):
        if self.kind == "goat":
            damage = int(GOAT_DAMAGE * self.game.get_element_damage_multiplier("magic"))
            reward = enemy.take_damage(damage, color=MAGIC_PINK, element="magic")
            self.game.coins += reward
            if enemy.health > 0:
                # 击退走敌人自己的 apply_knockback：盔甲怪免疫击退的规则保持一致
                enemy.apply_knockback(GOAT_KNOCKBACK)
            return

        # 绵羊 / 粉色绵羊：1% 最大生命，纯真实伤害（不吃抗性与任何增伤）
        damage = int(enemy.max_health * SHEEP_HP_PCT)
        if damage > 0:
            reward = enemy.take_damage(damage, color=MAGIC_PINK, scale=0.9,
                                       ignore_armor=True, element="magic")
            self.game.coins += reward

        if self.kind == "pink_sheep":
            self.try_charm(enemy)

    def try_charm(self, enemy):
        """粉色绵羊的魅惑：概率等同 15 级巫师，把目标再变成一只粉色绵羊。"""
        if enemy.health <= 0 or not is_charmable(enemy.enemy_type):
            return
        if self.game.count_pink_sheep() >= PINK_SHEEP_CAP:
            return
        if random.random() < PINK_SHEEP_CHARM_CHANCE:
            self.game.charm_enemy(enemy, "pink_sheep", self.tower_level)

    def draw(self, screen):
        screen.blit(self.current_image, self.rect)
