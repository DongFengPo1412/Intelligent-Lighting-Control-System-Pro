#include "audio_preferences.h"
#include "audio_sample_format.h"
#include "game_audio_stream.h"
#include "pcm_frame_writer.h"
#include <algorithm>
#include <cassert>
#include <cstdio>
#include <cstring>
#include <optional>
#include <vector>

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
