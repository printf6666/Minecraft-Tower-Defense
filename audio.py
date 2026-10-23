"""音频薄封装：为 pygame.mixer 提供一层永不抛异常的访问入口。

背景
----
这是发布前修的三个致命 bug 之一。玩家机器上没有可用音频设备时
（无声卡、远程桌面、独占被占用、容器内运行），pygame.mixer.init()
会失败，此后 pygame.mixer.music 的**任何**方法调用都抛异常。

而 game.py 里 mixer 调用多达 14 处，且全都写在游戏主循环的关键路径上：
其中 get_busy() 位于 `if self.state == PLAYING:` 分支内，意味着
**点下「开始游戏」的第一帧就会崩到桌面**。玩家看到的现象是
「点开始，窗口直接消失」，没有任何报错信息 —— 这是最劝退的一类崩溃。

设计要点
--------
1. init() 开机探测一次，失败时切 SDL_AUDIODRIVER=dummy 重试。
   dummy 驱动能初始化出一个「假」音频设备，所有 API 都可用、只是没声音。
   这比"到处判空"可靠得多 —— 调用方完全不用关心音频是否存在。
2. music_busy() 在无音频时返回 **True**，不是 False。
   这是刻意为之：调用方几乎都是 `if not music_busy(): 播下一首`。
   返回 True 表示"音乐正在播"，调用方就不会反复尝试播放，
   否则会变成每帧都去 load 一次音频文件的死循环。
3. 所有函数兜 try/except。音频失败永远不该让游戏崩溃 ——
   静音是可接受的降级，闪退不是。
"""

import os

import pygame

# 音频是否可用（init 之后有效）
_enabled = False

# 当前是否已切到 dummy 驱动（仅用于诊断输出，不参与逻辑判断）
_using_dummy = False


def init():
    """初始化音频子系统。返回是否可用。

    这个函数永远不会抛异常，最坏情况返回 False 并让全部音频调用变成空操作。
    """
    global _enabled, _using_dummy

    # 第一次尝试：用系统默认驱动
    try:
        if not pygame.mixer.get_init():
            pygame.mixer.init()
        # 探针：确认 music 模块真的能应答，而不只是 mixer 初始化成功
        pygame.mixer.music.get_busy()
        _enabled = True
        return True
    except Exception:
        pass

    # 第二次尝试：切 dummy 驱动，静音但 API 可用
    try:
        os.environ["SDL_AUDIODRIVER"] = "dummy"
        try:
            pygame.mixer.quit()
        except Exception:
            pass
        pygame.mixer.init()
        pygame.mixer.music.get_busy()
        _enabled = True
        _using_dummy = True
        return True
    except Exception:
        pass

    # 彻底失败：全部音频调用变成空操作
    _enabled = False
    return False


def is_enabled():
    """音频是否可用（dummy 驱动也算可用）。"""
    return _enabled


def is_silent():
    """当前是否为静音降级模式（dummy 驱动）。"""
    return _using_dummy


def music_busy():
    """当前是否有 BGM 在播放。

    注意：音频不可用（含 dummy 静音降级）时返回 True，让调用方"以为在播"
    从而不做任何操作。若返回 False，`if not music_busy()` 这类判断会每帧
    都触发一次 load+play 尝试 —— 虽然被 try 吞掉不会崩，但会白白吃 IO。
    """
    if not _enabled or _using_dummy:
        return True
    try:
        return pygame.mixer.music.get_busy()
    except Exception:
        return True


def play_music(path, loops=-1):
    """播放 BGM。失败静默。"""
    if not _enabled or _using_dummy:
        return False
    try:
        pygame.mixer.music.load(path)
        pygame.mixer.music.play(loops)
        return True
    except Exception:
        return False


def stop_music():
    """停止 BGM。失败静默。"""
    if not _enabled:
        return
    try:
        pygame.mixer.music.stop()
    except Exception:
        pass


def play_sound(sound):
    """播放音效。sound 为 None 时直接跳过（调用方不用再判空）。"""
    if not _enabled or _using_dummy or sound is None:
        return
    try:
        sound.play()
    except Exception:
        pass