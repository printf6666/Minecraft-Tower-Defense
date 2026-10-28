import pygame
import math
import assets
import stats
from config import *
from tower import TowerType
from enemy import EnemyType
from effects import WindExplosion, IceExplosion, DragonBreathPool, LightningEffect, HorizontalLightningEffect, PoisonSplash, TNTExplosion, MushroomExplosion, NuclearShockwave, WitherSplash


# ==========================================================================================
#  商店卡片布局
#  卡片高度必须按「最长的一条附魔描述」来算，否则像「余烬重生」这种 9 行的会被切掉。
#  行数只在第一次用到时算一次并缓存（字体在 assets.init_assets() 之后才存在）。
# ==========================================================================================
SHOP_SLOT_W = 340
SHOP_SLOT_GAP = 24
SHOP_DESC_TOP = 250          # 描述文字相对卡片顶部的 y
SHOP_LINE_H = 34             # 描述行距
SHOP_DESC_PAD = 24           # 最后一行到卡片底边的留白
SHOP_PANEL_W = 1200

_shop_desc_lines = None


def shop_desc_line_count():
    global _shop_desc_lines
    if _shop_desc_lines is None:
        font = assets.font_tower_level
        if font is None:
            return 6                      # 字体还没加载，给个安全值
        max_w = SHOP_SLOT_W - 40
        longest = 1
        for ench in ENCHANTMENT_ORDER:
            text = ENCHANTMENT_DATA[ench]["desc"]
            n = 1
            line = ""
            for ch in text:
                if font.render(line + ch, True, (0, 0, 0)).get_width() > max_w:
                    n += 1
                    line = ch
                else:
                    line += ch
            longest = max(longest, n)
        _shop_desc_lines = longest
    return _shop_desc_lines


def shop_slot_height():
    return SHOP_DESC_TOP + shop_desc_line_count() * SHOP_LINE_H + SHOP_DESC_PAD


def burn_preview(game):
    """面板里的「燃烧 X/s」预览。

    温度 <= 0 时火系根本点不着（apply_burn 直接 return），
    直接拿温度去算会显示成负数，看着像在倒扣血，所以这里按 0 显示。
    """
    if game.temperature <= 0:
        return 0
    return game.burn_tick_damage(game.temperature)


def get_tower_info(game, tower):
    base_cost_map = {ttype: cost for ttype, name, cost, key in TOWER_DATA}
    info = []
    if tower.type == TowerType.PHYSICAL:
        if tower.level >= 11:
            if tower.physical_branch == 2:
                info = [f"天堂陨落长弓 Lv{tower.level}", f"伤害:{tower.damage}", f"攻击间隔:0.5s", f"金币1%作为伤害加成", f"12方向散射", "按 R 切换分支"]
            elif tower.physical_branch == 3:
                info = [f"地狱升华之弩 Lv{tower.level}", "发射黑色射线", "随机秒杀一个敌人",
                        "对BOSS造成5%最大生命伤害", f"攻击间隔:{(19 - tower.level)}s", "按 R 切换分支"]
            else:
                info = [f"时空撕裂之矢 Lv{tower.level}", f"伤害:{tower.damage}", f"攻击间隔:0.5s",
                        f"金币1%作为伤害加成", f"破甲:受伤永久增加20%", "按 R 切换分支"]
        elif tower.level >= 6:
            info = [f"黄金箭塔 Lv{tower.level}", f"伤害:{tower.damage}", f"攻击间隔:0.5s", f"金币1%作为伤害加成"]
        else:
            info = [f"箭塔 Lv{tower.level}", f"伤害:{tower.damage}", f"攻击间隔:{tower.fire_rate / 60}s"]
    elif tower.type == TowerType.PRODUCTION:
        if tower.level >= 11:
            info = [f"绿宝石块 Lv{tower.level}", f"全局产量:{game.gold_per_second}/s",
                    f"全局每波产出:{5 * game.gold_per_wave}*当前波数", f"每波获得{game.emerald_per_wave}颗绿宝石"]
        elif tower.level >= 6:
            info = [f"下界合金矿 Lv{tower.level}", f"全局每波产出:{5 * game.gold_per_wave}*当前波数",
                    f"全局产量:{game.gold_per_second}/s", "放置在金矿石上时产出+100%"]
        else:
            info = [f"金矿 Lv{tower.level}", f"全局产量:{game.gold_per_second}/s", "放置在金矿石上时产出+100%"]
    elif tower.type == TowerType.ICE:
        if tower.level >= 11:
            if tower.ice_branch == HOLY_POT_BRANCH:
                base = HOLY_POT_DAMAGE_BASE.get(tower.level, 500)
                per = HOLY_POT_DAMAGE_TEMP.get(tower.level, 10)
                info = [f"神锅 Lv{tower.level}",
                        f"伤害:{tower.holy_pot_damage()}",
                        f"公式:{base}+{per}*温度",
                        f"攻击间隔:{HOLY_POT_FIRE_RATE / 60}s 射程:全屏",
                        "随机1名敌人 单体伤害",
                        "命中永久冰系破甲+100%",
                        "按R切换形态"]
                if Enchantment.MASTERPIECE in game.enchantments:
                    info.append(f"大招:{game.masterpiece_counter}/{MASTERPIECE_ATTACKS}")
            elif tower.ice_branch == 2:
                ice_dmg = {11: 30, 12: 60, 13: 90, 14: 120, 15: 150}
                info = [f"唤龙冰晶石 Lv{tower.level}", f"减速:50%", f"伤害:{tower.damage}", f"冻结:{tower.freeze_time}s",
                        f"5%召唤冰龙:{ice_dmg.get(tower.level,30)}倍|温度|",
                        "附加1%最大生命真实伤害", f"攻击间隔:0.5s", "按R切换形态"]
            elif tower.ice_branch == 3:
                wall_duration = {11: 2, 12: 2.5, 13: 3, 14: 3.5, 15: 4}
                info = [f"冰墙 Lv{tower.level}", f"伤害:{tower.damage}", f"冻结:{tower.freeze_time}s",
                        f"子弹经过的道路4%生成冰墙",
                        f"冰墙持续:{wall_duration.get(tower.level, 2)}s",
                        f"每道冰墙降低{ICE_WALL_TEMP_DROP}度温度", "阻挡地面怪物", "按R切换形态"]
            else:
                bomb_k = ICE_BOMB_TEMP_MULT.get(tower.level, 15)
                bomb_dmg = tower.damage + bomb_k * abs(game.temperature)
                info = [f"冰霜炸弹 Lv{tower.level}", f"减速:50%", f"伤害:{tower.damage}", f"冻结:{tower.freeze_time}s",
                        f"AOE:{bomb_dmg} {tower.damage}+{bomb_k}*|温度|",
                        f"攻击间隔:0.5s", "按R切换形态"]
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
            if tower.flame_branch == 3:
                info = [f"星焰提灯 Lv{tower.level}", f"伤害:{tower.lantern_damage()}",
                        f"燃烧:{burn_preview(game)}/s,持续4s",
                        f"范围:{LANTERN_RANGE_TILES.get(tower.level, 3.5)}格",
                        "冲击波:范围内全体敌人",
                        f"攻击间隔:{LANTERN_FIRE_RATE / 60}s 迷雾照明",
                        "按 R 切换形态"]
            elif tower.flame_branch == 2:
                fire_dmg = {11: 36, 12: 72, 13: 108, 14: 144, 15: 180}
                info = [f"唤龙火晶石 Lv{tower.level}", f"伤害:{tower.damage}", f"燃烧:{burn_preview(game)}/s,持续4s",
                        f"5%召唤火龙:{fire_dmg.get(tower.level,36)}倍|温度|",
                        "附加2%最大生命真实伤害", f"击晕:{tower.stun_time}s", f"攻击间隔:0.5s", "按R切换形态"]
            else:
                dmg_mult = (tower.level - 10) * 10
                info = [f"龙息 Lv{tower.level}", f"伤害:{tower.damage}", f"燃烧:{burn_preview(game)}/s,持续4s",
                        f"龙息:{dmg_mult}倍|温度|/s", f"击晕:{tower.stun_time}s", f"攻击间隔:0.5s", "按R切换形态"]
                if Enchantment.EMBER_REBIRTH in game.enchantments and tower.level == 15:
                    cost = 50000 * (2 ** game.sacrifices)
                    info.append(f"Q 献祭:{cost}金币")
        elif tower.level >= 6:
            info = [f"火球 Lv{tower.level}", f"伤害:{tower.damage}", f"燃烧:{burn_preview(game)}/s,持续4s",
                    f"击晕:{tower.stun_time}s", f"攻击间隔:0.5s"]
        else:
            info = [f"火焰弹 Lv{tower.level}", f"伤害:{tower.damage}", f"燃烧:{burn_preview(game)}/s,持续4s",
                    f"攻击间隔:{tower.fire_rate / 60}s"]
    elif tower.type == TowerType.TRIDENT:
        if tower.level >= 11:
            if tower.trident_branch == 2:
                info = [f"唤龙电晶石 Lv{tower.level}", f"伤害:{tower.damage}", f"闪电:{tower.lightning_damage}",
                        f"金币1%作为伤害加成", f"5%召唤电龙:{(tower.level-10)*50}倍|温度|",
                        "附加3%最大生命真实伤害", f"攻击间隔:0.5s", "按 R 切换形态"]
            else:
                info = [f"海渊裂空之戟 Lv{tower.level}", f"伤害:{tower.damage}", f"闪电:{tower.lightning_damage}",
                        f"金币1%作为伤害加成", f"攻击施放十字闪电", f"攻击间隔:0.5s", "按 R 切换形态"]
        elif tower.level >= 6:
            info = [f"黄金三叉戟 Lv{tower.level}", f"伤害:{tower.damage}", f"闪电:{tower.lightning_damage}",
                    f"金币1%作为伤害加成", f"攻击间隔:0.5s"]
        else:
            info = [f"三叉戟 Lv{tower.level}", f"伤害:{tower.damage}", f"闪电:{tower.lightning_damage}",
                    f"攻击间隔:{tower.fire_rate / 60}s"]
    elif tower.type == TowerType.WIND:
        if tower.level >= 11:
            if tower.wind_branch == 2:
                info = [f"雷神之锤 Lv{tower.level}", f"伤害:{tower.damage}",
                        f"命中落雷:{WIND_STORM_DAMAGE.get(tower.level, 2500)}",
                        f"AOE半径:{WIND_STORM_RADIUS}px",
                        f"落雷特效每{WIND_STORM_VISUAL_EVERY}次命中播1次",
                        "按 R 切换分支", f"攻击间隔:0.5s"]
            else:
                per_px = {11: 8, 12: 10, 13: 12, 14: 14, 15: 16}
                info = [f"山崩地裂之锤 Lv{tower.level}", f"伤害:{tower.damage}+{per_px.get(tower.level,8)}/px",
                        f"击退:{tower.wind_knockback}px", "最大距离命中:额外25%当前生命伤害",
                        "按 R 切换分支", f"攻击间隔:0.5s"]
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
                gold_amt = (tower.level - 10) * 1000
                info = [f"贪婪盾 Lv{tower.level}",
                        f"护盾破碎:造成金币1%伤害", f"获得{gold_amt}金币", "按 R 切换分支"]
            elif tower.shield_branch == 2:
                dmg_mult = (tower.level - 10) * 3000
                info = [f"寒冰盾 Lv{tower.level}",
                        f"护盾破碎:全屏{dmg_mult}点伤害", "使所有敌人冰冻3秒", "按 R 切换分支"]
            elif tower.shield_branch == 3:
                dmg_mult = (tower.level - 10) * 2500
                info = [f"雷盾 Lv{tower.level}",
                        f"护盾破碎:全屏{dmg_mult}点伤害", "击晕全场1秒并永久燃烧", "按 R 切换分支"]
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
                        f"射程:全屏", f"攻击间隔:35s", "按 R 切换形态"]
            else:
                # 与实际结算保持一致：伤害吃 |温度|，高温低温都增伤
                dmg = max(1, (40000 + 400 * abs(game.temperature)) * (tower.level - 10))
                info = [f"核弹 Lv{tower.level}", f"伤害:{dmg}(|温度|)",
                        f"击晕:2s", f"中毒:{tower.level * 10}层",
                        f"射程:全屏", f"攻击间隔:35s", "按 R 切换形态"]
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
    elif getattr(tower, "is_holy_pot", None) and tower.is_holy_pot():
        # 射程是全屏，信息里已经写了，不用再显示「射程:18.9」这种没意义的数字
        info.extend([f"升级:{upgrade_str}"])
    else:
        info.extend([f"射程:{round(tower.get_effective_range() / TILE_SIZE, 1)}", f"升级:{upgrade_str}"])
    sell_price = base_cost_map[tower.type] * tower.level
    info.append(f"出售:{sell_price}")

    return info


class UIManager:
    def __init__(self, game):
        self.game = game
        self._lantern_light_cache = {}

    def draw_menu(self):
        pygame.mouse.set_visible(True)
        title = assets.font_large.render("像素防线:晶域守卫", True, WHITE)
        self.game.screen.blit(title, (SCREEN_WIDTH // 2 - title.get_width() // 2, 300))
        pygame.draw.rect(self.game.screen, GREEN, (900, 840, 760, 80))
        start_text = assets.font_medium.render("开始游戏", True, WHITE)
        self.game.screen.blit(start_text, (1200, 855))
        pygame.draw.rect(self.game.screen, CODEX_BTN_COLOR,
                         (CODEX_BTN_X, CODEX_BTN_Y, CODEX_BTN_WIDTH, CODEX_BTN_HEIGHT))
        codex_text = assets.font_medium.render("查看图鉴", True, WHITE)
        self.game.screen.blit(codex_text, (1200, CODEX_BTN_Y + 15))
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
        # 不稳定水晶压在子弹下层，避免挡住弹道
        for crystal in self.game.crystals:
            crystal.draw(self.game.screen)
        self.game.bullets.draw(self.game.screen)
        for dragon in self.game.dragons:
            dragon.draw(self.game.screen)
        self.draw_boss_effects()
        for tower in self.game.towers:
            self.game.screen.blit(assets.font_tower_level.render(str(tower.level), True, YELLOW),
                                 (tower.x * TILE_SIZE + 85, tower.y * TILE_SIZE + 90))
            if getattr(tower, 'has_shield', False):
                self.game.screen.blit(assets.shield_img,
                                     (tower.x * TILE_SIZE, tower.y * TILE_SIZE))
            elif tower.in_pulse():
                img = assets.shield_img
                scale = 1.0 + 0.1 * math.cos(2 * math.pi * tower.shield_pulse_timer / 30)
                w, h = img.get_size()
                scaled = pygame.transform.smoothscale(img, (max(1, int(w * scale)), max(1, int(h * scale))))
                alpha = int(255 * (0.6 + 0.4 * tower.shield_pulse_timer / 480))
                scaled.set_alpha(alpha)
                self.game.screen.blit(scaled, scaled.get_rect(
                    center=(tower.x * TILE_SIZE + TILE_SIZE // 2, tower.y * TILE_SIZE + TILE_SIZE // 2)))
            if tower.disabled_timer > 0:
                self.game.screen.blit(self.get_disabled_overlay(),
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
            self.cut_lantern_lights(s)
            self.game.screen.blit(s, (0, TILE_SIZE))

        for pool in self.game.dragon_breath_pools:
            pool.draw(self.game.screen)
        for effect in self.game.lightning_effects:
            effect.draw(self.game.screen)
        for explosion in self.game.wind_explosions:
            explosion.draw(self.game.screen)
        for explosion in self.game.endless_greed_explosions:
            explosion.draw(self.game.screen)
        for exp in self.game.ice_explosions:
            exp.draw(self.game.screen)
        for burst in self.game.ice_star_bursts:
            burst.draw(self.game.screen)
        for wave_fx in self.game.lantern_shockwaves:
            wave_fx.draw(self.game.screen)
        for ray in self.game.hell_rays:
            ray.draw(self.game.screen)
        for storm in self.game.resonance_storms:
            storm.draw(self.game.screen)
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
        for meteor in self.game.meteors:
            meteor.draw(self.game.screen)
        for explosion in self.game.mushroom_explosions:
            explosion.draw(self.game.screen)
        for bee in self.game.bees:
            bee.draw(self.game.screen)
        # 「臻品呈现」大招冲击波：压在其它特效之上、伤害飘字之下，
        # 这样炸开的一瞬间数字是浮在光波上面的
        for wave_fx in self.game.masterpiece_shockwaves:
            wave_fx.draw(self.game.screen)
        self.game.damage_texts.draw(self.game.screen)

        self.draw_boss_screen_fx()
        self.draw_ui()
        self.draw_boss_hud()
        self.draw_herobrine_health_bar()

        # 「臻品呈现」大招动画：盖住整个界面（含塔信息、金币条），
        # 但暂停遮罩要压在它上面，否则暂停时看到的是被冻住的一帧视频。
        video_active = self.game.ultimate_video is not None
        if video_active:
            self.game.ultimate_video.draw(self.game.screen)

        if self.game.state == GameState.PAUSED:
            self.draw_pause_overlay()

        gauntlet_cursor = (
            Enchantment.INFINITY_GAUNTLET in self.game.enchantments
            and self.game.state in (GameState.PLAYING, GameState.WAVE_PREPARATION, GameState.PAUSED)
        )
        pygame.mouse.set_visible(not (gauntlet_cursor or video_active))
        if gauntlet_cursor:
            icon = assets.enchantment_icons_raw.get(Enchantment.INFINITY_GAUNTLET)
            if icon:
                mx, my = pygame.mouse.get_pos()
                self.game.screen.blit(icon, (mx - icon.get_width() // 2, my - icon.get_height() // 2))

    def draw_ui(self):
        pygame.draw.rect(self.game.screen, BLACK, (0, 0, SCREEN_WIDTH, 80))
        pygame.draw.line(self.game.screen, WHITE, (0, 80), (SCREEN_WIDTH, 80), 4)
        self.game.screen.blit(assets.gold_img, (0, 8))
        self.game.screen.blit(assets.font_medium.render(str(int(self.game.coins)), True, GOLD), (70, 16))
        self.game.screen.blit(assets.emerald_img, (345, 0))
        self.game.screen.blit(assets.font_medium.render(str(self.game.emeralds), True, GREEN), (420, 16))
        self.game.screen.blit(
            assets.font_medium.render(f"波数:{self.game.wave_manager.current_wave}", True, WHITE),
            (560, 16))
        weather_name = WEATHER_CONFIG[self.game.weather]["name"]
        weather_color = WEATHER_CONFIG[self.game.weather]["color"]
        self.game.screen.blit(assets.font_medium.render(f"天气:{weather_name}  温度:{self.game.temperature}", True, weather_color), (1570, 16))

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
        for rect, ttype, key_label in self.get_tower_icon_rects():
            self.game.screen.blit(assets.tower_icons[ttype.value], rect.topleft)
            num_surf = assets.font_tower_level.render(key_label, True, YELLOW)
            self.game.screen.blit(num_surf, (rect.x + 2, rect.y + 2))
            price_surf = assets.font_tower_level.render(str(self.get_tower_cost(ttype)), True, GOLD)
            self.game.screen.blit(price_surf, (rect.right - price_surf.get_width() - 2,
                                              rect.bottom - price_surf.get_height() - 2))
            positions[ttype] = (rect.x, rect.y)
        if self.game.selected_tower_type in positions:
            x, y = positions[self.game.selected_tower_type]
            hl = 110
            pygame.draw.rect(self.game.screen, WHITE, (x - (hl - icon_size) // 2, y - (hl - icon_size) // 2, hl, hl), 4)

        pygame.draw.rect(self.game.screen, INFO_BORDER_COLOR,
                         (INFO_BORDER_X, INFO_BORDER_Y, INFO_BORDER_SIZE, INFO_BORDER_SIZE), INFO_BORDER_WIDTH)
        if self.game.selected_tower:
            infos = get_tower_info(self.game, self.game.selected_tower)
            # 行距 40：font_small 的实际字高是 37px，原来的 32px 会让相邻两行
            # 叠在一起（三阶分支信息一多就糊成一片）。40px 下最多 11 行也只到
            # y=457，仍在外框 512px 之内。
            for i, info in enumerate(infos):
                self.game.screen.blit(assets.font_small.render(info, True, WHITE),
                                     (INFO_BORDER_X + 20, INFO_BORDER_Y + 20 + i * 40))
        pygame.draw.rect(self.game.screen, INFO_BORDER_COLOR,
                         (INFO_BORDER_X, ENCHANT_BOX_Y, ENCHANT_BOX_WIDTH, ENCHANT_BOX_HEIGHT), INFO_BORDER_WIDTH)
        for rect, ench, cnt in self.get_enchant_icon_rects():
            self.game.screen.blit(assets.enchantment_icons[ench], rect.topleft)
            # 试毒合约叠加到 1 层也要显示；其他附魔只在重复持有时显示数量
            if cnt > 1 or (ench is Enchantment.POISON_CONTRACT and cnt > 0):
                badge = assets.font_tower_level.render(str(cnt), True, WHITE)
                pygame.draw.rect(self.game.screen, (0, 0, 0),
                                 (rect.right - badge.get_width() - 8, rect.bottom - badge.get_height() - 8,
                                  badge.get_width() + 8, badge.get_height() + 8))
                self.game.screen.blit(badge, (rect.right - badge.get_width() - 4, rect.bottom - badge.get_height() - 4))

        # 「重新开始」需要连点两次才生效（见 game.handle_events）。
        # 处于确认窗口时按钮变红并改文案，让玩家知道这一下会真的重置。
        confirm_pending = getattr(self.game, "confirm_reset", 0) > 0
        restart_color = (170, 40, 40) if confirm_pending else RESTART_BTN_COLOR
        pygame.draw.rect(self.game.screen, restart_color,
                         (RESTART_BTN_X, RESTART_BTN_Y, RESTART_BTN_WIDTH, RESTART_BTN_HEIGHT))
        restart_label = "再点一次确认" if confirm_pending else "重新开始"
        restart_text = assets.font_small.render(restart_label, True, WHITE)
        self.game.screen.blit(restart_text, (RESTART_BTN_X + 40, RESTART_BTN_Y + 10))

        pygame.draw.rect(self.game.screen, EXIT_BTN_COLOR,
                         (EXIT_BTN_X, EXIT_BTN_Y, EXIT_BTN_WIDTH, EXIT_BTN_HEIGHT))
        exit_text = assets.font_small.render("退出游戏", True, WHITE)
        self.game.screen.blit(exit_text, (EXIT_BTN_X + EXIT_BTN_WIDTH // 2 - exit_text.get_width() // 2, EXIT_BTN_Y + 10))

        stats_btn = self.get_stats_button_rect()
        pygame.draw.rect(self.game.screen, STATS_BTN_COLOR, stats_btn)
        pygame.draw.rect(self.game.screen, STATS_BTN_BORDER, stats_btn, 2)
        stats_label = assets.font_small.render("伤害统计 (TAB)", True, WHITE)
        self.game.screen.blit(stats_label, (stats_btn.centerx - stats_label.get_width() // 2,
                                            stats_btn.centery - stats_label.get_height() // 2))

        instructions = ["操作说明:", "0~9选择炮塔", "U升级 S出售", "R切换分支 E升5级", "ESC暂停"]
        for i, text in enumerate(instructions):
            self.game.screen.blit(assets.font_small.render(text, True, WHITE), (2156, 1144 + i * 48))

    def get_enchant_icon_rects(self):
        rects = []
        counts = {}
        for ench in self.game.enchantments:
            counts[ench] = counts.get(ench, 0) + 1
        for i, (ench, cnt) in enumerate(counts.items()):
            if ench is Enchantment.POISON_CONTRACT:
                # 角标显示「已叠加层数」：基础毒伤 = 5 + 层数
                cnt = max(0, self.game.poison_base_damage - 5)
            col = i % ENCHANT_ICONS_PER_ROW
            row = i // ENCHANT_ICONS_PER_ROW
            x = INFO_BORDER_X + INFO_PADDING + col * (ENCHANT_ICON_SIZE + ENCHANT_ICON_GAP)
            y = ENCHANT_BOX_Y + INFO_PADDING + row * (ENCHANT_ICON_SIZE + ENCHANT_ICON_GAP)
            rects.append((pygame.Rect(x, y, ENCHANT_ICON_SIZE, ENCHANT_ICON_SIZE), ench, cnt))
        return rects

    def get_tower_icon_rects(self):
        icon_size = 100
        gap = 64
        step = icon_size + gap
        total_w = len(self.game.TOWER_DATA) * step - gap
        bar_left = 60
        bar_right = INFO_BORDER_X - 40
        start_x = bar_left + (bar_right - bar_left - total_w) // 2
        iy = SCREEN_HEIGHT - 114
        keys = (1, 2, 3, 4, 5, 6, 7, 8, 9, 0, '-', 'X')
        rects = []
        for i, (ttype, name, cost, key) in enumerate(self.game.TOWER_DATA):
            ix = start_x + i * step
            rects.append((pygame.Rect(ix, iy, icon_size, icon_size), ttype, str(keys[i])))
        return rects

    def get_tower_cost(self, ttype):
        for t, name, cost, key in self.game.TOWER_DATA:
            if t == ttype:
                return cost
        return 0

    def wrap_text(self, text, font, max_width):
        lines = []
        while text:
            line = text
            while line and font.render(line, True, (0, 0, 0)).get_width() > max_width:
                line = line[:-1]
            if not line:
                break
            lines.append(line)
            text = text[len(line):]
        return lines

    def get_shop_panel_rect(self):
        """面板高度 = 标题区 + 卡片 + 底部按钮区，跟着卡片高度走。"""
        height = 110 + shop_slot_height() + 150
        return pygame.Rect(SCREEN_WIDTH // 2 - SHOP_PANEL_W // 2,
                           (SCREEN_HEIGHT - height) // 2,
                           SHOP_PANEL_W, height)

    def get_shop_slots(self):
        panel = self.get_shop_panel_rect()
        offers = self.game.shop_offers
        if not offers:
            return []
        slot_h = shop_slot_height()
        total_w = len(offers) * SHOP_SLOT_W + (len(offers) - 1) * SHOP_SLOT_GAP
        start_x = panel.x + (panel.w - total_w) // 2
        y = panel.y + 110
        return [(pygame.Rect(start_x + i * (SHOP_SLOT_W + SHOP_SLOT_GAP), y,
                             SHOP_SLOT_W, slot_h), ench)
                for i, ench in enumerate(offers)]

    def get_shop_continue_rect(self):
        panel = self.get_shop_panel_rect()
        return pygame.Rect(panel.right - 260, panel.bottom - 90, 220, 60)

    def get_shop_refresh_rect(self):
        # 「刷新 (20绿宝石)」用 font_small 量出来 289px，原来按钮只有 220px，字会溢出到框外
        panel = self.get_shop_panel_rect()
        return pygame.Rect(panel.x + 40, panel.bottom - 90, 320, 60)

    def draw_shop(self):
        pygame.mouse.set_visible(True)
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 200))
        self.game.screen.blit(overlay, (0, 0))
        panel = self.get_shop_panel_rect()
        pygame.draw.rect(self.game.screen, (45, 45, 45), panel)
        pygame.draw.rect(self.game.screen, WHITE, panel, 4)
        title = assets.font_large.render("流浪商人商店", True, WHITE)
        self.game.screen.blit(title, (panel.centerx - title.get_width() // 2, panel.y + 20))
        emerald_text = assets.font_medium.render(f"绿宝石:{self.game.emeralds}", True, GREEN)
        self.game.screen.blit(emerald_text, (panel.right - emerald_text.get_width() - 30, panel.y + 30))

        if assets.trader_img:
            tw, th = assets.trader_img.get_size()
            tx = panel.right + 40
            ty = panel.y + (panel.height - th) // 2
            pygame.draw.rect(self.game.screen, WHITE, (tx - 6, ty - 6, tw + 12, th + 12), 3)
            self.game.screen.blit(assets.trader_img, (tx, ty))

        for rect, ench in self.get_shop_slots():
            ench_data = ENCHANTMENT_DATA[ench]
            cnt = self.game.enchantments.count(ench)
            affordable = self.game.emeralds >= ench_data["cost"]
            pygame.draw.rect(self.game.screen, (70, 70, 70) if affordable else (45, 45, 45), rect)
            pygame.draw.rect(self.game.screen, (255, 215, 0) if affordable else (100, 100, 100), rect, 2)
            icon = assets.enchantment_icons_raw[ench]
            if icon:
                self.game.screen.blit(icon, (rect.centerx - icon.get_width() // 2, rect.y + 20))
            else:
                icon = assets.enchantment_icons[ench]
                self.game.screen.blit(icon, (rect.centerx - icon.get_width() // 2, rect.y + 34))
            name_surf = assets.font_tower_level.render(ench_data["name"], True, WHITE)
            self.game.screen.blit(name_surf, (rect.centerx - name_surf.get_width() // 2, rect.y + 155))
            status = assets.font_tower_level.render(f"{ench_data['cost']} 绿宝石", True, GREEN if affordable else (200, 80, 80))
            self.game.screen.blit(status, (rect.centerx - status.get_width() // 2, rect.y + 200))
            desc_lines = self.wrap_text(ench_data["desc"], assets.font_tower_level, rect.width - 40)
            for li, line in enumerate(desc_lines):
                desc_surf = assets.font_tower_level.render(line, True, (180, 180, 180))
                self.game.screen.blit(desc_surf, (rect.centerx - desc_surf.get_width() // 2, rect.y + SHOP_DESC_TOP + li * SHOP_LINE_H))

        if not self.game.shop_offers:
            empty_text = assets.font_medium.render("已拥有全部附魔", True, (200, 200, 200))
            self.game.screen.blit(empty_text, (panel.centerx - empty_text.get_width() // 2, panel.y + 280))

        refresh_rect = self.get_shop_refresh_rect()
        can_refresh = self.game.emeralds >= 20
        pygame.draw.rect(self.game.screen, (130, 110, 40) if can_refresh else (60, 60, 60), refresh_rect)
        refresh_text = assets.font_small.render(f"刷新 (20绿宝石)", True, WHITE if can_refresh else (140, 140, 140))
        self.game.screen.blit(refresh_text, (refresh_rect.centerx - refresh_text.get_width() // 2,
                                             refresh_rect.y + (refresh_rect.height - refresh_text.get_height()) // 2))

        cont_rect = self.get_shop_continue_rect()
        pygame.draw.rect(self.game.screen, (60, 130, 60), cont_rect)
        cont_text = assets.font_small.render("继续", True, WHITE)
        self.game.screen.blit(cont_text, (cont_rect.centerx - cont_text.get_width() // 2,
                                          cont_rect.y + (cont_rect.height - cont_text.get_height()) // 2))

    def _lantern_light(self, radius):
        """缓存的路灯光斑：中心完全透明、向外渐变，用于从迷雾里挖出可视区域。"""
        light = self._lantern_light_cache.get(radius)
        if light is not None:
            return light
        light = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
        light.fill((0, 0, 0, 0))
        steps = 40
        for i in range(steps, 0, -1):
            r = max(1, int(radius * i / steps))
            alpha = int(255 * (1.0 - i / steps) ** 0.55)
            pygame.draw.circle(light, (0, 0, 0, alpha), (radius, radius), r)
        self._lantern_light_cache[radius] = light
        return light

    def cut_lantern_lights(self, fog_surface):
        """星焰提灯在迷雾 / 永夜黑暗里照亮自身周围（类似植物大战僵尸的路灯花）。"""
        for tower in self.game.towers:
            if not tower.is_lantern():
                continue
            radius = int(tower.get_effective_range() * 1.05)
            if radius <= 0:
                continue
            light = self._lantern_light(radius)
            # 迷雾层整体下移了一个 TILE_SIZE，这里要减回去
            fog_surface.blit(light,
                             (tower.rect.centerx - radius, tower.rect.centery - TILE_SIZE - radius),
                             special_flags=pygame.BLEND_RGBA_SUB)

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

    def get_gameover_restart_wave_rect(self):
        return pygame.Rect(620, 850, 620, 80)

    def get_gameover_restart_run_rect(self):
        return pygame.Rect(1320, 850, 620, 80)

    def draw_game_over(self):
        pygame.mouse.set_visible(True)
        self.game.screen.fill(BLACK)
        text1 = assets.font_large.render("游戏结束!", True, RED)
        self.game.screen.blit(text1, (SCREEN_WIDTH // 2 - text1.get_width() // 2, 400))

        # 左：重来本波。只清场重打，不动存档也不动炮塔，所以单击即可
        wave_rect = self.get_gameover_restart_wave_rect()
        pygame.draw.rect(self.game.screen, (45, 95, 155), wave_rect)
        pygame.draw.rect(self.game.screen, (140, 195, 255), wave_rect, 3)
        wave_text = assets.font_medium.render("重新开始本波", True, WHITE)
        self.game.screen.blit(wave_text, (wave_rect.centerx - wave_text.get_width() // 2,
                                          wave_rect.centery - wave_text.get_height() // 2))

        # 右：重来本局。会覆盖存档，沿用连点两次确认（见 game.handle_events）
        confirm_pending = getattr(self.game, "confirm_reset", 0) > 0
        run_rect = self.get_gameover_restart_run_rect()
        pygame.draw.rect(self.game.screen, (170, 40, 40) if confirm_pending else GREEN, run_rect)
        pygame.draw.rect(self.game.screen, (255, 150, 150) if confirm_pending else (170, 255, 170),
                         run_rect, 3)
        run_label = "再点一次确认" if confirm_pending else "重新开始本局"
        run_text = assets.font_medium.render(run_label, True, WHITE)
        self.game.screen.blit(run_text, (run_rect.centerx - run_text.get_width() // 2,
                                         run_rect.centery - run_text.get_height() // 2))

        hint = assets.font_small.render(
            "本波重来保留炮塔、金币与附魔；本局重开会覆盖存档", True, (190, 190, 190))
        self.game.screen.blit(hint, (SCREEN_WIDTH // 2 - hint.get_width() // 2, 990))
        hint2 = assets.font_small.render("按 TAB 查看伤害统计", True, (160, 160, 160))
        self.game.screen.blit(hint2, (SCREEN_WIDTH // 2 - hint2.get_width() // 2, 1038))

    # ------------------------------------------------------------------ 最终BOSS HUD

    def get_disabled_overlay(self):
        surf = getattr(self, "_disabled_surf", None)
        if surf is None:
            surf = pygame.Surface((TILE_SIZE, TILE_SIZE), pygame.SRCALPHA)
            surf.fill((110, 30, 180, 95))
            pygame.draw.line(surf, (235, 130, 255), (16, 16), (TILE_SIZE - 16, TILE_SIZE - 16), 5)
            pygame.draw.line(surf, (235, 130, 255), (TILE_SIZE - 16, 16), (16, TILE_SIZE - 16), 5)
            self._disabled_surf = surf
        return surf

    def draw_boss_effects(self):
        for portal in self.game.boss_portals:
            portal.draw(self.game.screen)
        for beam in self.game.boss_beams:
            beam.draw(self.game.screen)
        for strike in self.game.boss_strikes:
            strike.draw(self.game.screen)
        for wave in self.game.boss_shockwaves:
            wave.draw(self.game.screen)
        for rune in self.game.boss_runes:
            rune.draw(self.game.screen)
        boss = self.game.final_boss
        if boss is not None:
            boss.draw_overlay(self.game.screen)

    def draw_boss_screen_fx(self):
        game = self.game
        if game.boss_time_frozen > 0:
            overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            overlay.fill((40, 90, 200, 56))
            game.screen.blit(overlay, (0, 0))
            text = assets.font_large.render("TICK FREEZE", True, (170, 225, 255))
            game.screen.blit(text, (SCREEN_WIDTH // 2 - text.get_width() // 2, 250))
        if game.boss_flash > 0:
            overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            overlay.fill((255, 120, 235, min(80, game.boss_flash)))
            game.screen.blit(overlay, (0, 0))
        if game.boss_acid_timer > 0:
            overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            overlay.fill((90, 220, 50, min(66, game.boss_acid_timer)))
            game.screen.blit(overlay, (0, 0))
            text = assets.font_large.render("ACID RAIN", True, (170, 255, 130))
            text.set_alpha(min(255, game.boss_acid_timer * 5))
            game.screen.blit(text, (SCREEN_WIDTH // 2 - text.get_width() // 2, 310))

    def draw_boss_hud(self):
        game = self.game
        boss = game.final_boss
        if boss is None:
            return

        screen = game.screen
        bar_x, bar_y, bar_w, bar_h = 330, 86, 1900, 44
        ratio = max(0.0, min(1.0, boss.health / boss.max_health))
        phase_color = FINAL_BOSS_PHASE_COLORS[boss.phase - 1]

        pygame.draw.rect(screen, (10, 4, 18), (bar_x - 4, bar_y - 4, bar_w + 8, bar_h + 8))
        pygame.draw.rect(screen, (36, 8, 36), (bar_x, bar_y, bar_w, bar_h))
        pygame.draw.rect(screen, phase_color, (bar_x, bar_y, int(bar_w * ratio), bar_h))

        for i in range(1, FINAL_BOSS_LAYERS):
            x = bar_x + bar_w * i // FINAL_BOSS_LAYERS
            pygame.draw.line(screen, (14, 4, 20), (x, bar_y), (x, bar_y + bar_h), 1)
        for k in range(1, 4):
            x = bar_x + bar_w * k // 4
            pygame.draw.line(screen, (255, 255, 255), (x, bar_y), (x, bar_y + bar_h), 3)
        pygame.draw.rect(screen, (235, 205, 255), (bar_x, bar_y, bar_w, bar_h), 2)

        name_label = f"{FINAL_BOSS_NAME} {FINAL_BOSS_EN_NAME}"
        name_shadow = assets.font_small.render(name_label, True, (20, 0, 20))
        screen.blit(name_shadow, (bar_x + 18, bar_y + 5))
        name = assets.font_small.render(name_label, True, (255, 240, 255))
        screen.blit(name, (bar_x + 16, bar_y + 3))

        phase_text = assets.font_tower_level.render(
            f"阶段 {boss.phase} : {FINAL_BOSS_PHASE_NAMES[boss.phase - 1]}", True, WHITE)
        screen.blit(phase_text, (SCREEN_WIDTH // 2 - phase_text.get_width() // 2, bar_y + 7))

        layer_text = assets.font_tower_level.render(
            f"{max(0, boss.current_layer)} / {FINAL_BOSS_LAYERS} 层", True, (255, 230, 160))
        screen.blit(layer_text, (bar_x + bar_w - layer_text.get_width() - 14, bar_y + 7))

        # 技能播报
        if game.boss_banner_timer > 0 and game.boss_banner_text:
            alpha = min(255, game.boss_banner_timer * 4)
            banner = pygame.Surface((1500, 40), pygame.SRCALPHA)
            banner.fill((0, 0, 0, min(200, alpha)))
            screen.blit(banner, (SCREEN_WIDTH // 2 - 750, 134))
            text = assets.font_tower_level.render(game.boss_banner_text, True, (255, 220, 150))
            text.set_alpha(alpha)
            screen.blit(text, (SCREEN_WIDTH // 2 - text.get_width() // 2, 140))

        # 世界重载读条
        if boss.reloading:
            remain = max(0, boss.reload_timer) / 60.0
            charge = 1.0 - boss.reload_timer / max(1, boss.reload_total)
            pygame.draw.rect(screen, (30, 0, 0), (760, 188, 1040, 24))
            pygame.draw.rect(screen, (255, 70, 50), (760, 188, int(1040 * charge), 24))
            pygame.draw.rect(screen, (255, 220, 200), (760, 188, 1040, 24), 2)
            warn = assets.font_tower_level.render(f"世界重载 {remain:.1f}s —— 击破任意一层可打断", True, WHITE)
            screen.blit(warn, (SCREEN_WIDTH // 2 - warn.get_width() // 2, 216))

        # 规则覆写提示：占用右上角空白位置
        if game.boss_rule:
            labels = {"attack_speed": "攻速-50%", "range": "射程-30%", "gold": "金币产量归零"}
            label = labels.get(game.boss_rule.get("type"), "规则覆写")
            remain = max(0, game.boss_rule["timer"]) / 60.0
            panel = pygame.Rect(TOP_PANEL_X, TOP_PANEL_Y,
                                TOP_PANEL_WIDTH, TOP_PANEL_HEIGHT)
            pygame.draw.rect(screen, (92, 28, 18), panel)
            pygame.draw.rect(screen, (255, 150, 80), panel, 3)
            rule_text = assets.font_tower_level.render(
                f"指令覆写：{label}  {remain:.1f}s", True, (255, 228, 190))
            screen.blit(rule_text, (panel.centerx - rule_text.get_width() // 2,
                                    panel.centery - rule_text.get_height() // 2))

    # ------------------------------------------------------------------ 伤害统计

    def get_stats_button_rect(self):
        return pygame.Rect(STATS_BTN_X, STATS_BTN_Y, STATS_BTN_WIDTH, STATS_BTN_HEIGHT)

    def get_stats_panel_rect(self):
        # 高度跟着属性条数走：剑系删掉后只剩 7 行，写死 1020 会在底部空出一大块
        height = 160 + len(stats.ELEMENTS) * 92 + 110
        return pygame.Rect(580, (SCREEN_HEIGHT - height) // 2, 1400, height)

    def get_stats_close_rect(self):
        panel = self.get_stats_panel_rect()
        return pygame.Rect(panel.right - 76, panel.y + 18, 56, 56)

    def draw_damage_stats(self):
        game = self.game
        screen = game.screen
        panel = self.get_stats_panel_rect()

        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 190))
        screen.blit(overlay, (0, 0))

        pygame.draw.rect(screen, (24, 22, 34), panel)
        pygame.draw.rect(screen, (190, 180, 255), panel, 3)

        title = assets.font_large.render("伤害统计", True, WHITE)
        screen.blit(title, (panel.centerx - title.get_width() // 2, panel.y + 20))

        data = game.damage_stats
        total_text = assets.font_small.render(
            f"总伤害：{stats.format_damage(data.total)}", True, (230, 220, 255))
        screen.blit(total_text, (panel.centerx - total_text.get_width() // 2, panel.y + 94))

        rows = data.rows()
        max_damage = max([row[2] for row in rows] + [1])
        top = panel.y + 160
        row_h = 92
        bar_x = panel.x + 420
        bar_w = 620
        bar_h = 30
        for i, (key, name, damage, color, icon) in enumerate(rows):
            y = top + i * row_h
            if i % 2 == 1:
                pygame.draw.rect(screen, (32, 30, 46),
                                 (panel.x + 28, y - 4, panel.width - 56, row_h - 8))
            if icon:
                screen.blit(icon, (panel.x + 44, y + 8))
            else:
                pygame.draw.rect(screen, (80, 80, 80), (panel.x + 44, y + 8, 56, 56))
            name_surf = assets.font_small.render(name, True, WHITE)
            screen.blit(name_surf, (panel.x + 124, y + 20))
            pygame.draw.rect(screen, (48, 44, 62), (bar_x, y + 18, bar_w, bar_h))
            fill = int(bar_w * damage / max_damage)
            if fill > 0:
                pygame.draw.rect(screen, color, (bar_x, y + 18, fill, bar_h))
            pygame.draw.rect(screen, (90, 84, 110), (bar_x, y + 18, bar_w, bar_h), 1)
            dmg_surf = assets.font_tower_level.render(stats.format_damage(damage), True, (255, 245, 220))
            screen.blit(dmg_surf, (panel.x + 1180 - dmg_surf.get_width(), y + 20))
            pct = (damage / data.total * 100) if data.total > 0 else 0.0
            if damage > 0 and pct < 0.1:
                pct_text = "<0.1%"
            else:
                pct_text = f"{pct:.1f}%"
            pct_surf = assets.font_tower_level.render(pct_text, True, (200, 200, 220))
            screen.blit(pct_surf, (panel.x + 1225, y + 20))

        close = self.get_stats_close_rect()
        pygame.draw.rect(screen, (70, 30, 40), close)
        pygame.draw.rect(screen, (255, 120, 120), close, 2)
        pygame.draw.line(screen, WHITE, (close.x + 16, close.y + 16), (close.right - 16, close.bottom - 16), 4)
        pygame.draw.line(screen, WHITE, (close.right - 16, close.y + 16), (close.x + 16, close.bottom - 16), 4)

        note = assets.font_tower_level.render(
            "统计口径：凋零→毒系；无尽贪婪/不稳定水晶→爆炸；余烬陨石→火系；蜜脾蜂群→毒系",
            True, (170, 165, 190))
        screen.blit(note, (panel.centerx - note.get_width() // 2, panel.bottom - 92))
        hint = assets.font_tower_level.render(
            "打开统计时游戏暂停，点击 X 或按 TAB / ESC 关闭", True, (150, 145, 170))
        screen.blit(hint, (panel.centerx - hint.get_width() // 2, panel.bottom - 52))

    def draw_herobrine_health_bar(self):
        for enemy in self.game.enemies:
            if enemy.enemy_type == EnemyType.HEROBRINE:
                # y=86 和最终 BOSS 血条同一行（两者永不共存：第 50 波 / 第 100 波）
                bar_x = 810
                bar_y = 86
                bar_width = 740
                bar_height = 44
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
        pygame.mouse.set_visible(True)
        self.game.screen.fill(BLACK)
        text1 = assets.font_large.render("胜利!", True, GREEN)
        self.game.screen.blit(text1, (SCREEN_WIDTH // 2 - text1.get_width() // 2, 400))
        confirm_pending = getattr(self.game, "confirm_reset", 0) > 0
        pygame.draw.rect(self.game.screen, (140, 110, 30) if confirm_pending else GREEN,
                         (900, 850, 760, 80))
        restart_label = "再点一次确认（会覆盖存档）" if confirm_pending else "重新开始"
        restart_text = assets.font_medium.render(restart_label, True, WHITE)
        self.game.screen.blit(restart_text, (SCREEN_WIDTH // 2 - restart_text.get_width() // 2, 855))
        hint = assets.font_tower_level.render("按 TAB 查看伤害统计", True, (190, 190, 190))
        self.game.screen.blit(hint, (SCREEN_WIDTH // 2 - hint.get_width() // 2, 970))