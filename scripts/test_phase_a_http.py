"""Exercise real HTTP routes ONLY on an explicitly simulated service; no hardware."""
import argparse
import json
import urllib.request
import urllib.error
import asyncio
import time
from pathlib import Path


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--url',required=True)
    args=parser.parse_args()
    base=args.url.rstrip('/')
    http=urllib.request.build_opener(urllib.request.ProxyHandler({}))
    status=json.load(http.open(base+'/api/status',timeout=4))
    if status.get('simulated') is not True:
        raise RuntimeError('Refusing to run against a non-simulated service')
    def post(data):
        req=urllib.request.Request(base+'/api/arcade',data=json.dumps(data).encode(),headers={'Content-Type':'application/json'})
        return json.load(http.open(req,timeout=4))
    registry=json.loads((Path(__file__).resolve().parents[1]/'pc-agent-vision/arcade/registered_games.json').read_text())
    for gid in (entry['id'] for entry in registry):
        result=post({'action':'select','game_id':gid})
        assert result['status']=='ok' and result['simulated'] and result['game_status']['game_id']==gid
        if gid in (17,35,57,58,81,85,92,95,98):
            configured=post({'action':'config','sound_enabled':True,'sound_volume':20,'difficulty':2})
            assert configured['game_status']['difficulty_supported'] is True
            assert configured['game_status']['difficulty']==2
            post({'action':'start'})
            rejected=post({'action':'config','sound_enabled':False,'sound_volume':90,'difficulty':0})
            assert rejected['status']=='error'
            observed=post({'action':'status'})['game_status']
            assert observed['difficulty']==2 and observed['sound_enabled'] is True and observed['sound_volume']==20
            post({'action':'reset'})
            assert post({'action':'config','sound_enabled':False,'sound_volume':15,'difficulty':0})['game_status']['difficulty']==0
        if gid==20:
            assert post({'action':'players','count':2})['game_status']['player_count']==2
            post({'action':'start'});post({'action':'pause'})
            assert post({'action':'players','count':1})['game_status']['state']==2
            assert post({'action':'resume'})['game_status']['player_count']==1
        for action in ('start','pause','resume','reset'):
            assert post({'action':action})['status']=='ok', (gid,action)
        assert post({'action':'input','down':18,'pressed':16})['status']=='ok'
        assert post({'action':'input','down':2,'pressed':0})['status']=='ok'
        frame=json.load(http.open(base+'/api/arcade/frame',timeout=4))
        assert frame['simulated'] and frame['source']=='simulator' and len(frame['hex'])==1536
        assert post({'action':'exit'})['status']=='ok'
        time.sleep(.08) # Stay below the production HTTP rate budget.
        print(f'Target {gid:03}: select/start/pause/resume/reset/multi-key/frame/exit passed (SIMULATOR)')
    for gid in (-255,257,1.5,True,'1',100):
        try: post({'action':'select','game_id':gid})
        except urllib.error.HTTPError as error: assert error.code==400
        else: raise AssertionError(f'Invalid ID accepted: {gid!r}')
    print(f'Real HTTP integration passed for {len(registry)} registered games; HARDWARE NOT TESTED')
    try: post({'action':'config','sound_enabled':True,'sound_volume':25,'difficulty':None})
    except urllib.error.HTTPError as error: assert error.code==400
    else: raise AssertionError('Explicit null difficulty accepted')
    async def websocket_rate_check():
        import aiohttp
        async with aiohttp.ClientSession() as session:
            async with session.ws_connect(base+'/ws') as channel:
                await channel.receive()
                async def send():
                    try:
                        for _ in range(600):
                            await channel.send_json({'action':'ping'})
                    except (ConnectionError,RuntimeError):
                        pass
                sender=asyncio.create_task(send())
                try:
                    while True:
                        message=await asyncio.wait_for(channel.receive(),3)
                        if message.type in (aiohttp.WSMsgType.CLOSE,aiohttp.WSMsgType.CLOSED,aiohttp.WSMsgType.CLOSING):
                            break
                    assert channel.close_code==1008,channel.close_code
                finally:
                    await sender
        print('Production WebSocket rate limit: closed excessive messages with code 1008 (SIMULATOR)')
    asyncio.run(websocket_rate_check())


if __name__=='__main__': main()
