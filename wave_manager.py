import random
from config import EnemyType


class WaveManager:
    def __init__(self):
        self.current_wave = 0
        self.total_waves = 50
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
        if self.current_wave == 50:
            self.enemies_to_spawn = 1
            self.gold_armored_count = 0
            self.ghost_count = 0
            self.gold_nautilus_count = 0
        else:
            self.gold_armored_count = self.calculate_gold_armored_count()
            self.ghost_count = self.calculate_ghost_count()
            self.gold_nautilus_count = self.calculate_gold_nautilus_count()
            self.enemies_to_spawn = self.calculate_enemies_to_spawn() + self.gold_armored_count + self.ghost_count + self.gold_nautilus_count
        self.gold_armored_spawned = 0
        self.ghost_spawned = 0
        self.gold_nautilus_spawned = 0
        self.spawn_timer = 0
        self.wave_timer = self.wave_preparation_time

    def calculate_enemies_to_spawn(self):
        base_enemies = 5 + self.current_wave * 2
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
            return self.current_wave // 2 + 4
        return 0

    def calculate_gold_nautilus_count(self):
        if self.current_wave >= 15 and (self.current_wave - 15) % 5 == 0:
            return (self.current_wave - 10) // 5
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
        if self.gold_armored_spawned < self.gold_armored_count:
            self.gold_armored_spawned += 1
            return EnemyType.GOLD_ARMORED
        if self.ghost_spawned < self.ghost_count:
            self.ghost_spawned += 1
            return EnemyType.GHOST
        if self.gold_nautilus_spawned < self.gold_nautilus_count:
            self.gold_nautilus_spawned += 1
            return EnemyType.GOLD_NAUTILUS
        rand = random.random()
        if self.is_boss_wave() and self.enemies_spawned == self.enemies_to_spawn:
            return EnemyType.WITHER
        elif self.is_elite_wave() and rand < 0.3:
            return EnemyType.ELITE
        elif self.current_wave > 15 and rand < 0.10:
            return EnemyType.SLIME
        elif self.current_wave > 15 and rand < 0.18:
            return EnemyType.MAGMA_CUBE
        elif self.current_wave >= 15 and rand < 0.08:
            return EnemyType.WITCH
        elif self.current_wave > 8 and rand < 0.15:
            return EnemyType.IRON_ARMORED
        elif self.current_wave > 12 and rand < 0.25:
            return EnemyType.NAUTILUS
        elif self.current_wave > 20 and rand < 0.15:
            return EnemyType.IRON_NAUTILUS
        elif self.current_wave > 8 and rand < 0.08:
            return EnemyType.DIAMOND_ARMORED
        elif self.current_wave > 25 and rand < 0.10:
            return EnemyType.DIAMOND_NAUTILUS
        elif self.current_wave > 8 and rand < 0.04:
            return EnemyType.NETHERITE_ARMORED
        elif self.current_wave > 30 and rand < 0.08:
            return EnemyType.NETHERITE_NAUTILUS
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
