import random
from config import (EnemyType, FINAL_BOSS_WAVE, WAVE_ENEMY_BASE, WAVE_ENEMY_LINEAR,
                    WAVE_ENEMY_TURN_WAVE, WAVE_ENEMY_LATE_STEP, WAVE_ENEMY_CAP,
                    WAVE_GHOST_CAP)


class WaveManager:
    def __init__(self):
        self.current_wave = 0
        self.total_waves = FINAL_BOSS_WAVE
        self.enemies_spawned = 0
        self.enemies_to_spawn = 0
        self.spawn_timer = 0
        self.spawn_delay = 40
        self.wave_preparation_time = 360
        self.wave_timer = 0
        self.elite_wave_interval = 5
        self.boss_wave_interval = 10

    def start_new_wave(self):
        self.current_wave += 1
        self.enemies_spawned = 0
        if self.current_wave in (50, FINAL_BOSS_WAVE):
            self.enemies_to_spawn = 1
            self.gold_armored_count = 0
            self.ghost_count = 0
        else:
            self.gold_armored_count = self.calculate_gold_armored_count()
            self.ghost_count = self.calculate_ghost_count()
            self.enemies_to_spawn = self.calculate_enemies_to_spawn() + self.gold_armored_count + self.ghost_count
        self.gold_armored_spawned = 0
        self.ghost_spawned = 0
        self.spawn_timer = 0
        self.wave_timer = self.wave_preparation_time

    def calculate_enemies_to_spawn(self):
        w = self.current_wave
        if w <= WAVE_ENEMY_TURN_WAVE:
            base_enemies = WAVE_ENEMY_BASE + w * WAVE_ENEMY_LINEAR
        else:
            # 收敛段：每波只 +0.8，并卡上限，避免后期两三百只同屏拖死帧率
            base_enemies = (WAVE_ENEMY_BASE + WAVE_ENEMY_TURN_WAVE * WAVE_ENEMY_LINEAR
                            + int((w - WAVE_ENEMY_TURN_WAVE) * WAVE_ENEMY_LATE_STEP))
            base_enemies = min(base_enemies, WAVE_ENEMY_CAP)
        if self.is_elite_wave():
            base_enemies += 5
        elif self.is_boss_wave():
            base_enemies += 10
        return base_enemies

    def calculate_gold_armored_count(self):
        if self.current_wave >= 12 and (self.current_wave - 12) % 4 == 0:
            return (self.current_wave - 8) // 4
        return 0

    def calculate_ghost_count(self):
        if self.current_wave >= 5 and self.current_wave % 5 == 0:
            return min(self.current_wave // 2 + 4, WAVE_GHOST_CAP)
        return 0

    def is_elite_wave(self):
        return self.current_wave % self.elite_wave_interval == 0 and self.current_wave > 0

    def is_boss_wave(self):
        return self.current_wave % self.boss_wave_interval == 0 and self.current_wave > 0

    def update(self):
        if self.wave_timer > 0:
            self.wave_timer -= 1
            return None

        if self.enemies_spawned < self.enemies_to_spawn:
            self.spawn_timer += 1
            if self.spawn_timer >= self.spawn_delay:
                self.spawn_timer = 0
                self.enemies_spawned += 1
                return self.select_enemy_type()
        return None

    def select_enemy_type(self):
        if self.current_wave == 50:
            return EnemyType.HEROBRINE
        if self.current_wave == FINAL_BOSS_WAVE:
            return EnemyType.FINAL_BOSS
        if self.gold_armored_spawned < self.gold_armored_count:
            self.gold_armored_spawned += 1
            return EnemyType.GOLD_ARMORED
        if self.ghost_spawned < self.ghost_count:
            self.ghost_spawned += 1
            return EnemyType.GHOST
        rand = random.random()
        if self.is_boss_wave() and self.enemies_spawned == self.enemies_to_spawn:
            return EnemyType.WITHER
        elif self.is_elite_wave() and rand < 0.3:
            return EnemyType.ELITE
        elif random.random() < 0.04:
            return EnemyType.CREEPER
        elif random.random() < 0.04:
            return EnemyType.SPIDER
        elif self.current_wave > 12 and random.random() < 0.05:
            # 烈焰人：飞行 + 免疫火系，逼玩家留一手冰塔
            return EnemyType.BLAZE
        elif self.current_wave > 15 and rand < 0.10:
            return EnemyType.SLIME
        elif self.current_wave > 15 and rand < 0.18:
            return EnemyType.MAGMA_CUBE
        elif self.current_wave > 8 and rand < 0.15:
            return EnemyType.IRON_ARMORED
        elif self.current_wave > 8 and rand < 0.08:
            return EnemyType.DIAMOND_ARMORED
        elif self.current_wave > 8 and rand < 0.04:
            return EnemyType.NETHERITE_ARMORED
        elif self.current_wave > 10 and rand < 0.2:
            return EnemyType.TANK
        elif self.current_wave > 5 and rand < 0.3:
            return EnemyType.FAST
        else:
            return EnemyType.NORMAL

    def is_wave_complete(self, enemies):
        return self.enemies_spawned >= self.enemies_to_spawn and len(enemies) == 0

    def is_preparation_complete(self):
        return self.wave_timer <= 0

    def is_game_complete(self, enemies):
        return self.current_wave >= self.total_waves and self.is_wave_complete(enemies)
