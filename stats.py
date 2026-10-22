"""按属性统计伤害。

七种属性：物理 / 火系 / 冰系 / 电系 / 风系 / 毒系 / 爆炸。
图标直接复用对应「强化附魔」的图标。

归因约定：
- 塔的伤害：箭塔/传送塔 = 物理，冰塔 = 冰系，火塔 = 火系，三叉戟 = 电系，
  风塔 = 风系，毒塔 = 毒系，TNT/核弹 = 爆炸。
- 减益：燃烧 = 火系，中毒 = 毒系，**凋零 = 毒系**（凋零由毒塔体系施加，
  单独拆一行意义不大），蓄风爆炸 = 风系。
- 附魔：无尽贪婪奇点 = 爆炸，余烬重生陨石 = 火系，试毒合约爆炸 = 毒系，
  无限手套 = 按抽到的属性，不稳定水晶 = 爆炸，蜜脾蜂群 = 毒系。
"""

import pygame

import assets
from config import *

# (key, 显示名, 对应强化附魔, 条形图颜色)
ELEMENTS = [
    ("physical", "物理伤害", Enchantment.PHYSICAL, (235, 235, 235)),
    ("fire", "火系伤害", Enchantment.FLAME, (255, 128, 56)),
    ("ice", "冰系伤害", Enchantment.ICE, (130, 205, 255)),
    ("electric", "电系伤害", Enchantment.TRIDENT, (205, 130, 255)),
    ("wind", "风系伤害", Enchantment.WIND, (150, 255, 180)),
    ("poison", "毒系伤害", Enchantment.POISON, (130, 225, 90)),
    ("explosion", "爆炸伤害", Enchantment.BOMB, (255, 185, 70)),
]

ELEMENT_NAME = {key: name for key, name, _, _ in ELEMENTS}
ELEMENT_COLOR = {key: color for key, _, _, color in ELEMENTS}
ELEMENT_ENCHANT = {key: ench for key, _, ench, _ in ELEMENTS}

# 塔 → 属性
TOWER_ELEMENT = {
    TowerType.PHYSICAL: "physical",
    TowerType.TELEPORT: "physical",
    TowerType.ICE: "ice",
    TowerType.FLAME: "fire",
    TowerType.TRIDENT: "electric",
    TowerType.WIND: "wind",
    TowerType.POISON: "poison",
    TowerType.BOMB: "explosion",
}


def tower_element(tower_type):
    return TOWER_ELEMENT.get(tower_type)


def format_damage(value):
    value = int(value)
    if value >= 100_000_000:
        return f"{value / 100_000_000:.2f}亿"
    if value >= 10_000:
        return f"{value / 10_000:.1f}万"
    return str(value)


class DamageStats:
    def __init__(self):
        self.damage = {}
        self.total = 0
        self._icons = {}
        self.reset()

    def reset(self):
        self.damage = {key: 0 for key, _, _, _ in ELEMENTS}
        self.total = 0

    def add(self, element, amount):
        amount = int(amount)
        if amount <= 0 or element not in self.damage:
            return
        self.damage[element] += amount
        self.total += amount

    def rows(self):
        """固定顺序返回 (key, 名称, 伤害, 颜色, 图标)。"""
        rows = []
        for key, name, _, color in ELEMENTS:
            rows.append((key, name, self.damage[key], color, self.icon(key)))
        return rows

    def to_dict(self):
        return {key: int(self.damage.get(key, 0)) for key, _, _, _ in ELEMENTS}

    def load_dict(self, data):
        """从存档恢复七属性伤害；缺省或非法值按 0 处理。"""
        self.reset()
        if not isinstance(data, dict):
            return
        for key, _, _, _ in ELEMENTS:
            try:
                value = int(data.get(key, 0))
            except (TypeError, ValueError):
                value = 0
            self.damage[key] = max(0, value)
            self.total += self.damage[key]

    def icon(self, key):
        if key not in self._icons:
            ench = ELEMENT_ENCHANT[key]
            raw = assets.enchantment_icons_raw.get(ench)
            if raw is None:
                raw = assets.enchantment_icons.get(ench)
            if raw is not None:
                self._icons[key] = pygame.transform.smoothscale(raw, (56, 56))
            else:
                self._icons[key] = None
        return self._icons[key]
