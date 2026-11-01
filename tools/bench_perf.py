"""性能基准：模拟后期高负载场景，测 update / draw 的每帧耗时。

用法：D:/pytools/python.exe tools/bench_perf.py [塔数] [敌人数] [飘字数]
"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

pygame.init()
screen = pygame.display.set_mode((1920, 1080))
clock = pygame.time.Clock()

import assets
import game as game_mod
import tower as tower_mod
import enemy as enemy_mod
from config import TowerType, EnemyType

assets.init_assets()

N_TOWER = int(sys.argv[1]) if len(sys.argv) > 1 else 40
N_ENEMY = int(sys.argv[2]) if len(sys.argv) > 2 else 200
N_TEXT = int(sys.argv[3]) if len(sys.argv) > 3 else 300
FRAMES = int(sys.argv[4]) if len(sys.argv) > 4 else 60

g = game_mod.Game(screen, clock)
g.save_game = lambda: None
g.state = game_mod.GameState.PLAYING
g.current_bgm = ""
g.coins = 10_000_000

# 铺塔：棋盘式铺满可用格子
placed = 0
for y in range(1, 12):
    for x in range(1, 28):
        if placed >= N_TOWER:
            break
        if not g.can_build_tower(x, y):
            continue
        ttype = [TowerType.PHYSICAL, TowerType.ELECTRIC, TowerType.ICE,
                 TowerType.FLAME, TowerType.POISON, TowerType.BOMB][placed % 6]
        g.build_tower(x, y, ttype)
        placed += 1
    if placed >= N_TOWER:
        break

for t in list(g.towers):
    for _ in range(10):
        t.upgrade()

# 铺怪：直接沿路径摆
for i in range(N_ENEMY):
    e = enemy_mod.Enemy(g.path, EnemyType.NORMAL, g)
    idx = min(len(g.path) - 1, (i * 7) % len(g.path))
    e.pos_x, e.pos_y = g.path[idx]
    e.rect.center = (int(e.pos_x), int(e.pos_y))
    g.enemies.add(e)

g._build_enemy_grid()

# 铺飘字
for i in range(N_TEXT):
    g.spawn_damage_text(1234 + i, (400 + (i * 37) % 1000, 200 + (i * 53) % 700))

print(f"塔 {len(g.towers)} / 怪 {len(g.enemies)} / 飘字 {len(g.damage_texts)} / 帧数 {FRAMES}")

t_update = 0.0
t_draw = 0.0
t_flip = 0.0
for _ in range(FRAMES):
    a = time.perf_counter()
    g.update()
    b = time.perf_counter()
    g.draw()
    c = time.perf_counter()
    pygame.display.flip()
    d = time.perf_counter()
    t_update += b - a
    t_draw += c - b
    t_flip += d - c

n = FRAMES
print(f"update {t_update / n * 1000:7.2f} ms")
print(f"draw   {t_draw / n * 1000:7.2f} ms")
print(f"flip   {t_flip / n * 1000:7.2f} ms")
print(f"合计   {(t_update + t_draw + t_flip) / n * 1000:7.2f} ms  -> "
      f"{n / (t_update + t_draw + t_flip):.1f} FPS 上限")
print(f"结束时：怪 {len(g.enemies)} / 子弹 {len(g.bullets)} / 飘字 {len(g.damage_texts)}")
