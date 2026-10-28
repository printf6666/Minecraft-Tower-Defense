"""大招动画叠加层：「臻品呈现」的全屏视频播放。

为什么不用 pygame.movie：pygame 2 已经把它移除了。
为什么不用运行时解码：解码 mp4 要拖 ffmpeg / opencv，打包体积和兼容性都不划算，
所以视频在构建阶段就用 ffmpeg 拆成 JPEG 帧（video/ultimate/frame_XXX.jpg），
运行时只做「读一张 → 放大到屏幕 → blit」。

为什么要有后台预取线程：一帧 1156x720 的 JPEG 解码约 8ms、放大到 2560x1600 约
10ms，加起来接近 30fps 的单帧预算。全放主线程会让整个游戏在这 1.6 秒里明显卡顿，
所以读取 + 缩放都丢给工作线程，主线程只从缓存里取现成的 Surface。

「比全屏大一点」的实现：不是把 Surface 画到屏幕外面（那样要额外分配 20MB），
而是先按 ULTIMATE_VIDEO_ZOOM 把源画面中心裁一块、再放大到满屏 ——
数学上等价于「放大 1.15 倍后居中裁切」，右下角的 UID 自然就被裁掉了。
"""

import os
import sys
import threading

import pygame

from config import SCREEN_WIDTH, SCREEN_HEIGHT, ULTIMATE_VIDEO_ZOOM, ULTIMATE_VIDEO_FPS

FRAME_DIR = "video/ultimate"


def resource_path(relative_path):
    base_path = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_path, relative_path)


class UltimateVideo:
    """播一遍就结束的帧序列播放器。"""

    PREFETCH = 3          # 缓存里最多存几帧（一帧 16MB，别贪多）

    def __init__(self, screen_size=(SCREEN_WIDTH, SCREEN_HEIGHT), zoom=ULTIMATE_VIDEO_ZOOM,
                 fps=ULTIMATE_VIDEO_FPS):
        self.screen_w, self.screen_h = screen_size
        self.zoom = max(1.0, float(zoom))
        self.frame_interval = 1000.0 / max(1, fps)

        folder = resource_path(FRAME_DIR)
        self.paths = []
        if os.path.isdir(folder):
            self.paths = [os.path.join(folder, n) for n in sorted(os.listdir(folder))
                          if n.lower().endswith(".jpg")]
        if not self.paths:
            # 打包时忘了 --add-data "video;video" 会走到这里。以前是静默跳过动画，
            # 表现成「大招没反应」，排查起来很费劲，所以留一条日志。
            print(f"[UltimateVideo] 没找到视频帧: {folder}，大招动画将跳过")

        self.index = -1
        self.elapsed = 0.0
        self.last_tick = pygame.time.get_ticks()
        self.current = None
        self.done = not self.paths

        self._ready = {}
        self._lock = threading.Condition()
        self._stop = threading.Event()
        self._worker = None
        if self.paths:
            # 首帧在主线程同步渲染一次：
            # 这样第一帧必定有画面，后续才能安心「缺帧就保持上一帧」，
            # 否则会退化成主线程同步渲染 —— 那等于和预取线程抢 CPU，
            # 两边都按 20ms/帧 跑，播放端永远慢一帧、永远命中不了缓存。
            try:
                self.current = self._render(0)
            except Exception:
                self.current = None
            self.index = 0
            self._worker = threading.Thread(target=self._prefetch, daemon=True)
            self._worker.start()

    # ------------------------------------------------------------ 预取线程
    def _prefetch(self):
        i = self.index + 1      # 0 号帧已经在主线程预热过了
        total = len(self.paths)
        while i < total:
            if self._stop.is_set():
                return
            # 播放头已经越过的帧直接跳过：否则缓存会被一堆没人要的旧帧占满，
            # 工作线程堵在「缓存已满」上，而主线程要的新帧永远做不出来。
            if i < self.index:
                i += 1
                continue
            with self._lock:
                while len(self._ready) >= self.PREFETCH and not self._stop.is_set():
                    self._lock.wait(0.05)
                if self._stop.is_set():
                    return
            surf = None
            try:
                surf = self._render(i)
            except Exception:
                surf = None
            with self._lock:
                self._ready[i] = surf
                self._lock.notify_all()
            i += 1

    def _render(self, index):
        """读一帧并放大成屏幕尺寸（只保留 zoom 倍数的中心区域）。"""
        img = pygame.image.load(self.paths[index]).convert()
        w, h = img.get_size()
        crop_w = max(1, int(w / self.zoom))
        crop_h = max(1, int(h / self.zoom))
        left = (w - crop_w) // 2
        top = (h - crop_h) // 2
        sub = img.subsurface((left, top, crop_w, crop_h))
        return pygame.transform.smoothscale(sub, (self.screen_w, self.screen_h))

    def _take(self, index):
        with self._lock:
            # 顺手清掉已经过期的帧，把缓存位让给预取线程
            for stale in [k for k in self._ready if k < index]:
                del self._ready[stale]
            surf = self._ready.pop(index, None)
            self._lock.notify_all()
        return surf

    # ------------------------------------------------------------ 主线程
    def update(self):
        """按真实时间推进；返回 False 表示播完了。"""
        if self.done:
            return False
        now = pygame.time.get_ticks()
        dt = now - self.last_tick
        self.last_tick = now
        # 卡顿保护：单帧最多按 3 个视频帧推进，避免掉帧后动画直接跳完
        self.elapsed += min(dt, self.frame_interval * 3)

        target = int(self.elapsed / self.frame_interval)
        if target >= len(self.paths):
            self.finish()
            return False
        if target != self.index:
            self.index = target
            surf = self._take(target)
            if surf is not None:
                self.current = surf
            # 预取没跟上就继续显示上一帧（宁可掉一帧，也不要抢预取线程的 CPU）
        return True

    def draw(self, screen):
        if self.current is not None:
            screen.blit(self.current, (0, 0))

    def finish(self):
        self.done = True
        self._stop.set()
        with self._lock:
            self._lock.notify_all()
        self.current = None
        self._ready.clear()
        worker = self._worker
        if worker is not None and worker.is_alive():
            worker.join(timeout=0.2)
        self._worker = None
