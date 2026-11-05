"""Start the same paired-Wi-Fi voice lifecycle as the PC control application.

Models, ready sound, wake greetings and continuous conversation have one owner;
this entry point does not maintain a second USB-only startup/reconnect loop.
All web_server command-line options remain available (including --simulate).
"""

import os
from pathlib import Path
import runpy
import sys


def main():
    agent_dir = Path(__file__).resolve().parents[1] / 'pc-agent-vision'
    sys.path.insert(0, str(agent_dir))
    os.environ.setdefault('KURISU_AUDIO_TRANSPORT', 'wifi')
    runpy.run_module('web_server', run_name='__main__')


if __name__ == '__main__':
    main()
