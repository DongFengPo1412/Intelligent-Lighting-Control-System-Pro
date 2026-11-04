"""Real loopback HTTP/WS/UDP integration; fake board, no physical devices."""
import asyncio
from collections import Counter
import json
import os
from pathlib import Path
import socket
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'pc-agent-vision'))
from aiohttp import web, WSServerHandshakeError
from aiohttp.test_utils import TestClient, TestServer
from access_control import AccessPolicy, access_middleware, pair
from wifi_gateway import WiFiGateway
from arcade_runner import ArcadeSession


class AccessTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.token='a'*43
        self.policy=AccessPolicy(self.token)
        self.touches=0
        app=web.Application(middlewares=[access_middleware]);app['access_policy']=self.policy
        async def controlled(request):
            self.touches+=1
            return web.json_response({'status':'ok'})
        async def ws(request):
            channel=web.WebSocketResponse();await channel.prepare(request)
            await channel.send_str('authorized')
            async for _ in channel: pass
            return channel
        app.router.add_post('/api/pair',pair)
        app.router.add_route('*','/api/control',controlled)
        app.router.add_post('/mcp',controlled)
        app.router.add_post('/api/pro/documents',controlled)
        app.router.add_get('/xiaozhi/v1/',controlled)
        app.router.add_get('/ws',ws)
        self.client=TestClient(TestServer(app));await self.client.start_server()

    async def asyncTearDown(self):
        await self.client.close()

    async def test_remote_http_mcp_and_websocket_require_token(self):
        with patch.object(self.policy,'local',return_value=False):
            for path in ['/api/control','/mcp']:
                response=await self.client.post(path,json={})
                self.assertEqual(response.status,401)
            with self.assertRaises(WSServerHandshakeError) as error:
                await self.client.ws_connect('/ws')
            self.assertEqual(error.exception.status,401);self.assertEqual(self.touches,0)
            response=await self.client.post('/api/control',json={},headers={'Authorization':'Bearer '+self.token})
            self.assertEqual(response.status,200)
            channel=await self.client.ws_connect('/ws',headers={'Authorization':'Bearer '+self.token})
            self.assertEqual((await channel.receive()).data,'authorized');await channel.close()

    async def test_host_origin_and_preflight_fail_closed(self):
        denied=await self.client.post('/api/control',headers={'Origin':'https://evil.example','Authorization':'Bearer '+self.token})
        self.assertEqual(denied.status,403)
        rebound=await self.client.post('/api/control',headers={'Host':'evil.example'})
        self.assertEqual(rebound.status,401)
        null=await self.client.post('/api/control',headers={'Origin':'null'})
        self.assertEqual(null.status,403)
        cross_site=await self.client.get('/api/control',headers={'Sec-Fetch-Site':'cross-site'})
        self.assertEqual(cross_site.status,403)
        bad=await self.client.options('/api/control',headers={'Origin':'https://evil.example'})
        self.assertEqual(bad.status,403);self.assertNotIn('Access-Control-Allow-Origin',bad.headers)
        origin=str(self.client.make_url('/')).rstrip('/')
        good=await self.client.options('/api/control',headers={'Origin':origin})
        self.assertEqual(good.status,204);self.assertEqual(good.headers['Access-Control-Allow-Origin'],origin)

    async def test_loopback_scripts_still_work_and_pairing_sets_session(self):
        self.assertEqual((await self.client.post('/api/control',json={})).status,200)
        response=await self.client.post('/api/pair',headers={'Authorization':'Bearer '+self.token})
        self.assertEqual(response.status,200)
        cookie=response.cookies['kurisu_session']
        self.assertTrue(cookie['httponly']);self.assertEqual(cookie['samesite'],'Strict')
        with patch.object(self.policy,'local',return_value=False):
            response=await self.client.post('/api/control',headers={'Cookie':'kurisu_session='+self.token})
            self.assertEqual(response.status,200)

    async def test_size_and_rate_limits_include_chunked_requests(self):
        large=await self.client.post('/api/control',data=b'x'*65537)
        self.assertEqual(large.status,413)
        async def chunks():
            yield b'x'*40000;yield b'y'*40000
        large=await self.client.post('/api/control',data=chunks())
        self.assertEqual(large.status,413)
        with patch.object(self.policy,'allow_rate',return_value=False):
            self.assertEqual((await self.client.post('/api/control')).status,429)

    async def test_optional_xiaozhi_credential_is_scoped_to_its_adapter(self):
        self.policy.xiaozhi_token='z'*40
        headers={'Authorization':'Bearer '+self.policy.xiaozhi_token}
        with patch.object(self.policy,'local',return_value=False):
            self.assertEqual((await self.client.get('/xiaozhi/v1/',headers=headers)).status,200)
            self.assertEqual((await self.client.post('/api/control',headers=headers)).status,401)

    async def test_document_limit_preserves_existing_100k_character_ingestion(self):
        response=await self.client.post('/api/pro/documents',json={'text':'实验资料'*25000})
        self.assertEqual(response.status,200)


class UdpIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(dir=os.environ.get('KURISU_TEST_TMP'))
        self.server=socket.socket(socket.AF_INET,socket.SOCK_DGRAM);self.server.bind(('127.0.0.1',0));self.server.settimeout(.1)
        self.running=True;self.wire=[];self.executions=Counter();self.drop=True
        self.key='a'*64;self.boot='b'*32;self.cache={}
        self.worker=threading.Thread(target=self.serve,daemon=True);self.worker.start()
        gateway=WiFiGateway.__new__(WiFiGateway)
        gateway.sock=socket.socket(socket.AF_INET,socket.SOCK_DGRAM);gateway.sock.bind(('127.0.0.1',0));gateway.sock.settimeout(.1)
        gateway.port=self.server.getsockname()[1];gateway.is_running=True
        gateway.control_token=self.key;gateway.boot_id=None;gateway.client_id='c'*32;gateway._sequence=1
        gateway.board_sta_ip='127.0.0.1';gateway.board_ap_ip='192.168.4.1';gateway.last_seen=0;gateway.last_mode=None
        gateway.last_result={};gateway._pending={};gateway._pending_lock=threading.Lock();gateway._send_lock=threading.RLock()
        gateway._state_path=Path(self.temp.name)/'device-state.json'
        gateway._receiver=threading.Thread(target=gateway._receiver_loop,daemon=True);gateway._receiver.start()
        self.gateway=gateway

    def tearDown(self):
        self.gateway.close();self.running=False;self.server.close()
        self.worker.join(1);self.gateway._receiver.join(1);self.temp.cleanup()

    def serve(self):
        while self.running:
            try: raw,addr=self.server.recvfrom(4096)
            except socket.timeout: continue
            except OSError: return
            value=json.loads(raw);rid=value['request_id']
            if 'command' not in value:
                reply={'request_id':rid,'status':'error','error':'pairing_required','boot_id':self.boot}
            elif value.get('token')!=self.key:
                reply={'request_id':rid,'status':'error','error':'pairing_required'}
            else:
                self.wire.append(raw)
                if rid not in self.cache:
                    self.executions[rid]+=1
                    self.cache[rid]={'request_id':rid,'status':'ok','pixels':'ab'*768,'frame_id':1}
                    # Wrong IDs and malformed packets must never complete the request.
                    self.server.sendto(b'{bad json',addr)
                    self.server.sendto(b'{"request_id":["unhashable"],"status":"ok"}',addr)
                    self.server.sendto(json.dumps({'request_id':rid,'status':'ok','mode':[]}).encode(),addr)
                    self.server.sendto(b'{"request_id":"wrong","status":"ok"}',addr)
                    if self.drop:self.drop=False;continue
                reply=self.cache[rid]
            self.server.sendto(json.dumps(reply).encode(),addr)

    def test_lost_ack_retry_is_identical_and_full_frame_is_received(self):
        self.assertTrue(self.gateway.send_command('{"cmd":"frame"}',timeout=.08,retries=1))
        self.assertEqual(len(self.gateway.last_result['pixels']),1536)
        self.assertEqual(self.wire[0],self.wire[1]);self.assertEqual(sum(self.executions.values()),1)
        sent=json.loads(self.wire[0]);self.assertEqual(sent['token'],self.key);self.assertEqual(sent['boot_id'],self.boot)
        self.assertTrue(self.gateway.is_online());self.assertFalse(self.gateway._pending)

    def test_wrong_credentials_do_not_report_online_or_fall_back(self):
        self.gateway.control_token='d'*64
        self.assertFalse(self.gateway.send_command('{"cmd":"arcade","action":"start"}',timeout=.1,retries=0))
        self.assertEqual(self.gateway.last_result['error'],'pairing_required');self.assertFalse(self.gateway.is_online())
        self.assertFalse(self.executions)


class ArcadeFailureTests(unittest.TestCase):
    def test_all_registered_cartridges_accept_protocol_masks_after_reset(self):
        for game_id,cart in ArcadeSession().cartridges.items():
            with self.subTest(game_id=game_id):
                cart.init();cart.start();cart.pause();cart.resume();cart.reset()
                cart.update(0.,18,16)
                self.assertEqual(len(cart.render()),768)

    def test_exit_and_frame_failure_are_not_success_or_implicit_simulation(self):
        class Controller:
            port='FAKE';control_connected=True
            def command_result(self,payload): return {'status':'error','error':'hardware_nack'}
        session=ArcadeSession(Controller())
        session.select_game(33,force_simulation=True)
        session.simulated_mode=False
        self.assertEqual(session.stop()['status'],'error')
        frame=session.get_frame();self.assertEqual(frame['status'],'error');self.assertFalse(frame['simulated']);self.assertNotEqual(frame['source'],'simulator')

    def test_invalid_masks_and_castable_ids_are_rejected(self):
        session=ArcadeSession(None)
        for game_id in [True,'1',1.5,257,-255]:
            self.assertEqual(session.select_game(game_id)['error'],'invalid_game_id')
        for masks in [(True,0),(-1,0),(0,256),(0,'16')]:
            self.assertEqual(session.input_state(*masks)['error'],'invalid_input')


if __name__=='__main__': unittest.main()
