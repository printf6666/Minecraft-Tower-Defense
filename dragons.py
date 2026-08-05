import pygame
import math
import assets
from config import *


class Dragon(pygame.sprite.Sprite):
    def __init__(self, path, dragon_type, tower_level, game):
        super().__init__()
        self.path = path
        self.dragon_type = dragon_type
        self.tower_level = tower_level
        self.game = game

        if dragon_type == "ice":
            self.image = assets.ice_dragon_img
            self.color = ICE_BLUE
            self.damage_multiplier = {11: 30, 12: 60, 13: 90, 14: 120, 15: 150}
            self.freeze_duration = 3 * 60
        elif dragon_type == "electric":
            self.image = assets.electric_dragon_img
            self.color = GOLD
            self.damage_multiplier = {11: 50, 12: 100, 13: 150, 14: 200, 15: 250}
            self.stun_duration = 60
        else:
            self.image = assets.fire_dragon_img
            self.color = YELLOW
            self.damage_multiplier = {11: 36, 12: 72, 13: 108, 14: 144, 15: 180}
            self.burn_duration = 20 * 60

        self.image_flipped = pygame.transform.flip(self.image, True, False)
        self.current_image = self.image

        self.rect = self.image.get_rect()

        end_point = self.path[-1]
        self.x = end_point[0] * TILE_SIZE + TILE_SIZE // 2 - 128
        self.y = end_point[1] * TILE_SIZE + TILE_SIZE // 2 - 128

        self.rect.topleft = (self.x, self.y)

        self.path_idx = len(self.path) - 1
        self.speed = 8
        if game.dragon_legend_active():
            self.speed = 14
        self.target_x = None
        self.target_y = None
        self.update_target()

        self.done = False
        self.hit_enemies = set()
        self.last_direction = -1

    def update_target(self):
        if self.path_idx > 0:
            target_point = self.path[self.path_idx - 1]
            self.target_x = target_point[0] * TILE_SIZE + TILE_SIZE // 2 - 128
            self.target_y = target_point[1] * TILE_SIZE + TILE_SIZE // 2 - 128
        else:
            start_point = self.path[0]
            self.target_x = start_point[0] * TILE_SIZE + TILE_SIZE // 2 - 128
            self.target_y = start_point[1] * TILE_SIZE + TILE_SIZE // 2 - 128

    def update(self):
        if self.done:
            return

        dx = self.target_x - self.x
        dy = self.target_y - self.y
        dist = (dx * dx + dy * dy) ** 0.5

        if dx > 1:
            current_dir = 1
        elif dx < -1:
            current_dir = -1
        else:
            current_dir = self.last_direction

        if current_dir != self.last_direction:
            self.last_direction = current_dir
            if current_dir == 1:
                self.current_image = self.image_flipped
            else:
                self.current_image = self.image

        if dist < self.speed:
            self.x = self.target_x
            self.y = self.target_y
            self.path_idx -= 1
            if self.path_idx <= 0:
                self.done = True
                return
            self.update_target()
        else:
            self.x += (dx / dist) * self.speed
            self.y += (dy / dist) * self.speed

        self.rect.topleft = (self.x, self.y)

        self.check_collisions()

    def check_collisions(self):
        col = int(self.rect.centerx) // TILE_SIZE
        row = int(self.rect.centery) // TILE_SIZE
        grid = self.game.enemy_grid

        for dc in (-1, 0, 1):
            for dr in (-1, 0, 1):
                for enemy in grid.get((col + dc, row + dr), ()):
                    if enemy.health > 0 and enemy not in self.hit_enemies:
                        if self.rect.colliderect(enemy.rect):
                            self.hit_enemies.add(enemy)
                            self.deal_damage(enemy)

    def deal_damage(self, enemy):
        multiplier = self.damage_multiplier.get(self.tower_level, 30)
        if self.game.dragon_legend_active():
            multiplier *= 2
        if self.dragon_type == "ice":
            damage = multiplier * abs(self.game.temperature)
            color = ICE_BLUE
            reward = enemy.take_damage(damage, color=color)
            self.game.coins += reward
            enemy.apply_freeze(self.freeze_duration)
        elif self.dragon_type == "electric":
            damage = multiplier * abs(self.game.temperature)
            color = GOLD
            reward = enemy.take_damage(damage, color=color)
            self.game.coins += reward
            enemy.apply_stun(self.stun_duration)
        else:
            damage = multiplier * abs(self.game.temperature)
            color = YELLOW
            reward = enemy.take_damage(damage, color=color)
            self.game.coins += reward
            enemy.apply_burn(self.game.temperature, self.burn_duration)

    def draw(self, screen):
        screen.blit(self.current_image, self.rect)