#include "audio_preferences.h"
#include "audio_sample_format.h"
#include "game_audio_stream.h"
#include "pcm_frame_writer.h"
#include "wifi_audio_power.h"
#include "pcm_tx_queue.h"
#include <algorithm>
#include <cassert>
#include <cstdio>
#include <cstring>
#include <optional>
#include <vector>
#include <memory>

static std::vector<uint8_t> Wire(uint8_t kind,const std::vector<uint8_t>& data) {
    std::vector<uint8_t> result={'K','A','P','1',kind,
        static_cast<uint8_t>(data.size()>>8),static_cast<uint8_t>(data.size())};
    result.insert(result.end(),data.begin(),data.end());return result;
}
static void TestPcmTxQueue() {
    using namespace pcm_transport;
    auto storage=std::make_unique<PcmTxQueue>();auto& q=*storage;
    std::vector<uint8_t> mic(480,17),marker={1,2,3,4},last={5,6};
    auto expected=Wire(2,mic);
    for(const auto& frame:{Wire(5,marker),Wire(2,last)})expected.insert(expected.end(),frame.begin(),frame.end());
    for(size_t cut=0;cut<expected.size();++cut) {
        assert(q.Enqueue(2,mic.data(),mic.size(),100));
        assert(q.Enqueue(5,marker.data(),marker.size(),100));
        assert(q.Enqueue(2,last.data(),last.size(),100));
        std::vector<uint8_t> wire;
        const auto first=q.Flush(101,[&](const uint8_t* p,size_t n){
            const size_t accepted=std::min(n,cut-wire.size());
            wire.insert(wire.end(),p,p+accepted);
            return TxWrite{accepted,accepted?TxState::Progress:TxState::Blocked};
        });
        assert(first==FlushResult::Pending && wire.size()==cut);
        assert(q.Flush(102,[&](const uint8_t* p,size_t n){
            wire.insert(wire.end(),p,p+n);return TxWrite{n,TxState::Progress};
        })==FlushResult::Idle);
        assert(wire==expected && q.DroppedSamples()==0);
    }
    const uint32_t before=q.DroppedSamples();
    for(size_t i=0;i<PcmTxQueue::kSlots-2;++i)assert(q.Enqueue(2,last.data(),2,200));
    assert(!q.Enqueue(2,last.data(),2,200));
    assert(q.DroppedSamples()==before+1);
    assert(q.Enqueue(5,marker.data(),4,200) && q.Enqueue(5,last.data(),2,200));
    assert(!q.Enqueue(5,last.data(),2,200));
    unsigned calls=0;
    while(q.Queued())q.Flush(201,[&](const uint8_t*,size_t n){++calls;return TxWrite{n,TxState::Progress};});
    assert(calls==PcmTxQueue::kSlots);

    auto blocked=[](const uint8_t*,size_t){return TxWrite{0,TxState::Blocked};};
    assert(q.Enqueue(2,last.data(),2,300));
    assert(q.Flush(300,blocked)==FlushResult::Pending);
    assert(q.Flush(1799,blocked)==FlushResult::Pending);
    assert(q.Flush(1801,[](const uint8_t*,size_t)->TxWrite{
        assert(false && "Expired data must not reach socket");return {0,TxState::Fault};
    })==FlushResult::Expired);
    q.Clear();
    assert(q.Enqueue(2,last.data(),2,UINT32_MAX-100));
    assert(q.Flush(50,blocked)==FlushResult::Pending); // Wrapped monotonic clock.
    assert(q.Flush(1501,blocked)==FlushResult::Expired);q.Clear();

    assert(!q.Enqueue(2,nullptr,2,0) && !q.Enqueue(2,last.data(),1,0));
    assert(!q.Enqueue(2,last.data(),2049,0) && !q.Enqueue(1,last.data(),2,0));
    assert(!q.Enqueue(5,last.data(),0,0) && q.Queued()==0);
    std::vector<uint8_t> maximum(2048,0xa7),wire;
    assert(q.Enqueue(2,maximum.data(),maximum.size(),0));
    calls=0;
    assert(q.Flush(1,[&](const uint8_t* p,size_t){
        wire.push_back(*p);++calls;return TxWrite{1,TxState::Progress};
    })==FlushResult::Pending && calls==8); // Bounded work per poll.
    q.Clear(); // Disconnected peer must not leak its partial frame to the next.
    wire.clear();assert(q.Enqueue(5,marker.data(),marker.size(),10));
    assert(q.Flush(11,[&](const uint8_t* p,size_t n){
        wire.insert(wire.end(),p,p+n);return TxWrite{n,TxState::Progress};
    })==FlushResult::Idle && wire==Wire(5,marker));

    assert(q.Enqueue(2,maximum.data(),maximum.size(),20));wire.clear();
    assert(q.Flush(21,[&](const uint8_t* p,size_t n){
        wire.insert(wire.end(),p,p+n);return TxWrite{n,TxState::Progress};
    })==FlushResult::Idle && wire==Wire(2,maximum));
    assert(q.Enqueue(5,marker.data(),4,30));
    assert(q.Flush(31,[](const uint8_t*,size_t){return TxWrite{0,TxState::Fault};})==FlushResult::Fault);
    q.Clear();assert(q.Enqueue(5,marker.data(),4,40));
    assert(q.Flush(41,[](const uint8_t*,size_t n){return TxWrite{n+1,TxState::Progress};})==FlushResult::Fault);
    q.Clear();assert(q.Enqueue(5,marker.data(),4,50));
    assert(q.Flush(51,[](const uint8_t*,size_t){return TxWrite{1,TxState::Blocked};})==FlushResult::Fault);
    q.Clear();
    std::printf("PASS: PCM queue %u partial/backpressure positions, control reserve, expiry, reset and bounded work; storage=%u bytes (host)\n",
        static_cast<unsigned>(expected.size()),static_cast<unsigned>(sizeof(PcmTxQueue)));
}

namespace {
wifi_ps_type_t wifi_policy=WIFI_PS_MIN_MODEM;
int wifi_get_error=ESP_OK,wifi_set_error=ESP_OK;
unsigned wifi_gets=0;
std::vector<wifi_ps_type_t> wifi_sets;
}
esp_err_t esp_wifi_get_ps(wifi_ps_type_t* policy) {
    ++wifi_gets;
    if(wifi_get_error!=ESP_OK)return wifi_get_error;
    *policy=wifi_policy;return ESP_OK;
}
esp_err_t esp_wifi_set_ps(wifi_ps_type_t policy) {
    wifi_sets.push_back(policy);
    if(wifi_set_error!=ESP_OK)return wifi_set_error;
    wifi_policy=policy;return ESP_OK;
}
static void TestWifiAudioPower() {
    for(auto initial:{WIFI_PS_MIN_MODEM,WIFI_PS_MAX_MODEM,WIFI_PS_NONE}) {
        wifi_policy=initial;wifi_sets.clear();wifi_gets=0;
        {
            pcm_transport::WifiAudioPowerSession session;
            assert(session.Activate()==ESP_OK && wifi_policy==WIFI_PS_NONE);
            assert(session.Activate()==ESP_OK && wifi_gets==1);
        }
        assert(wifi_policy==initial);
        if(initial==WIFI_PS_NONE)assert(wifi_sets.empty());
        else assert((wifi_sets==std::vector<wifi_ps_type_t>{WIFI_PS_NONE,initial}));
    }
    // A failed get/set must not pretend activation or restore an unknown mode.
    wifi_policy=WIFI_PS_MIN_MODEM;wifi_sets.clear();wifi_get_error=ESP_FAIL;
    {pcm_transport::WifiAudioPowerSession session;assert(session.Activate()==ESP_FAIL);}
    assert(wifi_sets.empty() && wifi_policy==WIFI_PS_MIN_MODEM);
    wifi_get_error=ESP_OK;wifi_set_error=ESP_FAIL;
    {pcm_transport::WifiAudioPowerSession session;assert(session.Activate()==ESP_FAIL);}
    assert(wifi_sets.size()==1 && wifi_policy==WIFI_PS_MIN_MODEM);
    wifi_set_error=ESP_OK;wifi_sets.clear();
    // Early return, e.g. failed authenticated hello, still restores policy.
    auto failed_hello=[] {
        pcm_transport::WifiAudioPowerSession session;
        assert(session.Activate()==ESP_OK);return false;
    };
    assert(!failed_hello() && wifi_policy==WIFI_PS_MIN_MODEM && wifi_sets.size()==2);
    wifi_sets.clear();
    {
        pcm_transport::WifiAudioPowerSession session;
        assert(session.Activate()==ESP_OK);
        wifi_set_error=ESP_FAIL;
    }
    assert(wifi_policy==WIFI_PS_NONE && wifi_sets.size()==2); // No retry/panic on restore failure.
    wifi_set_error=ESP_OK;wifi_policy=WIFI_PS_MIN_MODEM;
    std::puts("PASS: production audio Wi-Fi policy activation, failure and scope-exit restore (host stubs)");
}

static void TestPcmFraming() {
    std::vector<uint8_t> pcm(480);
    for (size_t i=0;i<pcm.size();++i) pcm[i]=static_cast<uint8_t>(i);
    std::vector<uint8_t> expected={'K','A','P','1',2,1,224};
    expected.insert(expected.end(),pcm.begin(),pcm.end());
    // Every possible header/payload failure position must invalidate the
    // stream once; continuing at the next header would corrupt its boundary.
    for (size_t stop=0;stop<expected.size();++stop) {
        std::vector<uint8_t> wire;
        unsigned disconnected=0;
        const bool ok=pcm_transport::WriteFrame(2,pcm.data(),pcm.size(),
            [&](const uint8_t* p,size_t n)->int {
                const size_t accepted=std::min(std::min(n,size_t{3}),stop-wire.size());
                wire.insert(wire.end(),p,p+accepted);
                return accepted?static_cast<int>(accepted):-1;
            },[&]{++disconnected;});
        assert(!ok && disconnected==1 && wire.size()==stop);
        assert(std::equal(wire.begin(),wire.end(),expected.begin()));
    }
    for (size_t chunk=1;chunk<=13;++chunk) {
        std::vector<uint8_t> wire;
        assert(pcm_transport::WriteFrame(2,pcm.data(),pcm.size(),
            [&](const uint8_t* p,size_t n)->int {
                const size_t accepted=std::min(n,chunk);
                wire.insert(wire.end(),p,p+accepted);
                return static_cast<int>(accepted);
            },[]{assert(false && "Fragmented successful writes must not disconnect");}));
        assert(wire==expected);
    }
    unsigned writes=0,disconnected=0;
    auto writer=[&](const uint8_t*,size_t)->int {++writes;return 0;};
    auto disconnect=[&]{++disconnected;};
    assert(!pcm_transport::WriteFrame(2,pcm.data(),0,writer,disconnect));
    assert(!pcm_transport::WriteFrame(2,pcm.data(),2049,writer,disconnect));
    assert(!pcm_transport::WriteFrame(2,nullptr,480,writer,disconnect));
    assert(writes==0 && disconnected==0);
    assert(!pcm_transport::WriteFrame(2,pcm.data(),480,writer,disconnect));
    assert(writes==1 && disconnected==1); // Busy/zero write cannot spin.
    std::puts("PASS: TCP PCM fragmented writes and 487 injected failure positions (host; no hardware)");
}

namespace {
std::optional<int32_t> stored, pending;
int open_error=ESP_OK, set_error=ESP_OK, commit_error=ESP_OK;
unsigned opens=0, closes=0, commits=0;
}
int nvs_open(const char* name,int mode,nvs_handle_t* handle) {
    assert(std::strcmp(name,"audio")==0);
    assert(mode==NVS_READONLY || mode==NVS_READWRITE);
    ++opens; if(open_error!=ESP_OK)return open_error; *handle=1;return ESP_OK;
}
int nvs_get_i32(nvs_handle_t handle,const char* key,int32_t* value) {
    assert(handle==1 && std::strcmp(key,"output_volume")==0);
    if(!stored)return ESP_ERR_NVS_NOT_FOUND;
    *value=*stored;return ESP_OK;
}
int nvs_set_i32(nvs_handle_t handle,const char* key,int32_t value) {
    assert(handle==1 && std::strcmp(key,"output_volume")==0);
    if(set_error!=ESP_OK)return set_error;
    pending=value;return ESP_OK;
}
int nvs_commit(nvs_handle_t handle) {
    assert(handle==1);++commits;
    if(commit_error!=ESP_OK)return commit_error;
    stored=pending;return ESP_OK;
}
void nvs_close(nvs_handle_t handle) { assert(handle==1);++closes;pending.reset(); }

int main() {
    TestPcmTxQueue();
    TestWifiAudioPower();
    TestPcmFraming();
    using namespace audio_preferences;
    const auto empty=Load(); assert(empty.value==70 && !empty.saved);
    assert(Save(60)==ESP_OK); assert(Load().value==60 && Load().saved);
    assert(Save(0)==ESP_OK); assert(Load().value==0 && Load().saved);
    const unsigned read_commits=commits;
    stored=200; const auto corrupt=Load();assert(corrupt.value==70 && !corrupt.saved);
    assert(commits==read_commits); // Reading bad values never erases/rewrites NVS.
    stored=40;set_error=ESP_FAIL;assert(Save(80)==ESP_FAIL && *stored==40);
    set_error=ESP_OK;commit_error=ESP_FAIL;assert(Save(80)==ESP_FAIL && *stored==40);
    commit_error=ESP_OK;open_error=ESP_FAIL;const unsigned close_before=closes;
    assert(Save(80)==ESP_FAIL && closes==close_before);
    assert(Load().value==70 && !Load().saved);
    open_error=ESP_OK;const unsigned open_before=opens;
    assert(Save(-1)==ESP_FAIL && Save(101)==ESP_FAIL && opens==open_before);
    assert(Save(80)==ESP_OK && Load().value==80);

    using namespace audio_pcm;
    assert(VolumeFactor(0)==0 && VolumeFactor(70)==32112 && VolumeFactor(100)==65536);
    int16_t input[]={INT16_MIN,-1,0,1,INT16_MAX};
    int32_t output[]={123,0,0,0,0,0,456};
    PackMono(input,5,VolumeFactor(100),output+1);
    assert(output[0]==123 && output[6]==456);
    assert(output[1]==INT32_MIN && output[2]==-65536 && output[3]==0);
    assert(output[4]==65536 && output[5]==2147418112);
    PackMono(input,5,0,output+1);for(unsigned i=1;i<6;++i)assert(output[i]==0);
    PackMono(input,5,70000,output+1);assert(output[1]==INT32_MIN && output[5]==INT32_MAX);
    using namespace arcade;
    assert(GameWriteFromBytes(160,640,AudioWriteState::Ready,kI2sBytesPerSample).samples==160);
    assert(GameWriteFromBytes(160,320,AudioWriteState::Busy,kI2sBytesPerSample).samples==80);
    assert(GameWriteFromBytes(160,641,AudioWriteState::Ready,kI2sBytesPerSample).state==AudioWriteState::Fault);
    assert(GameWriteFromBytes(160,644,AudioWriteState::Ready,kI2sBytesPerSample).state==AudioWriteState::Fault);
    assert(GameWriteFromBytes(160,640,AudioWriteState::Busy).samples==80); // Old stereo contract remains explicit.
    // Replay a real sound through DMA-busy/partial mono writes. Each accepted
    // sample must appear exactly once in the original synthesized waveform.
    SoundBus bus;
    assert(bus.Emit(Sound::Win,35));
    SoundEvent expected{Sound::Win,35,0,bus.Generation(),0};
    GameAudioStream stream(bus);
    std::vector<int32_t> accepted;
    unsigned calls=0;
    for(unsigned now=0;now<250;++now) {
        stream.Poll(now,[&](const int16_t* pcm,unsigned count) {
            if(++calls<=2)return AudioWriteResult{0,AudioWriteState::Busy};
            const unsigned n=std::min(80u,count);
            int32_t packed[80];PackMono(pcm,n,VolumeFactor(70),packed);
            accepted.insert(accepted.end(),packed,packed+n);
            return GameWriteFromBytes(count,n*kI2sBytesPerSample,
                n<count?AudioWriteState::Busy:AudioWriteState::Ready,kI2sBytesPerSample);
        });
    }
    assert(bus.played==1 && bus.busy>0 && bus.short_writes>0 && bus.faults==0);
    assert(accepted.size()==ToneFor(expected).duration_ms*16);
    for(unsigned i=0;i<accepted.size();++i)
        assert(accepted[i]==int64_t(SoundSample(expected,i,bus.Volume()))*VolumeFactor(70));
    std::puts("PASS: production mono packing, partial-write accounting and NVS volume contracts (host stubs; no hardware)");
}
