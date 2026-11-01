"""持续产生飘字的压力测试：每帧新增 N 条，模拟后期子弹海。"""
import os, sys, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("SDL_VIDEODRIVER", "dummy"); os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
import pygame
pygame.init()
screen = pygame.display.set_mode((1920, 1080)); clock = pygame.time.Clock()
import assets, game as gm, enemy as em
from config import TowerType, EnemyType
assets.init_assets()

N_TOWER = int(sys.argv[1]) if len(sys.argv) > 1 else 40
N_ENEMY = int(sys.argv[2]) if len(sys.argv) > 2 else 200
PER_FRAME = int(sys.argv[3]) if len(sys.argv) > 3 else 30
FRAMES = int(sys.argv[4]) if len(sys.argv) > 4 else 60

g = gm.Game(screen, clock); g.save_game = lambda: None
g.state = gm.GameState.PLAYING; g.current_bgm = ""; g.coins = 10_000_000
placed = 0
for y in range(1, 12):
    for x in range(1, 28):
        if placed >= N_TOWER: break
        if not g.can_build_tower(x, y): continue
        g.build_tower(x, y, [TowerType.PHYSICAL, TowerType.ELECTRIC, TowerType.ICE,
                             TowerType.FLAME, TowerType.POISON, TowerType.BOMB][placed % 6]); placed += 1
    if placed >= N_TOWER: break
for t in list(g.towers):
    for _ in range(10): t.upgrade()
for i in range(N_ENEMY):
    e = em.Enemy(g.path, EnemyType.NORMAL, g)
    idx = min(len(g.path) - 1, (i * 7) % len(g.path))
    e.pos_x, e.pos_y = g.path[idx]; e.rect.center = (int(e.pos_x), int(e.pos_y)); g.enemies.add(e)

tu = td = tf = 0.0
peak = 0
for f in range(FRAMES):
    for i in range(PER_FRAME):
        g.spawn_damage_text(1234 + (f * i) % 977, (400 + (i * 37 + f * 13) % 1000, 200 + (i * 53) % 700))
    a = time.perf_counter(); g.update(); b = time.perf_counter()
    g.draw(); c = time.perf_counter(); pygame.display.flip(); d = time.perf_counter()
    tu += b - a; td += c - b; tf += d - c
    peak = max(peak, len(g.damage_texts))
n = FRAMES
print(f"塔 {len(g.towers)} / 怪 {len(g.enemies)} / 每帧 +{PER_FRAME} 条飘字")
print(f"update {tu/n*1000:7.2f} ms | draw {td/n*1000:7.2f} ms | 合计 {(tu+td+tf)/n*1000:7.2f} ms -> {n/(tu+td+tf):.1f} FPS")
print(f"飘字峰值 {peak} | 结束 怪{len(g.enemies)} 弹{len(g.bullets)} 字{len(g.damage_texts)}")
