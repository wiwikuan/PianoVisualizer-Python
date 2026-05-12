#!/usr/bin/env python3
"""
MIDI Piano Visualizer (AA version)
Supersampling anti-aliasing for smooth rounded keys.

Dependencies:
    pip install pygame mido python-rtmidi

Run:
    python piano-visualizer.py
"""

import sys
import colorsys
import pygame
import mido

# ---------- 可調參數（對齊原版） ----------

IS_BLACK = [0, 11, 0, 13, 0, 0, 11, 0, 12, 0, 13, 0]

BORDER = 3
WHITE_KEY_WIDTH = 20
WHITE_KEY_SPACE = 1
BLACK_KEY_WIDTH = 17
BLACK_KEY_HEIGHT = 45
RADIUS = 5
B_RADIUS = 4
KEY_AREA_Y = 3
KEY_AREA_HEIGHT = 70

RAINBOW_MODE = False
NOTE_NAMES = False

KEY_ON_HSB = (326, 100, 100)
PEDALED_HSB = (326, 100, 70)

WIN_WIDTH = (WHITE_KEY_WIDTH + WHITE_KEY_SPACE) * 52 + (BORDER * 2)
WIN_HEIGHT = KEY_AREA_HEIGHT + (KEY_AREA_Y * 2)

BG_HSB = (0, 0, 30)
FPS = 60

# 超取樣倍率：3x 已經很漂亮，4x 更絲滑但稍微吃 CPU
SUPERSAMPLE = 3

# ---------- 工具 ----------

def hsb_to_rgb(h, s, v):
    r, g, b = colorsys.hsv_to_rgb(h / 360.0, s / 100.0, v / 100.0)
    return (int(r * 255), int(g * 255), int(b * 255))


def rainbow_color(pitch, value=100):
    hue = ((pitch - 21) / (108 - 21) * 1080) % 360
    return hsb_to_rgb(hue, 100, value)


def pick_midi_input():
    ports = mido.get_input_names()
    if not ports:
        print("找不到任何 MIDI 輸入裝置。請先插上鍵盤再試一次。")
        sys.exit(1)

    print("\nAvailable MIDI inputs:")
    for i, name in enumerate(ports):
        print(f"  [{i}] {name}")

    if len(ports) == 1:
        print(f"\n只有一個裝置，自動選擇 [0] {ports[0]}")
        return ports[0]

    while True:
        try:
            choice = input("\n選擇要使用的 MIDI 輸入編號：").strip()
            idx = int(choice)
            if 0 <= idx < len(ports):
                return ports[idx]
        except (ValueError, KeyboardInterrupt, EOFError):
            print("再來一次。")


# ---------- 狀態 ----------

class State:
    def __init__(self):
        self.is_key_on = [0] * 128
        self.is_pedaled = [0] * 128
        self.now_pedaling = False

    def note_on(self, pitch, velocity):
        if velocity == 0:
            self.note_off(pitch)
            return
        self.is_key_on[pitch] = 1
        if self.now_pedaling:
            self.is_pedaled[pitch] = 1

    def note_off(self, pitch):
        self.is_key_on[pitch] = 0

    def control_change(self, number, value):
        if number == 64:
            if value >= 64:
                self.now_pedaling = True
                for i in range(128):
                    self.is_pedaled[i] = self.is_key_on[i]
            else:
                self.now_pedaling = False
                for i in range(128):
                    self.is_pedaled[i] = 0


# ---------- 繪製（在放大的 surface 上畫，最後縮小） ----------

def draw_rounded_rect(surface, color, rect, radius, stroke_color=None, stroke_width=0):
    pygame.draw.rect(surface, color, rect, border_radius=radius)
    if stroke_color is not None and stroke_width > 0:
        pygame.draw.rect(surface, stroke_color, rect, width=stroke_width, border_radius=radius)


def draw_scene(big_surface, state, font_big):
    s = SUPERSAMPLE

    border = BORDER * s
    wkw = WHITE_KEY_WIDTH * s
    wks = WHITE_KEY_SPACE * s
    bkw = BLACK_KEY_WIDTH * s
    bkh = BLACK_KEY_HEIGHT * s
    radius = RADIUS * s
    bradius = B_RADIUS * s
    kay = KEY_AREA_Y * s
    kah = KEY_AREA_HEIGHT * s

    key_on_rgb = hsb_to_rgb(*KEY_ON_HSB)
    pedaled_rgb = hsb_to_rgb(*PEDALED_HSB)
    white_rgb = (255, 255, 255)
    black_rgb = (0, 0, 0)
    stroke_rgb = (0, 0, 0)
    bg_rgb = hsb_to_rgb(*BG_HSB)

    big_surface.fill(bg_rgb)

    # --- 白鍵 ---
    w_index = 0
    for i in range(21, 109):
        if IS_BLACK[i % 12] == 0:
            if state.is_key_on[i] == 1 and not RAINBOW_MODE:
                color = key_on_rgb
            elif state.is_key_on[i] == 1 and RAINBOW_MODE:
                color = rainbow_color(i, 100)
            elif state.is_pedaled[i] == 1 and not RAINBOW_MODE:
                color = pedaled_rgb
            elif state.is_pedaled[i] == 1 and RAINBOW_MODE:
                color = rainbow_color(i, 70)
            else:
                color = white_rgb

            x = border + w_index * (wkw + wks)
            rect = pygame.Rect(x, kay, wkw, kah)
            draw_rounded_rect(big_surface, color, rect, radius,
                              stroke_color=stroke_rgb, stroke_width=max(1, s // 2))
            w_index += 1

    # --- 黑鍵 ---
    w_index = 0
    for i in range(21, 109):
        if IS_BLACK[i % 12] == 0:
            w_index += 1
            continue

        if state.is_key_on[i] == 1 and not RAINBOW_MODE:
            color = key_on_rgb
        elif state.is_key_on[i] == 1 and RAINBOW_MODE:
            color = rainbow_color(i, 100)
        elif state.is_pedaled[i] == 1 and not RAINBOW_MODE:
            color = pedaled_rgb
        elif state.is_pedaled[i] == 1 and RAINBOW_MODE:
            color = rainbow_color(i, 70)
        else:
            color = black_rgb

        x = border + (w_index - 1) * (wkw + wks) + IS_BLACK[i % 12] * s
        rect = pygame.Rect(x, kay - 1 * s, bkw, bkh)
        draw_rounded_rect(big_surface, color, rect, bradius,
                          stroke_color=stroke_rgb, stroke_width=max(1, int(s * 0.75)))

    # --- 音名 ---
    if NOTE_NAMES:
        note_names = ["A", "B", "C", "D", "E", "F", "G"]
        text_rgb = (64, 64, 64)
        w_index = 0
        for i in range(52):
            x = border + w_index * (wkw + wks)
            y = kay + kah - 13 * s
            name = note_names[i % 7]
            surf = font_big.render(name, True, text_rgb)
            rect = surf.get_rect(center=(x + wkw // 2, y))
            big_surface.blit(surf, rect)
            w_index += 1


# ---------- 主程式 ----------

def main():
    port_name = pick_midi_input()

    pygame.init()
    pygame.display.set_caption("MIDI Piano Visualizer")

    screen = pygame.display.set_mode((WIN_WIDTH, WIN_HEIGHT))
    big_surface = pygame.Surface((WIN_WIDTH * SUPERSAMPLE, WIN_HEIGHT * SUPERSAMPLE))
    clock = pygame.time.Clock()

    # 字型也要放大版（跟著 big_surface 一起縮小，文字就會 AA）
    font_big = pygame.font.SysFont(None, 14 * SUPERSAMPLE)

    state = State()

    print(f"\n開始接收：{port_name}")
    print("視窗聚焦時按 R 切換彩虹模式、N 切換音名、ESC 或關閉視窗結束。")

    global RAINBOW_MODE, NOTE_NAMES

    with mido.open_input(port_name) as port:
        running = True
        while running:
            for msg in port.iter_pending():
                if msg.type == "note_on":
                    state.note_on(msg.note, msg.velocity)
                elif msg.type == "note_off":
                    state.note_off(msg.note)
                elif msg.type == "control_change":
                    state.control_change(msg.control, msg.value)

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        running = False
                    elif event.key == pygame.K_r:
                        RAINBOW_MODE = not RAINBOW_MODE
                    elif event.key == pygame.K_n:
                        NOTE_NAMES = not NOTE_NAMES

            # 1) 在放大 surface 上繪製
            draw_scene(big_surface, state, font_big)
            # 2) smoothscale 縮回視窗大小 → 邊緣自動柔化
            pygame.transform.smoothscale(big_surface, (WIN_WIDTH, WIN_HEIGHT), screen)

            pygame.display.flip()
            clock.tick(FPS)

    pygame.quit()


if __name__ == "__main__":
    main()
