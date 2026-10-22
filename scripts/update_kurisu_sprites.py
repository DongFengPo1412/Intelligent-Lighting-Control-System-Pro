from pathlib import Path

# Source image colors remain the reference. LED output below follows the user's
# visual feedback, independently of the source sRGB values.
DESK_PET_BRIGHTNESS_PERCENT = 100
LED_REFERENCE_BRIGHTNESS = 20
BG_OFF = (0, 0, 0)          # Background prohibited from emitting light / 彻底熄灭
DARK_BLK = (0, 0, 0)        # #000000: Actual dark clothing pixels in the PNG
SOLE = (0, 0, 0)            # #000000: Actual boot outline and sole in the PNG
HR_D = (71, 45, 30)         # #472D1E: Hair dark contour
HAIR = (141, 74, 58)        # #8D4A3A: Hair main color
HR_M = (106, 54, 33)        # #6A3621: Hair shadow
HR_L = (186, 119, 102)      # #BA7766: Hair highlight
LASH = (52, 28, 78)         # #341C4E: Upper eyelid
EYEW = (255, 255, 255)      # #FFFFFF: Outer eye white
IRIS = (135, 141, 215)      # #878DD7: Upper iris
EYEL = (225, 213, 253)      # #E1D5FD: Lower iris
SKIN = (253, 246, 240)      # #FDF6F0: Skin
SHIRT_A = (224, 232, 238)   # #E0E8EE: Actual collar pixels in the PNG
SHIRT_W = (255, 255, 255)   # #FFFFFF: Shirt highlight
TIE = (195, 84, 73)         # #C35449: Tie
COAT = (174, 121, 89)       # #AE7959: Coat
BOOT = (136, 103, 84)       # #886754: Boots

# Initial physical PWM targets at global brightness 20, not screen RGB colors.
# These are a tuning starting point; the user judges the actual panel appearance.
LED_REFERENCE_PWM = {
    'BG_OFF': (0, 0, 0),
    'HR_D': (3, 2, 1),       # Dark brown outer hair, not a red outline
    'HAIR': (9, 1, 1),       # Deep saturated red main hair
    'HR_M': (4, 1, 0),       # Dark red-brown hair strands
    'HR_L': (13, 3, 1),      # Brighter warm red strands, avoiding pale pink
    'LASH': (2, 0, 3),       # Very dark purple eyelid
    'IRIS': (6, 2, 9),       # Light purple upper iris
    'EYEL': (10, 5, 13),     # Lighter purple lower iris, distinct from skin
    'SKIN': (12, 5, 4),      # Warm flesh pink instead of white
    'EYEW': (9, 10, 12),     # Restrained cool white eye corners
    'SHIRT_A': (9, 10, 12),
    'SHIRT_W': (9, 10, 12),
    'TIE': (20, 0, 0),       # Strongest red accent in the whole character
    'COAT': (7, 4, 2),       # Coffee brown, distinct from red hair
    'PANTS': (4, 2, 1),      # Darker coffee brown, penultimate row
    'DARK_BLK': (2, 1, 1),   # Dim seams, distinct from the unlit background
    'SOLE': (1, 1, 1),       # Near-black shoes stay faintly visible
}
LED_PALETTE = {
    name: tuple((channel * 255 + LED_REFERENCE_BRIGHTNESS - 1) // LED_REFERENCE_BRIGHTNESS
                for channel in rgb)
    for name, rgb in LED_REFERENCE_PWM.items()
}

SOURCE_PALETTE = {
    'BG_OFF': BG_OFF,
    'DARK_BLK': DARK_BLK,
    'SOLE': SOLE,
    'HR_D': HR_D,
    'HAIR': HAIR,
    'HR_M': HR_M,
    'HR_L': HR_L,
    'LASH': LASH,
    'EYEW': EYEW,
    'IRIS': IRIS,
    'EYEL': EYEL,
    'SKIN': SKIN,
    'SHIRT_A': SHIRT_A,
    'SHIRT_W': SHIRT_W,
    'TIE': TIE,
    'COAT': COAT,
    'BOOT': BOOT,
    'PANTS': BOOT,  # Source PNG brown; output role follows the user description.
}

grid_roles = [
    ['BG_OFF', 'BG_OFF', 'BG_OFF', 'BG_OFF', 'BG_OFF', 'HR_D', 'HR_D', 'HR_M', 'HR_M', 'HR_D', 'HR_D', 'BG_OFF', 'BG_OFF', 'BG_OFF', 'BG_OFF', 'BG_OFF'],
    ['BG_OFF', 'BG_OFF', 'BG_OFF', 'HR_D', 'HR_D', 'HAIR', 'HAIR', 'HAIR', 'HAIR', 'HAIR', 'HAIR', 'HR_D', 'HR_D', 'BG_OFF', 'BG_OFF', 'BG_OFF'],
    ['BG_OFF', 'HR_D', 'HR_L', 'HAIR', 'HAIR', 'HAIR', 'HAIR', 'HAIR', 'HAIR', 'HAIR', 'HR_L', 'HAIR', 'HAIR', 'HAIR', 'HR_D', 'BG_OFF'],
    ['BG_OFF', 'HR_D', 'HAIR', 'HAIR', 'HAIR', 'HR_L', 'HAIR', 'HR_L', 'HR_L', 'HAIR', 'HAIR', 'HR_M', 'HAIR', 'HAIR', 'HR_D', 'BG_OFF'],
    ['HR_D', 'HAIR', 'HAIR', 'HAIR', 'HAIR', 'HAIR', 'HAIR', 'HAIR', 'HAIR', 'HAIR', 'HAIR', 'HAIR', 'HR_M', 'HAIR', 'HAIR', 'HR_D'],
    ['HR_D', 'HAIR', 'HAIR', 'HR_M', 'HAIR', 'HAIR', 'HAIR', 'HAIR', 'HAIR', 'HR_M', 'HAIR', 'HAIR', 'HAIR', 'HR_M', 'HAIR', 'HR_D'],
    ['HR_D', 'HAIR', 'HR_M', 'HAIR', 'HAIR', 'HR_M', 'SKIN', 'HAIR', 'HR_M', 'SKIN', 'HR_M', 'HAIR', 'HAIR', 'HR_M', 'HAIR', 'HR_D'],
    ['HR_D', 'HAIR', 'HR_M', 'HAIR', 'LASH', 'LASH', 'LASH', 'HAIR', 'SKIN', 'LASH', 'LASH', 'LASH', 'HAIR', 'HR_M', 'HAIR', 'HR_D'],
    ['HR_D', 'HAIR', 'HAIR', 'HAIR', 'EYEW', 'IRIS', 'IRIS', 'SKIN', 'SKIN', 'IRIS', 'IRIS', 'EYEW', 'HAIR', 'HAIR', 'HAIR', 'HR_D'],
    ['HR_D', 'HAIR', 'HAIR', 'HAIR', 'EYEW', 'EYEL', 'EYEL', 'SKIN', 'SKIN', 'EYEL', 'EYEL', 'EYEW', 'HAIR', 'HAIR', 'HAIR', 'HR_D'],
    ['BG_OFF', 'BG_OFF', 'HR_D', 'HAIR', 'HR_M', 'HR_M', 'HR_D', 'SHIRT_A', 'SHIRT_A', 'HR_D', 'HR_M', 'HR_M', 'HAIR', 'HR_D', 'BG_OFF', 'BG_OFF'],
    ['BG_OFF', 'BG_OFF', 'HR_D', 'HAIR', 'HR_M', 'DARK_BLK', 'COAT', 'TIE', 'TIE', 'COAT', 'DARK_BLK', 'HR_M', 'HAIR', 'HR_D', 'BG_OFF', 'BG_OFF'],
    ['BG_OFF', 'BG_OFF', 'HR_D', 'HAIR', 'DARK_BLK', 'COAT', 'COAT', 'SHIRT_W', 'SHIRT_W', 'COAT', 'COAT', 'DARK_BLK', 'HAIR', 'HR_D', 'BG_OFF', 'BG_OFF'],
    ['BG_OFF', 'BG_OFF', 'HR_D', 'DARK_BLK', 'SKIN', 'COAT', 'COAT', 'SHIRT_A', 'SHIRT_A', 'COAT', 'COAT', 'SKIN', 'DARK_BLK', 'HR_D', 'BG_OFF', 'BG_OFF'],
    ['BG_OFF', 'BG_OFF', 'BG_OFF', 'BG_OFF', 'BG_OFF', 'SOLE', 'PANTS', 'PANTS', 'PANTS', 'PANTS', 'SOLE', 'BG_OFF', 'BG_OFF', 'BG_OFF', 'BG_OFF', 'BG_OFF'],
    ['BG_OFF', 'BG_OFF', 'BG_OFF', 'BG_OFF', 'BG_OFF', 'BG_OFF', 'SOLE', 'SOLE', 'SOLE', 'SOLE', 'BG_OFF', 'BG_OFF', 'BG_OFF', 'BG_OFF', 'BG_OFF', 'BG_OFF'],
]

grid = [[SOURCE_PALETTE[role] for role in row] for row in grid_roles]

def format_frame(name, g):
    lines = [f'static const ColorRGB {name}[16][16] = {{']
    for row in g:
        row_str = '    {' + ''.join(f'ColorRGB({c[0]}, {c[1]}, {c[2]}), ' for c in row) + '},'
        lines.append(row_str)
    lines.append('};\n')
    return '\n'.join(lines)

def generate_header():
    content = '// Generated by scripts/update_kurisu_sprites.py; visual-role LED drive palette, not sRGB.\n'
    content += '#pragma once\n'
    content += '#include "display_types.h"\n\n'
    content += f'constexpr uint8_t KURISU_BRIGHTNESS_PERCENT = {DESK_PET_BRIGHTNESS_PERCENT};\n\n'
    led_grid = [[LED_PALETTE[role] for role in row] for row in grid_roles]
    for name in ('IDLE', 'BLINK', 'TALK1', 'TALK2'):
        content += format_frame(f'KURISU_FRAME_{name}', led_grid)
    return content


def generate_transfer_header():
    # IEC sRGB decoding, represented in 16-bit linear light. Quantize only
    # after brightness scaling; an 8-bit intermediate would crush dark pixels.
    values = []
    for value in range(256):
        encoded = value / 255.0
        linear = encoded / 12.92 if encoded <= 0.04045 else ((encoded + 0.055) / 1.055) ** 2.4
        values.append(round(linear * 65535))
    lines = [
        '// Generated by scripts/update_kurisu_sprites.py; IEC sRGB decoding.',
        '#pragma once', '#include <stdint.h>', '', 'namespace DisplayColor {',
        'constexpr uint16_t SRGB_TO_LINEAR[256] = {',
    ]
    for offset in range(0, 256, 16):
        lines.append('    ' + ', '.join(str(v) for v in values[offset:offset + 16]) + ',')
    lines += [
        '};', '',
        '// Ideal linear-light PWM reference, not a measured panel calibration.',
        'constexpr uint8_t SrgbToPwm(uint8_t encoded, uint8_t brightness) {',
        '    return static_cast<uint8_t>((static_cast<uint32_t>(SRGB_TO_LINEAR[encoded]) * brightness + 32767u) / 65535u);',
        '}', '}  // namespace DisplayColor', '',
    ]
    return '\n'.join(lines)


if __name__ == '__main__':
    target_dir = Path(__file__).resolve().parents[1] / 'firmware-s3/main/display'
    for name, content in (('kurisu_sprites.h', generate_header()), ('srgb_transfer.h', generate_transfer_header())):
        target_path = target_dir / name
        target_path.write_text(content, encoding='utf-8')
        print('Updated:', target_path)
