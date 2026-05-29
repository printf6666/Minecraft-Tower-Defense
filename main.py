import pygame
import assets
from config import SCREEN_WIDTH, SCREEN_HEIGHT
from game import Game

def main():
    pygame.init()
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.FULLSCREEN | pygame.SCALED)
    pygame.display.set_caption("像素防线 · 晶域守卫")
    clock = pygame.time.Clock()
    assets.init_assets()
    game = Game(screen, clock)
    game.run()
if __name__ == "__main__":
    main()
