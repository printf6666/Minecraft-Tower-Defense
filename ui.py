import pygame
import math
import assets
from config import *
from tower import TowerType
from enemy import EnemyType
from effects import WindExplosion, IceExplosion, DragonBreathPool, LightningEffect, HorizontalLightningEffect, PoisonSplash, TNTExplosion, MushroomExplosion, NuclearShockwave, WitherSplash


def get_tower_info(game, tower):
    base_cost_map = {ttype: cost for ttype, name, cost, key in TOWER_DATA}
    info = []
    if tower.type == TowerType.PHYSICAL:
        if tower.level >= 11:
            if tower.physical_branch == 2:
                info = [f"天堂陨落长弓 Lv{tower.level}", f"伤害:{tower.damage}", f"攻击间隔:0.5s", f"将当前金币的1%作为伤害加成", f"12方向散射", "按 R 切换分支"]
            else:
                info = [f"时空撕裂之矢 Lv{tower.level}", f"伤害:{tower.damage}", f"攻击间隔:0.5s",
                        f"将当前金币的1%作为伤害加成", f"破甲:受伤永久增加20%", "按 R 切换分支"]
        elif tower.level >= 6:
            info = [f"黄金箭塔 Lv{tower.level}", f"伤害:{tower.damage}", f"攻击间隔:0.5s", f"将当前金币的1%作为伤害加成"]
        else:
            info = [f"箭塔 Lv{tower.level}", f"伤害:{tower.damage}", f"攻击间隔:{tower.fire_rate / 60}s"]
    elif tower.type == TowerType.PRODUCTION:
        if tower.level >= 11:
            info = [f"无尽矿 Lv{tower.level}", f"全局产量:{game.gold_per_second}/s",
                    f"全局每波产出:{5 * game.gold_per_wave}*当前波数", f"全局每波利息:{round(100 * game.gold_profit_per_wave, 1)}%", "放置在金矿石上时产出+100%"]
        elif tower.level >= 6:
            info = [f"下界合金矿 Lv{tower.level}", f"全局每波产出:{5 * game.gold_per_wave}*当前波数",
                    f"全局产量:{game.gold_per_second}/s", "放置在金矿石上时产出+100%"]
        else:
            info = [f"金矿 Lv{tower.level}", f"全局产量:{game.gold_per_second}/s", "放置在金矿石上时产出+100%"]
    elif tower.type == TowerType.ICE:
        if tower.level >= 11:
            if tower.ice_branch == 2:
                ice_dmg = {11: 30, 12: 60, 13: 90, 14: 120, 15: 150}
                info = [f"唤龙冰晶石 Lv{tower.level}", f"减速:50%", f"伤害:{tower.damage}", f"冻结:{tower.freeze_time}s",
                        f"2%召唤冰龙:{ice_dmg.get(tower.level,30)}倍温度+冰冻3s", f"攻击间隔:0.5s", "按R切换形态"]
            elif tower.ice_branch == 3:
                wall_duration = {11: 2, 12: 2.5, 13: 3, 14: 3.5, 15: 4}
                wall_chance = {11: 2, 12: 2.5, 13: 3, 14: 3.5, 15: 4}
                info = [f"冰墙 Lv{tower.level}", f"伤害:{tower.damage}", f"冻结:{tower.freeze_time}s",
                        f"子弹每经过1格道路{wall_chance.get(tower.level, 3)}%生成冰墙",
                        f"冰墙持续:{wall_duration.get(tower.level, 2)}s(火雨天减半)",
                        f"每道冰墙降低5度温度", "阻挡地面怪物", "按R切换形态"]
            else:
                bonus_pct = 300 * (tower.level - 10)
                info = [f"冰霜炸弹 Lv{tower.level}", f"减速:50%", f"伤害:{tower.damage}", f"冻结:{tower.freeze_time}s",
                        f"对冻结+{bonus_pct}%温度伤害", f"攻击间隔:0.5s", "按R切换形态"]
        elif tower.level >= 6:
            info = [f"冰球 Lv{tower.level}", f"减速:50%", f"伤害:{tower.damage}", f"冻结:{tower.freeze_time}s",
                    f"攻击间隔:0.5s"]
        else:
            info = [f"雪球 Lv{tower.level}", f"减速:50%", f"伤害:{tower.damage}", f"攻击间隔:{tower.fire_rate / 60}s"]
    elif tower.type == TowerType.TELEPORT:
        if tower.teleport_branch == 2:
            if tower.level >= 11:
                info = [f"无尽催化剂 Lv{tower.level}", f"随机伤害:0~{tower.damage * 2}",
                        f"八方向散射", f"必定施加随机永久debuff", f"攻击间隔:{tower.fire_rate / 60}s", "按R切换形态"]
            elif tower.level >= 6:
                poison_stacks = {6: 600, 7: 700, 8: 800, 9: 900, 10: 1000}
                info = [f"毒马铃薯 Lv{tower.level}", f"随机伤害:0~{tower.damage * 2}",
                        f"2%施加{poison_stacks.get(tower.level, 600)}层中毒", f"攻击间隔:{tower.fire_rate / 60}s", "按R切换形态"]
            else:
                info = [f"幸运四叶草 Lv{tower.level}", f"随机伤害:0~{tower.damage * 2}",
                        f"攻击间隔:{tower.fire_rate / 60}s", "按R切换形态"]
        else:
            if tower.level >= 11:
                info = [f"终望珍珠 Lv{tower.level}", f"秒杀概率:{int(tower.oneshot_chance * 100)}%",
                        f"瞬移概率:{int(tower.teleport_chance * 100)}%", f"百分比伤害:{(tower.level-10)*0.4}%",
                        f"范围伤害:{tower.damage}", f"攻击间隔:{tower.fire_rate / 60}s", "按R切换形态"]
            elif tower.level >= 6:
                info = [f"末影之眼 Lv{tower.level}", f"秒杀概率:{int(tower.oneshot_chance * 100)}%",
                        f"瞬移概率:{int(tower.teleport_chance * 100)}%", f"伤害:{tower.damage}", f"攻击间隔:{tower.fire_rate / 60}s", "按R切换形态"]
            else:
                info = [f"末影珍珠 Lv{tower.level}", f"瞬移概率:{int(tower.teleport_chance * 100)}%",
                        f"伤害:{tower.damage}", f"攻击间隔:{tower.fire_rate / 60}s", "按R切换形态"]
    elif tower.type == TowerType.FLAME:
        if tower.level >= 11:
            if tower.flame_branch == 2:
                fire_dmg = {11: 36, 12: 72, 13: 108, 14: 144, 15: 180}
                info = [f"唤龙火晶石 Lv{tower.level}", f"伤害:{tower.damage}", f"燃烧:{game.temperature}/s,持续4s",
                        f"5%召唤火龙:{fire_dmg.get(tower.level,36)}倍温度+燃烧", f"击晕:{tower.stun_time}s", f"攻击间隔:0.5s", "按R切换形态"]
            else:
                dmg_mult = (tower.level - 10) * 10
                info = [f"龙息 Lv{tower.level}", f"伤害:{tower.damage}", f"燃烧:{game.temperature}/s,持续4s",
                        f"龙息:{dmg_mult}倍温度/s", f"击晕:{tower.stun_time}s", f"攻击间隔:0.5s", "按R切换形态"]
        elif tower.level >= 6:
            info = [f"火球 Lv{tower.level}", f"伤害:{tower.damage}", f"燃烧:{game.temperature}/s,持续4s",
                    f"击晕:{tower.stun_time}s", f"攻击间隔:0.5s"]
        else:
            info = [f"火焰弹 Lv{tower.level}", f"伤害:{tower.damage}", f"燃烧:{game.temperature}/s,持续4s",
                    f"攻击间隔:{tower.fire_rate / 60}s"]
    elif tower.type == TowerType.TRIDENT:
        if tower.level >= 11:
            if tower.trident_branch == 2:
                info = [f"唤龙电晶石 Lv{tower.level}", f"伤害:{tower.damage}", f"闪电:{tower.lightning_damage}",
                        f"将当前金币的1%作为伤害加成", f"5%召唤电龙:{(tower.level-10)*50}倍温度+麻痹1s", f"攻击间隔:0.5s", "按 R 切换形态"]
            else:
                info = [f"海渊裂空之戟 Lv{tower.level}", f"伤害:{tower.damage}", f"闪电:{tower.lightning_damage}",
                        f"将当前金币的1%作为伤害加成", f"攻击施放十字闪电", f"攻击间隔:0.5s", "按 R 切换形态"]
        elif tower.level >= 6:
            info = [f"黄金三叉戟 Lv{tower.level}", f"伤害:{tower.damage}", f"闪电:{tower.lightning_damage}",
                    f"将当前金币的1%作为伤害加成", f"攻击间隔:0.5s"]
        else:
            info = [f"三叉戟 Lv{tower.level}", f"伤害:{tower.damage}", f"闪电:{tower.lightning_damage}",
                    f"攻击间隔:{tower.fire_rate / 60}s"]
    elif tower.type == TowerType.WIND:
        if tower.level >= 11:
            if tower.wind_branch == 2:
                dmg_map = {11: 2000, 12: 4000, 13: 6000, 14: 8000, 15: 10000}
                info = [f"雷神之锤 Lv{tower.level}", f"伤害:{tower.damage}",
                        f"子弹命中释放竖向闪电:{dmg_map.get(tower.level,2500)}", "按 R 切换分支", f"攻击间隔:0.5s"]
            else:
                per_px = {11: 8, 12: 10, 13: 12, 14: 14, 15: 16}
                stun_s = {11: 0.1, 12: 0.2, 13: 0.3, 14: 0.4, 15: 0.5}
                info = [f"山崩地裂之锤 Lv{tower.level}", f"伤害:{tower.damage}+{per_px.get(tower.level,8)}/px",
                        f"击退:{tower.wind_knockback}px", f"击晕:{stun_s.get(tower.level,0.1)}s", "按 R 切换分支", f"攻击间隔:0.5s"]
        elif tower.level >= 6:
            info = [f"重锤 Lv{tower.level}", f"伤害:{tower.damage}", f"击退:{tower.wind_knockback}px",
                    f"蓄风印记", f"攻击间隔:0.5s"]
        else:
            info = [f"风弹 Lv{tower.level}", f"伤害:{tower.damage}", f"击退:{tower.wind_knockback}px",
                    f"攻击间隔:{tower.fire_rate / 60}s"]
    elif tower.type == TowerType.POISON:
        if tower.poison_branch == 3:
            stacks = tower.level * 9
            info = [f"九头蛇毒箭 Lv{tower.level}", f"单体伤害:{tower.damage}",
                    f"中毒层数:{stacks}层/次", "按 R 切换分支", f"攻击间隔:0.5s"]
        elif tower.poison_branch == 2:
            if tower.level >= 11:
                info = [f"凋零之首 Lv{tower.level}", f"范围伤害:{tower.damage}",
                        f"凋零:12s", "按 R 切换分支", f"攻击间隔:0.5s"]
            elif tower.level >= 6:
                info = [f"凋零药水 Lv{tower.level}", f"范围伤害:{tower.damage}",
                        f"范围凋零:5s", "按 R 切换分支", f"攻击间隔:0.5s"]
            else:
                info = [f"凋零箭 Lv{tower.level}", f"伤害:{tower.damage}",
                        f"凋零:5s", "按 R 切换分支", f"攻击间隔:{tower.fire_rate / 60}s"]
        elif tower.level >= 11:
            stacks = tower.level * 4
            info = [f"剧毒环刃 Lv{tower.level}", f"范围伤害:{tower.damage}",
                    f"中毒层数:{stacks}层/次", "按 R 切换分支", f"攻击间隔:0.5s"]
        elif tower.level >= 6:
            info = [f"剧毒药水 Lv{tower.level}", f"范围伤害:{tower.damage}",
                    f"中毒层数:{tower.level}层/次", "按 R 切换分支", f"攻击间隔:0.5s"]
        else:
            info = [f"毒箭 Lv{tower.level}", f"伤害:{tower.damage}",
                    f"中毒层数:{tower.level}层/次", "按 R 切换分支", f"攻击间隔:{tower.fire_rate / 60}s"]
    elif tower.type == TowerType.TIME:
        if tower.level >= 11:
            info = [f"时间洪流怀表 Lv{tower.level}", f"攻速加成:{tower.level}%", f"范围:7x7"]
        elif tower.level >= 6:
            info = [f"加速火把 Lv{tower.level}", f"攻速加成:{tower.level}%", f"范围:5x5"]
        else:
            info = [f"时钟 Lv{tower.level}", f"攻速加成:{tower.level}%", f"范围:3x3"]
    elif tower.type == TowerType.SHIELD:
        if tower.level >= 11:
            if tower.shield_branch == 1:
                dmg_mult = (tower.level - 10) * 36
                info = [f"火焰盾 Lv{tower.level}",
                        f"护盾破碎:全屏{dmg_mult}倍温度伤害", "使所有敌人永久燃烧", "按 R 切换分支"]
            elif tower.shield_branch == 2:
                dmg_mult = (tower.level - 10) * 30
                info = [f"寒冰盾 Lv{tower.level}",
                        f"护盾破碎:全屏{dmg_mult}倍温度伤害", "使所有敌人冰冻3秒", "按 R 切换分支"]
            elif tower.shield_branch == 3:
                gold_amt = (tower.level - 10) * 1000
                info = [f"贪婪盾 Lv{tower.level}",
                        f"护盾破碎:造成金币1%伤害", f"获得{gold_amt}金币", "按 R 切换分支"]
            elif tower.shield_branch == 4:
                dmg_mult = (tower.level - 10) * 25
                info = [f"雷盾 Lv{tower.level}",
                        f"护盾破碎:全屏{dmg_mult}倍温度伤害", "击晕全场1秒并永久燃烧", "按 R 切换分支"]
        elif tower.level >= 6:
            info = [f"铁壁盾 Lv{tower.level}", "每60秒给5*5范围内随机3个塔施加护盾"]
        else:
            info = [f"老木盾 Lv{tower.level}", "每90秒给3*3范围内随机1个塔施加护盾"]
    elif tower.type == TowerType.BOMB:
        if tower.level >= 11:
            if tower.bomb_branch == 2:
                info = [f"凋零核弹 Lv{tower.level}",
                        f"伤害:{(tower.level - 10)*2}%最大生命+{(tower.level - 10)*2000}固定",
                        f"击晕:2s", f"凋零:10s",
                        f"射程:全屏", f"攻击间隔:20s", "按 R 切换形态"]
            else:
                dmg = (20000 + 100 * game.temperature) * (tower.level - 10)
                info = [f"核弹 Lv{tower.level}", f"伤害:{dmg}(受温度影响)",
                        f"击晕:2s", f"中毒:{tower.level * 10}层",
                        f"射程:全屏", f"攻击间隔:20s", "按 R 切换形态"]
        elif tower.level >= 6:
            sub_names = {BombSubType.SNOW: "雪TNT", BombSubType.ICE: "冰TNT",
                         BombSubType.FLAME: "火焰TNT", BombSubType.POISON: "毒TNT",
                         BombSubType.WITHER_TNT: "凋零TNT"}
            sub_name = sub_names.get(tower.bomb_subtype, "雪TNT")
            if tower.bomb_subtype == BombSubType.SNOW:
                extra = "范围减速50%,持续12s"
            elif tower.bomb_subtype == BombSubType.ICE:
                extra = f"范围冰冻{tower.level * 0.1}s"
            elif tower.bomb_subtype == BombSubType.FLAME:
                extra = "范围燃烧8s"
            elif tower.bomb_subtype == BombSubType.POISON:
                extra = f"范围中毒{tower.level * 2}层"
            elif tower.bomb_subtype == BombSubType.WITHER_TNT:
                extra = "范围凋零5s"
            info = [f"{sub_name} Lv{tower.level}", f"伤害:{tower.damage}",
                    extra, "按 R 切换分支", "攻击间隔:2s"]
        else:
            info = [f"TNT Lv{tower.level}", f"伤害:{tower.damage}", f"攻击间隔:2s"]
    upgrade_str = "MAX" if tower.level >= 15 else str(tower.upgrade_cost)
    if tower.type == TowerType.BOMB and tower.is_nuclear:
        info.extend([f"升级:{upgrade_str}"])
    elif tower.type == TowerType.SHIELD:
        info.extend([f"升级:{upgrade_str}"])
    else:
        info.extend([f"射程:{round(tower.get_effective_range() / TILE_SIZE, 1)}", f"升级:{upgrade_str}"])
    sell_price = base_cost_map[tower.type] * tower.level
    info.append(f"出售:{sell_price}")

    return info


class UIManager:
    def __init__(self, game):
        self.game = game

    def draw_menu(self):
        title = assets.font_large.render("像素防线:晶域守卫", True, WHITE)
        self.game.screen.blit(title, (SCREEN_WIDTH // 2 - title.get_width() // 2, 300))
        pygame.draw.rect(self.game.screen, GREEN, (900, 840, 760, 80))
        start_text = assets.font_medium.render("开始游戏", True, WHITE)
        self.game.screen.blit(start_text, (1200, 855))
        pygame.draw.rect(self.game.screen, RED, (900, 1020, 760, 80))
        exit_text = assets.font_medium.render("退出游戏", True, WHITE)
        self.game.screen.blit(exit_text, (1200, 1035))

    def draw_game(self):
        self.game.screen.blit(self.game.background_surface, (0, 0))

        self.game.towers.draw(self.game.screen)
        for wall in self.game.ice_walls:
            wall.draw(self.game.screen)
        for cb in self.game.command_blocks:
            alpha = 255 if (cb['timer'] // 30) % 2 == 0 else 128
            img = assets.command_block_img.copy()
            img.set_alpha(alpha)
            self.game.screen.blit(img, (cb['x'] * TILE_SIZE, cb['y'] * TILE_SIZE))
        self.game.enemies.draw(self.game.screen)
        self.game.bullets.draw(self.game.screen)
        for dragon in self.game.dragons:
            dragon.draw(self.game.screen)
        for tower in self.game.towers:
            self.game.screen.blit(assets.font_tower_level.render(str(tower.level), True, YELLOW),
                                 (tower.x * TILE_SIZE + 85, tower.y * TILE_SIZE + 90))
            if getattr(tower, 'has_shield', False):
                self.game.screen.blit(assets.shield_img,
                                     (tower.x * TILE_SIZE, tower.y * TILE_SIZE))
        for enemy in self.game.enemies:
            enemy.draw_health_bar(self.game.screen)

        if self.game.show_range and self.game.selected_tower:
            self.game.selected_tower.draw_range(self.game.screen)

        self.draw_weather_particles()
        self.draw_weather_banner()

        if self.game.fog_visible:
            gw = GRID_WIDTH * TILE_SIZE
            gh = GRID_HEIGHT * TILE_SIZE
            s = pygame.Surface((gw, gh), pygame.SRCALPHA)
            if self.game.weather == Weather.ENDLESS_NIGHT:
                s.fill((0, 0, 0, 255))
            else:
                s.fill((255, 255, 255, 255))
            self.game.screen.blit(s, (0, TILE_SIZE))

        for pool in self.game.dragon_breath_pools:
            pool.draw(self.game.screen)
        for effect in self.game.lightning_effects:
            effect.draw(self.game.screen)
        for explosion in self.game.wind_explosions:
            explosion.draw(self.game.screen)
        for exp in self.game.ice_explosions:
            exp.draw(self.game.screen)
        for splash in self.game.poison_splashes:
            splash.draw(self.game.screen)
        for splash in self.game.wither_splashes:
            splash.draw(self.game.screen)
        for effect in self.game.horizontal_lightning_effects:
            effect.draw(self.game.screen)
        for explosion in self.game.tnt_explosions:
            explosion.draw(self.game.screen)
        for explosion in self.game.creeper_explosions:
            explosion.draw(self.game.screen)
        for sw in self.game.shockwave_effects:
            sw.draw(self.game.screen)
        for explosion in self.game.mushroom_explosions:
            explosion.draw(self.game.screen)
        self.game.damage_texts.draw(self.game.screen)

        self.draw_ui()
        self.draw_herobrine_health_bar()
        if self.game.state == GameState.PAUSED:
            self.draw_pause_overlay()

    def draw_ui(self):
        pygame.draw.rect(self.game.screen, BLACK, (0, 0, SCREEN_WIDTH, 80))
        pygame.draw.line(self.game.screen, WHITE, (0, 80), (SCREEN_WIDTH, 80), 4)
        self.game.screen.blit(assets.gold_img, (0, 8))
        self.game.screen.blit(assets.font_medium.render(str(int(self.game.coins)), True, GOLD), (70, 16))
        self.game.screen.blit(assets.heart_img, (320, -25))
        self.game.screen.blit(assets.font_medium.render(str(self.game.lives), True, RED), (420, 16))
        self.game.screen.blit(
            assets.font_medium.render(f"波数:{self.game.wave_manager.current_wave}/{self.game.wave_manager.total_waves}", True, WHITE),
            (520, 16))
        weather_name = WEATHER_CONFIG[self.game.weather]["name"]
        weather_color = WEATHER_CONFIG[self.game.weather]["color"]
        self.game.screen.blit(assets.font_medium.render(f"天气:{weather_name}  温度:{self.game.temperature}", True, weather_color), (1570, 16))

        if self.game.wave_manager.current_wave < 47:
            can_buy = self.game.state == GameState.PLAYING and not self.game.forecast_purchased
            can_afford = self.game.coins >= 100 * self.game.wave_manager.current_wave
            btn_color = FORECAST_BTN_COLOR if can_buy and can_afford else FORECAST_BTN_COLOR_DISABLED
            pygame.draw.rect(self.game.screen, btn_color,
                             (FORECAST_BTN_X, FORECAST_BTN_Y, FORECAST_BTN_WIDTH, FORECAST_BTN_HEIGHT))
            if self.game.forecast_purchased and 0 <= self.game.forecast_weather_idx < len(self.game.weather_forecast):
                forecast_names = []
                for i in range(3):
                    idx = self.game.forecast_weather_idx + i
                    if idx < len(self.game.weather_forecast):
                        forecast_names.append(WEATHER_CONFIG[self.game.weather_forecast[idx]]['name'])
                label = f"天气预报:{','.join(forecast_names)}"
            else:
                label = f"天气预报:花费{100*self.game.wave_manager.current_wave}金"
            fc_color = WHITE if can_afford else GRAY
            fc_text = assets.font_small.render(label, True, fc_color)
            self.game.screen.blit(fc_text, (FORECAST_BTN_X + 20, FORECAST_BTN_Y + 10))

        pygame.draw.rect(self.game.screen, BLACK, (0, SCREEN_HEIGHT - 128, SCREEN_WIDTH, 128))
        pygame.draw.line(self.game.screen, WHITE, (0, SCREEN_HEIGHT - 128), (SCREEN_WIDTH, SCREEN_HEIGHT - 128), 4)

        icon_size = 100
        gap = 64
        step = icon_size + gap
        total_w = len(self.game.TOWER_DATA) * step - gap
        bar_left = 60
        bar_right = INFO_BORDER_X - 40
        start_x = bar_left + (bar_right - bar_left - total_w) // 2
        positions = {}
        for i, (ttype, name, cost, key) in enumerate(self.game.TOWER_DATA):
            ix = start_x + i * step
            iy = SCREEN_HEIGHT - 114
            keys = (1, 2, 3, 4, 5, 6, 7, 8, 9, 0, 'X')
            self.game.screen.blit(assets.tower_icons[ttype.value], (ix, iy))
            num_surf = assets.font_tower_level.render(str(keys[i]), True, YELLOW)
            self.game.screen.blit(num_surf, (ix + 2, iy + 2))
            price_surf = assets.font_tower_level.render(str(cost), True, GOLD)
            self.game.screen.blit(price_surf, (ix + icon_size - price_surf.get_width() - 2,
                                              iy + icon_size - price_surf.get_height() - 2))
            positions[ttype] = (ix, iy)
        if self.game.selected_tower_type in positions:
            x, y = positions[self.game.selected_tower_type]
            hl = 110
            pygame.draw.rect(self.game.screen, WHITE, (x - (hl - icon_size) // 2, y - (hl - icon_size) // 2, hl, hl), 4)

        pygame.draw.rect(self.game.screen, INFO_BORDER_COLOR,
                         (INFO_BORDER_X, INFO_BORDER_Y, INFO_BORDER_SIZE, INFO_BORDER_SIZE), INFO_BORDER_WIDTH)
        if self.game.selected_tower:
            infos = get_tower_info(self.game, self.game.selected_tower)
            for i, info in enumerate(infos):
                self.game.screen.blit(assets.font_small.render(info, True, WHITE),
                                     (INFO_BORDER_X + 20, INFO_BORDER_Y + 20 + i * 32))
        pygame.draw.rect(self.game.screen, RESTART_BTN_COLOR,
                         (RESTART_BTN_X, RESTART_BTN_Y, RESTART_BTN_WIDTH, RESTART_BTN_HEIGHT))
        restart_text = assets.font_small.render("重新开始", True, WHITE)
        self.game.screen.blit(restart_text, (RESTART_BTN_X + 40, RESTART_BTN_Y + 10))

        pygame.draw.rect(self.game.screen, EXIT_BTN_COLOR,
                         (EXIT_BTN_X, EXIT_BTN_Y, EXIT_BTN_WIDTH, EXIT_BTN_HEIGHT))
        exit_text = assets.font_small.render("退出游戏", True, WHITE)
        self.game.screen.blit(exit_text, (EXIT_BTN_X + EXIT_BTN_WIDTH // 2 - exit_text.get_width() // 2, EXIT_BTN_Y + 10))

        instructions = ["操作说明:", "0~9,X选择炮塔", "U升级 S出售", "R切换分支 E升5级", "ESC暂停"]
        for i, text in enumerate(instructions):
            self.game.screen.blit(assets.font_small.render(text, True, WHITE), (2156, 1144 + i * 48))

    def draw_weather_particles(self):
        for p in self.game.weather_particles:
            if p[-1] == "rain":
                x, y, _, length = p[0], p[1], p[2], p[3]
                s = assets.rain_cache.get(length)
                if s is None:
                    s = pygame.Surface((2, length), pygame.SRCALPHA)
                    s.fill((100, 150, 255, 180))
                    assets.rain_cache[length] = s
                self.game.screen.blit(s, (int(x), int(y)))
            elif p[-1] == "acid_rain":
                x, y, _, length = p[0], p[1], p[2], p[3]
                s = assets.acid_rain_cache.get(length)
                if s is None:
                    s = pygame.Surface((2, length), pygame.SRCALPHA)
                    s.fill((0, 200, 0, 180))
                    assets.acid_rain_cache[length] = s
                self.game.screen.blit(s, (int(x), int(y)))
            elif p[-1] == "snow":
                x, y, _, _, size = p[0], p[1], p[2], p[3], p[4]
                s = assets.snow_cache.get(size)
                if s is None:
                    s = pygame.Surface((size * 2, size * 2), pygame.SRCALPHA)
                    pygame.draw.circle(s, (255, 255, 255, 200), (size, size), size)
                    assets.snow_cache[size] = s
                self.game.screen.blit(s, (int(x) - size, int(y) - size))
            elif p[-1] == "fire":
                x, y, _, _, size, phase = p[0], p[1], p[2], p[3], p[4], p[5]
                flicker = int(30 * (0.5 + 0.5 * math.sin(phase)))
                r = min(255, 200 + flicker)
                g = max(0, min(200, 150 - flicker))
                alpha = min(200, 120 + flicker)
                color_key = (r, g, 0)
                s = assets.fire_cache.get((size, color_key))
                if s is None:
                    s = pygame.Surface((size * 2, size * 2), pygame.SRCALPHA)
                    pygame.draw.circle(s, (*color_key, alpha), (size, size), size)
                    pygame.draw.circle(s, (255, 255, 100, alpha // 2), (size, size), size // 2)
                    assets.fire_cache[(size, color_key)] = s
                self.game.screen.blit(s, (int(x) - size, int(y) - size))

    def draw_weather_banner(self):
        if self.game.weather_banner_timer <= 0:
            return
        alpha = min(255, self.game.weather_banner_timer * 2)
        banner_w = 1200
        banner_h = 60
        banner_x = SCREEN_WIDTH // 2 - banner_w // 2
        banner_y = 200
        s = pygame.Surface((banner_w, banner_h), pygame.SRCALPHA)
        s.fill((0, 0, 0, min(180, alpha)))
        self.game.screen.blit(s, (banner_x, banner_y))
        text = assets.font_medium.render(self.game.weather_banner_text, True, WHITE)
        text.set_alpha(alpha)
        self.game.screen.blit(text, (SCREEN_WIDTH // 2 - text.get_width() // 2, banner_y + 10))

    def draw_pause_overlay(self):
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 128))
        self.game.screen.blit(overlay, (0, 0))
        pause_text = assets.font_large.render("已暂停", True, WHITE)
        continue_text = assets.font_small.render("按 ESC 继续", True, WHITE)
        self.game.screen.blit(pause_text, (SCREEN_WIDTH // 2 - pause_text.get_width() // 2, SCREEN_HEIGHT // 2 - 60))
        self.game.screen.blit(continue_text, (SCREEN_WIDTH // 2 - continue_text.get_width() // 2, SCREEN_HEIGHT // 2 + 20))

    def draw_game_over(self):
        self.game.screen.fill(BLACK)
        text1 = assets.font_large.render("游戏结束!", True, RED)
        self.game.screen.blit(text1, (SCREEN_WIDTH // 2 - text1.get_width() // 2, 400))
        pygame.draw.rect(self.game.screen, GREEN, (900, 850, 760, 80))
        restart_text = assets.font_medium.render("重新开始", True, WHITE)
        self.game.screen.blit(restart_text, (SCREEN_WIDTH // 2 - restart_text.get_width() // 2, 855))

    def draw_herobrine_health_bar(self):
        for enemy in self.game.enemies:
            if enemy.enemy_type == EnemyType.HEROBRINE:
                bar_x = 810
                bar_y = 20
                bar_width = 740
                bar_height = 50
                pygame.draw.rect(self.game.screen, (100, 0, 0), (bar_x, bar_y, bar_width, bar_height))
                health_ratio = enemy.health / enemy.max_health
                fill_width = int(bar_width * health_ratio)
                pygame.draw.rect(self.game.screen, (0, 255, 0), (bar_x, bar_y, fill_width, bar_height))
                layers_text = assets.font_medium.render(f"*{enemy.current_layer}", True, WHITE)
                text_x = bar_x + bar_width - layers_text.get_width() - 5
                text_y = bar_y + (bar_height - layers_text.get_height()) // 2
                self.game.screen.blit(layers_text, (text_x, text_y))
                break

    def draw_victory(self):
        self.game.screen.fill(BLACK)
        text1 = assets.font_large.render("胜利!", True, GREEN)
        self.game.screen.blit(text1, (SCREEN_WIDTH // 2 - text1.get_width() // 2, 400))
        pygame.draw.rect(self.game.screen, GREEN, (900, 850, 760, 80))
        restart_text = assets.font_medium.render("重新开始", True, WHITE)
        self.game.screen.blit(restart_text, (SCREEN_WIDTH // 2 - restart_text.get_width() // 2, 855))