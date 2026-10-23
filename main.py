import pygame
import assets
import audio
from config import SCREEN_WIDTH, SCREEN_HEIGHT
from game import Game

def main():
    pygame.init()
    # 音频必须在 assets.init_assets() 之前探测：后者会用 pygame.mixer.Sound
    # 预加载音效。没有音频设备时若不先降级，这里拿到的一堆 None
    # 会让后续 14 处 mixer 调用在第一帧就崩。
    audio.init()
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.FULLSCREEN | pygame.SCALED)
    pygame.display.set_caption("Minecraft Tower Defense")
    clock = pygame.time.Clock()
    assets.init_assets()
    game = Game(screen, clock)
    game.run()
if __name__ == "__main__":
    main()