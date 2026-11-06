"""Compile production audio helpers with injected NVS; no board or sound.

Usage: python scripts/test_audio_alignment_native.py --work-dir ABS_CACHE_DIR
"""
import argparse
import os
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--work-dir', required=True)
    args = parser.parse_args()
    work = Path(args.work_dir).resolve()
    if work == ROOT or ROOT in work.parents:
        raise ValueError('Build outputs must be outside the source repository')
    work.mkdir(parents=True, exist_ok=True)
    includes = [ROOT/'tests/phase_a_stubs', ROOT/'firmware-s3/main/audio', ROOT/'firmware-s3/main/protocol',
                ROOT/'firmware-s3/main/display/arcade']
    source = ROOT/'tests/audio_alignment_native_test.cpp'
    env = dict(os.environ)
    executable = work/('audio-alignment.exe' if os.name == 'nt' else 'audio-alignment')
    if os.name == 'nt':
        vswhere = Path(os.environ.get('ProgramFiles(x86)', 'C:/Program Files (x86)'))/'Microsoft Visual Studio/Installer/vswhere.exe'
        installation = subprocess.check_output([str(vswhere), '-latest', '-products', '*', '-requires',
            'Microsoft.VisualStudio.Component.VC.Tools.x86.x64', '-property', 'installationPath'], text=True).strip()
        vcvars = Path(installation)/'VC/Auxiliary/Build/vcvars64.bat'
        values = subprocess.check_output(f'cmd.exe /d /s /c ""{vcvars}" >nul && set"', text=True)
        for line in values.splitlines():
            if '=' in line and line.split('=', 1)[0]:
                key, value = line.split('=', 1); env[key] = value
        compiler = shutil.which('cl.exe', path=env.get('Path', env.get('PATH', '')))
        if not compiler: raise RuntimeError('Visual Studio C++ compiler not found')
        command = [compiler, '/nologo', '/std:c++17', '/EHsc', '/utf-8', '/W3', '/WX',
                   *[f'/I{x}' for x in includes], str(source), f'/Fe{executable}']
    else:
        command = [os.environ.get('CXX', 'c++'), '-std=c++17', '-Wall', '-Wextra', '-Werror',
                   *[f'-I{x}' for x in includes], str(source), '-o', str(executable)]
    subprocess.run(command, cwd=work, env=env, check=True)
    subprocess.run([str(executable)], cwd=work, env=env, check=True)


if __name__ == '__main__': main()
