"""No serial connection, UDP socket, microphone, model or audio output."""
import contextlib
import ast
import io
from pathlib import Path
import sys
import unittest
import types
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).parents[1]/'pc-agent-vision'))
from light_controller import LightController
import light_tools
from semantic_control import validate_plan


class Tests(unittest.TestCase):
    def setUp(self):
        self.client=LightController.__new__(LightController)
        self.commands=[]
        self.client.send_json=lambda cmd:self.commands.append(cmd) or True
        self.output=contextlib.redirect_stdout(io.StringIO());self.output.__enter__()

    def tearDown(self):self.output.__exit__(None,None,None)

    def test_direct_mode_set(self):
        for mode in list(range(18))+list(range(19,25))+list(range(26,32)):
            self.assertTrue(self.client.set_mode(mode))
        self.assertEqual(len(self.commands),30)

    def test_countdown_requires_its_parameterized_command(self):
        with self.assertRaises(ValueError):self.client.set_mode(25)
        self.assertEqual(self.commands,[])
        self.assertTrue(self.client.countdown(60))
        self.assertEqual(self.commands,[{'cmd':'countdown','seconds':60}])

    def test_invalid_modes_never_send(self):
        for mode in (18,-1,32,True,1.5,'1'):
            with self.assertRaises(ValueError):self.client.set_mode(mode)
        self.assertEqual(self.commands,[])

    def test_invalid_timer_never_sends(self):
        for seconds in (0,-1,86401,True,1.5,'60'):
            with self.assertRaises(ValueError):self.client.countdown(seconds)
        self.assertEqual(self.commands,[])

    def test_timer_alias_cannot_select_an_uninitialized_mode(self):
        for name in ('timer','countdown','hourglass','sand'):
            with self.assertRaises(ValueError):self.client.set_theme(name)
        self.assertEqual(self.commands,[])

    def test_tool_reports_rejected_mode(self):
        with patch.object(light_tools,'get_light_controller',return_value=self.client):
            result=light_tools.execute_tool('set_light_mode',{'mode':25})
        self.assertNotEqual(result['status'],'success')
        self.assertEqual(self.commands,[])

    def test_semantic_timer_uses_duration(self):
        good={'kind':'control','actions':[{'tool':'start_countdown','value':60}]}
        self.assertEqual(validate_plan(good),good)
        with self.assertRaises(ValueError):
            validate_plan({'kind':'control','actions':[{'tool':'set_light_mode','value':25}]})

    def test_control_readiness_does_not_require_usb_audio(self):
        import wifi_gateway
        self.client.ser=None
        with patch.object(wifi_gateway,'get_wifi_gateway',return_value=types.SimpleNamespace(is_online=lambda:True)):
            self.assertTrue(self.client.control_connected)

    def test_spectrum_start_failure_releases_capture(self):
        source=Path(__file__).parents[1]/'pc-agent-vision/audio_visualizer.py'
        cls=next(n for n in ast.parse(source.read_text(encoding='utf-8')).body if isinstance(n,ast.ClassDef))
        closed=[]
        stream=types.SimpleNamespace(stop_stream=lambda:closed.append('stop'),close=lambda:closed.append('close'))
        pa=types.SimpleNamespace(open=lambda **kw:stream,terminate=lambda:closed.append('terminate'))
        scope={'pyaudio':types.SimpleNamespace(PyAudio=lambda:pa,paInt16=8),'print':lambda *a:None}
        exec(compile(ast.Module(body=[cls],type_ignores=[]),str(source),'exec'),scope)
        v=scope['AudioVisualizer'].__new__(scope['AudioVisualizer']);v.sample_rate=16000;v.chunk_size=512
        v.controller=types.SimpleNamespace(set_mode=lambda _:False,control_connected=False)
        with self.assertRaises(ConnectionError):v.start_stream()
        self.assertEqual(closed,['stop','close','terminate'])


if __name__=='__main__':unittest.main()
