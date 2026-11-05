"""Formal compatibility adapter contracts. Isolated software, no board/camera/audio."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'pc-agent-vision'))
import unittest
from arcade_runner import ArcadeSession
from arcade.base_cartridge import KEY_RIGHT,KEY_UP

class ClosureTests(unittest.TestCase):
    def test_legacy_inputs_never_select_wrong_card_or_launch_second_engine(self):
        class Controller:port='SIMULATION'
        session=ArcadeSession(Controller())
        session.legacy_control(33,'start')
        self.assertEqual(session.legacy_control(41,'pulse','up')['error'],'cartridge_not_selected')
        self.assertEqual(session.status['game_id'],33)
        self.assertEqual(session.legacy_control(33,'pulse','up')['status'],'ok')
        session.legacy_control(41,'start')
        self.assertEqual(session.legacy_control(33,'key','left')['error'],'cartridge_not_selected')
        self.assertEqual(session.status['game_id'],41)
        self.assertEqual(session.legacy_control(41,'pause')['game_status']['state'],2)
        self.assertEqual(session.legacy_control(41,'resume')['game_status']['state'],1)
        self.assertEqual(session.legacy_control(41,'reset')['status'],'ok')

    def test_legacy_mario_start_uses_same_session_and_has_no_hidden_fallback(self):
        class Offline:
            port='FAKE';control_connected=False
        session=ArcadeSession(Offline())
        self.assertEqual(session.legacy_control(1,'start')['error'],'device_offline')
        self.assertFalse(session.simulated_mode)
        class Controller:port='SIMULATION'
        session=ArcadeSession(Controller())
        self.assertEqual(session.legacy_control(1,'start')['source'],'simulator')
        self.assertEqual(session.status['game_id'],1)
        self.assertIs(session.current_cartridge,session.cartridges[1])

if __name__=='__main__':unittest.main()
