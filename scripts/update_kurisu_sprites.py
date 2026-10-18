import os

# WS2812B Hardware-Equalized Color Palette - Exact Perfect Version
BG_OFF = (0, 0, 0)          # Background prohibited from emitting light / 彻底熄灭
DARK_BLK = (40, 34, 44)     # Body black parts: subtle dark charcoal micro-glow
HR_D = (75, 36, 22)         # #472D1E: Hair dark contour
HAIR = (180, 75, 42)        # Calibrated: Boosted red channel for vibrant auburn hair on WS2812B
HR_M = (120, 50, 30)        # #6A3621: Hair mid shadow
HR_L = (220, 120, 80)       # #BA7766: Hair highlight
LASH = (115, 35, 170)       # Brightened vivid deep violet lash (clearly illuminated anime eyeliner)
EYEW = (210, 215, 230)      # Crisp clean white sclera (suppressed green flare)
IRIS = (20, 60, 205)        # True Deep Cobalt Blue (紫蓝 -> 纯正钴蓝, B-dominant)
EYEL = (215, 85, 240)       # True Luminous Lavender (薰衣草紫 -> 明艳薰衣草紫, R+B dominant)
SKIN = (235, 145, 110)      # Warm anime peach skin (reduced G from 246 to 145 to prevent blinding white)
SHIRT_A = (190, 205, 220)   # Clean light blue-grey shirt collar
SHIRT_W = (220, 225, 235)   # Crisp white shirt center
TIE = (220, 30, 42)         # Saturated crimson tie
COAT = (185, 115, 75)       # Classic khaki coat
BOOT = (136, 95, 75)        # Brown leather boots

grid = [
    # Y=0
    [BG_OFF, BG_OFF, BG_OFF, BG_OFF, BG_OFF, HR_D, HR_D, HR_M, HR_M, HR_D, HR_D, BG_OFF, BG_OFF, BG_OFF, BG_OFF, BG_OFF],
    # Y=1
    [BG_OFF, BG_OFF, BG_OFF, HR_D, HR_D, HAIR, HAIR, HAIR, HAIR, HAIR, HAIR, HR_D, HR_D, BG_OFF, BG_OFF, BG_OFF],
    # Y=2
    [BG_OFF, HR_D, HR_L, HAIR, HAIR, HAIR, HAIR, HAIR, HAIR, HAIR, HR_L, HAIR, HAIR, HAIR, HR_D, BG_OFF],
    # Y=3
    [BG_OFF, HR_D, HAIR, HAIR, HAIR, HR_L, HAIR, HR_L, HR_L, HAIR, HAIR, HR_M, HAIR, HAIR, HR_D, BG_OFF],
    # Y=4
    [HR_D, HAIR, HAIR, HAIR, HAIR, HAIR, HAIR, HAIR, HAIR, HAIR, HAIR, HAIR, HR_M, HAIR, HAIR, HR_D],
    # Y=5
    [HR_D, HAIR, HAIR, HR_M, HAIR, HAIR, HAIR, HAIR, HAIR, HR_M, HAIR, HAIR, HAIR, HR_M, HAIR, HAIR, HR_D][:16],
    # Y=6
    [HR_D, HAIR, HR_M, HAIR, HAIR, HR_M, SKIN, HAIR, HR_M, SKIN, HR_M, HAIR, HAIR, HR_M, HAIR, HR_D],
    # Y=7
    [HR_D, HAIR, HR_M, HAIR, LASH, LASH, LASH, HAIR, SKIN, LASH, LASH, LASH, HAIR, HR_M, HAIR, HR_D],
    # Y=8
    [HR_D, HAIR, HAIR, HAIR, EYEW, IRIS, IRIS, SKIN, SKIN, IRIS, IRIS, EYEW, HAIR, HAIR, HAIR, HR_D],
    # Y=9
    [HR_D, HAIR, HAIR, HAIR, EYEW, EYEL, EYEL, SKIN, SKIN, EYEL, EYEL, EYEW, HAIR, HAIR, HAIR, HR_D],
    # Y=10
    [BG_OFF, BG_OFF, HR_D, HAIR, HR_M, HR_M, HR_D, SHIRT_A, SHIRT_A, HR_D, HR_M, HR_M, HAIR, HR_D, BG_OFF, BG_OFF],
    # Y=11
    [BG_OFF, BG_OFF, HR_D, HAIR, HR_M, DARK_BLK, COAT, TIE, TIE, COAT, DARK_BLK, HR_M, HAIR, HR_D, BG_OFF, BG_OFF],
    # Y=12
    [BG_OFF, BG_OFF, HR_D, HAIR, DARK_BLK, COAT, COAT, SHIRT_W, SHIRT_W, COAT, COAT, DARK_BLK, HAIR, HR_D, BG_OFF, BG_OFF],
    # Y=13
    [BG_OFF, BG_OFF, HR_D, DARK_BLK, SKIN, COAT, COAT, SHIRT_A, SHIRT_A, COAT, COAT, SKIN, DARK_BLK, HR_D, BG_OFF, BG_OFF],
    # Y=14
    [BG_OFF, BG_OFF, BG_OFF, BG_OFF, BG_OFF, DARK_BLK, BOOT, BOOT, BOOT, BOOT, DARK_BLK, BG_OFF, BG_OFF, BG_OFF, BG_OFF, BG_OFF],
    # Y=15
    [BG_OFF, BG_OFF, BG_OFF, BG_OFF, BG_OFF, BG_OFF, DARK_BLK, DARK_BLK, DARK_BLK, DARK_BLK, BG_OFF, BG_OFF, BG_OFF, BG_OFF, BG_OFF, BG_OFF]
]

def format_frame(name, g):
    lines = [f'static const ColorRGB {name}[16][16] = {{']
    for row in g:
        row_str = '    {' + ''.join(f'ColorRGB({c[0]}, {c[1]}, {c[2]}), ' for c in row) + '},'
        lines.append(row_str)
    lines.append('};\n')
    return '\n'.join(lines)

content = '// Generated Makise Kurisu 16x16 Pixel Matrix - Exact Perfect Version\n'
content += '#pragma once\n'
content += '#include "display_types.h"\n\n'
content += format_frame('KURISU_FRAME_IDLE', grid)
content += format_frame('KURISU_FRAME_BLINK', grid)
content += format_frame('KURISU_FRAME_TALK1', grid)
content += format_frame('KURISU_FRAME_TALK2', grid)

target_path = r'C:\workspace\Intelligent-Lighting-Control-System-Pro\firmware-s3\main\display\kurisu_sprites.h'
with open(target_path, 'w', encoding='utf-8') as f:
    f.write(content)

print('Updated:', target_path)
