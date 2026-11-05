"""Compile the actual legacy GameEngine with an external clock/display adapter."""
import argparse
import os
from pathlib import Path
import shutil
import subprocess
from build_offline_renderer import HAL

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--work-dir', required=True)
    args = parser.parse_args()
    work = Path(args.work_dir).resolve()
    if work == ROOT or ROOT in work.parents:
        raise ValueError('Use an external task cache')
    work.mkdir(parents=True, exist_ok=True)
    display = ROOT / 'firmware-s3/main/display'
    for name in ['game_engine.cc', 'game_engine.h', 'display_types.h', 'matrix_layout.h', 'font_5x3.h']:
        shutil.copy2(display / name, work / name)
    (work / 'display_hal.h').write_text(HAL, encoding='utf-8')
    (work / 'esp_random.h').write_text('#pragma once\n#include <stdint.h>\nuint32_t esp_random();\n')
    (work / 'esp_timer.h').write_text('#pragma once\n#include <stdint.h>\nint64_t esp_timer_get_time();\n')
    exe = work / ('legacy-snake.exe' if os.name == 'nt' else 'legacy-snake')
    env = dict(os.environ)
    sources = [ROOT / 'tests/legacy_snake_host.cpp', work / 'game_engine.cc']
    if os.name == 'nt':
        vswhere = Path(os.environ.get('ProgramFiles(x86)', 'C:/Program Files (x86)')) / 'Microsoft Visual Studio/Installer/vswhere.exe'
        installation = subprocess.check_output([str(vswhere), '-latest', '-products', '*', '-requires', 'Microsoft.VisualStudio.Component.VC.Tools.x86.x64', '-property', 'installationPath'], text=True).strip()
        vcvars = Path(installation) / 'VC/Auxiliary/Build/vcvars64.bat'
        for line in subprocess.check_output(f'cmd.exe /d /s /c ""{vcvars}" >nul && set"', text=True).splitlines():
            if '=' in line:
                key, value = line.split('=', 1)
                if key:
                    env[key] = value
        compiler = shutil.which('cl.exe', path=env.get('Path', env.get('PATH', '')))
        if not compiler:
            raise RuntimeError('Visual Studio C++ compiler not found')
        command = [compiler, '/nologo', '/std:c++17', '/EHsc', '/utf-8', '/D_USE_MATH_DEFINES', f'/I{work}', *sources, f'/Fe{exe}']
    else:
        command = [os.environ.get('CXX', 'c++'), '-std=c++17', f'-I{work}', *sources, '-o', exe]
    subprocess.run([str(x) for x in command], cwd=work, env=env, check=True)
    subprocess.run([str(exe)], cwd=work, env=env, check=True)


if __name__ == '__main__':
    main()
