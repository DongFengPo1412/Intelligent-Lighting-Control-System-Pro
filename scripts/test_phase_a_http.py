"""Exercise real HTTP routes ONLY on an explicitly simulated service; no hardware."""
import argparse
import json
import urllib.request
import urllib.error
import asyncio


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
    for gid in (1,9,10,20,21,26,33,34,38,41,54,74,97):
        result=post({'action':'select','game_id':gid})
        assert result['status']=='ok' and result['simulated'] and result['game_status']['game_id']==gid
        for action in ('start','pause','resume','reset'):
            assert post({'action':action})['status']=='ok', (gid,action)
        assert post({'action':'input','down':18,'pressed':16})['status']=='ok'
        assert post({'action':'input','down':2,'pressed':0})['status']=='ok'
        frame=json.load(http.open(base+'/api/arcade/frame',timeout=4))
        assert frame['simulated'] and frame['source']=='simulator' and len(frame['hex'])==1536
        assert post({'action':'exit'})['status']=='ok'
        print(f'Target {gid:03}: select/start/pause/resume/reset/multi-key/frame/exit passed (SIMULATOR)')
    for gid in (-255,257,1.5,True,'1'):
        try: post({'action':'select','game_id':gid})
        except urllib.error.HTTPError as error: assert error.code==400
        else: raise AssertionError(f'Invalid ID accepted: {gid!r}')
    print('Real HTTP integration passed for 13 registered games; HARDWARE NOT TESTED')
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
