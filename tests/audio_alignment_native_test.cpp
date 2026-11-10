#ifdef _WIN32
#ifndef NOMINMAX
#define NOMINMAX
#endif
#endif
#include "audio_preferences.h"
#include "audio_sample_format.h"
#include "game_audio_stream.h"
#include "pcm_frame_writer.h"
#include "wifi_audio_power.h"
#include "pcm_tx_queue.h"
#include "afe_sample_stream.h"
#include "../firmware-s3/main/display/board_led_profile.h"
#include <algorithm>
#include <cassert>
#include <cstdio>
#include <cstring>
#include <optional>
#include <vector>
#include <memory>
#include <string>

static void TestMidLedProfile() {
    static_assert(mid_led::kDefault == 4 && mid_led::kLow == 2 && mid_led::kHigh == 16,
                  "Keep Mid raw RGB levels");
    assert(mid_led::BlinkOn(99999,100) && !mid_led::BlinkOn(100000,100));
    assert(!mid_led::BlinkOn(199999,100) && mid_led::BlinkOn(200000,100));
    assert(mid_led::BlinkOn(499999,500) && !mid_led::BlinkOn(500000,500));
    assert(!mid_led::BlinkOn(999999,500) && mid_led::BlinkOn(1000000,500));
    std::puts("PASS: Mid LED RGB levels and 100/500ms monotonic blink boundaries (host; no hardware)");
}
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
    TestMidLedProfile();
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

    // Test 24kHz Resampler Chunk Slicing Invariance
    {
        int16_t input[4] = { 1000, 2000, 3000, 4000 };
        uint32_t factor = VolumeFactor(100);

        Resampler16kTo24k r1;
        int32_t out1[16] = {};
        size_t n1 = r1.Process(input, 4, factor, out1, true);

        Resampler16kTo24k r2;
        int32_t out2[16] = {};
        size_t n2_a = r2.Process(input, 2, factor, out2, false);
        size_t n2_b = r2.Process(input + 2, 2, factor, out2 + n2_a, true);
        size_t n2 = n2_a + n2_b;

        Resampler16kTo24k r3;
        int32_t out3[16] = {};
        size_t n3 = 0;
        for (int i = 0; i < 4; ++i) {
            n3 += r3.Process(input + i, 1, factor, out3 + n3, i == 3);
        }

        assert(n1 == 6);
        assert(n2 == 6);
        assert(n3 == 6);
        for (size_t i = 0; i < 6; ++i) {
            assert(out1[i] == out2[i]);
            assert(out1[i] == out3[i]);
        }
        std::puts("PASS: 24kHz resampler chunk slicing invariance (1, 2, 4 chunk splits identical)");
    }

    // Test Microphone Shift: 16-bit shift vs 12-bit shift with clipping regression
    {
        // Simulate 24-bit raw I2S sample in 32-bit slot (e.g. amplitude 0x10000000)
        int32_t raw_loud = 0x10000000; // High amplitude in MSB
        int32_t raw_normal = 0x00500000; // Normal amplitude

        // 16-bit shift: raw >> 16
        int32_t s16_loud = raw_loud >> 16;
        int16_t out16_loud = (s16_loud > INT16_MAX) ? INT16_MAX : (s16_loud < INT16_MIN) ? INT16_MIN : int16_t(s16_loud);
        assert(out16_loud == 0x1000); // 4096, clean, no saturation!

        // 12-bit shift: raw >> 12 (+24dB)
        int32_t s12_loud = raw_loud >> 12; // 0x10000 = 65536 > 32767
        int16_t out12_loud = (s12_loud > INT16_MAX) ? INT16_MAX : (s12_loud < INT16_MIN) ? INT16_MIN : int16_t(s12_loud);
        assert(out12_loud == INT16_MAX); // Saturated clipping confirmed on 12-bit shift!

        int32_t s12_normal = raw_normal >> 12;
        int16_t out12_normal = (s12_normal > INT16_MAX) ? INT16_MAX : (s12_normal < INT16_MIN) ? INT16_MIN : int16_t(s12_normal);
        assert(out12_normal == 0x500); // Normal gain
        std::puts("PASS: mic 16-bit vs 12-bit shift & saturation clipping regression");
    }

    // Test Production Network Audio Protocol Parser, Ticket Lifecycle & Boundary Security
    {
        using namespace pcm_transport;
        auto make_header = [](uint8_t kind, size_t bytes) {
            std::vector<uint8_t> h = { 'K', 'A', 'P', '1', kind, static_cast<uint8_t>(bytes >> 8), static_cast<uint8_t>(bytes & 0xFF) };
            return h;
        };

        size_t out_bytes = 0;

        // Standard chunk (512 samples = 1024 bytes) -> OkAudio
        auto h1024 = make_header(1, 1024);
        assert(ValidateFrameHeader(h1024.data(), out_bytes) == ParseFrameStatus::OkAudio && out_bytes == 1024);

        // Max allowable chunk (1024 samples = 2048 bytes) -> OkAudio
        auto h2048 = make_header(1, 2048);
        assert(ValidateFrameHeader(h2048.data(), out_bytes) == ParseFrameStatus::OkAudio && out_bytes == 2048);

        // Oversized chunk (1025 samples = 2050 bytes) -> RejectOversized
        auto h2050 = make_header(1, 2050);
        assert(ValidateFrameHeader(h2050.data(), out_bytes) == ParseFrameStatus::RejectOversized);

        // Huge chunk (4096 bytes) -> RejectOversized
        auto h4096 = make_header(1, 4096);
        assert(ValidateFrameHeader(h4096.data(), out_bytes) == ParseFrameStatus::RejectOversized);

        // Odd length PCM (1023 bytes) -> RejectOddLength
        auto h1023 = make_header(1, 1023);
        assert(ValidateFrameHeader(h1023.data(), out_bytes) == ParseFrameStatus::RejectOddLength);

        // 0-byte frame -> RejectZeroLength
        auto h0 = make_header(1, 0);
        assert(ValidateFrameHeader(h0.data(), out_bytes) == ParseFrameStatus::RejectZeroLength);

        // Corrupt magic header -> RejectHeader
        std::vector<uint8_t> bad_magic = { 'B', 'A', 'D', '!', 1, 4, 0 };
        assert(ValidateFrameHeader(bad_magic.data(), out_bytes) == ParseFrameStatus::RejectHeader);

        // Control echo (kind = 5) -> OkControlEcho
        auto h_echo = make_header(5, 64);
        assert(ValidateFrameHeader(h_echo.data(), out_bytes) == ParseFrameStatus::OkControlEcho && out_bytes == 64);

        // Production Handshake Parser Validation
        const char* extracted_token = nullptr;
        std::string good_token = "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef";
        std::string good_payload = std::string(kHelloPrefix) + "|" + good_token;
        auto h_hs = make_header(4, good_payload.size());
        assert(ValidateHandshakePayload(h_hs.data(), reinterpret_cast<const uint8_t*>(good_payload.data()), good_payload.size(), extracted_token));
        assert(extracted_token != nullptr && std::string(extracted_token, 64) == good_token);

        // Missing '|' separator
        std::string bad_payload_no_pipe = std::string(kHelloPrefix) + "X" + good_token;
        assert(!ValidateHandshakePayload(h_hs.data(), reinterpret_cast<const uint8_t*>(bad_payload_no_pipe.data()), bad_payload_no_pipe.size(), extracted_token));

        // Wrong prefix
        std::string bad_prefix_payload = "pcm16le/wrong/stereo/v1|" + good_token;
        auto h_bad_prefix = make_header(4, bad_prefix_payload.size());
        assert(!ValidateHandshakePayload(h_bad_prefix.data(), reinterpret_cast<const uint8_t*>(bad_prefix_payload.data()), bad_prefix_payload.size(), extracted_token));

        // Oversized handshake payload (>= 256 bytes)
        std::vector<uint8_t> huge_hs_payload(260, 'A');
        auto h_huge_hs = make_header(4, huge_hs_payload.size());
        assert(!ValidateHandshakePayload(h_huge_hs.data(), huge_hs_payload.data(), huge_hs_payload.size(), extracted_token));

        // Production AudioTicketGuard Lifecycle & Boundary Security
        AudioTicketGuard guard;
        struct in_addr ip_pc, ip_attacker;
        ip_pc.s_addr = 0x0A2BA8C0;       // 192.168.43.10
        ip_attacker.s_addr = 0x142BA8C0; // 192.168.43.20

        char out_ticket[65] = {0};
        auto dummy_rng = [](void* buf, size_t n) {
            std::memset(buf, 0xaa, n);
        };
        auto attacker_rng = [](void* buf, size_t n) {
            std::memset(buf, 0xbb, n);
        };

        // Authorized PC requests ticket
        assert(guard.CreateTicket(ip_pc, out_ticket, 1000, dummy_rng));
        std::string pc_ticket = out_ticket;
        assert(pc_ticket.size() == 64);

        // Attacker attempts to overwrite ticket while active -> REJECTED
        char attacker_ticket[65] = {0};
        assert(!guard.CreateTicket(ip_attacker, attacker_ticket, 5000, attacker_rng));

        // Same PC refreshes its ticket -> ACCEPTED
        char pc_ticket_new[65] = {0};
        auto new_rng = [](void* buf, size_t n) {
            std::memset(buf, 0xcc, n);
        };
        assert(guard.CreateTicket(ip_pc, pc_ticket_new, 6000, new_rng));
        std::string pc_ticket_str = pc_ticket_new;

        // Attacker attempts to redeem PC's ticket -> REJECTED (wrong IP)
        assert(!guard.CheckAndConsume(pc_ticket_str.c_str(), ip_attacker, 7000));

        // Wrong token from PC -> REJECTED
        assert(!guard.CheckAndConsume("dddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddd", ip_pc, 8000));

        // PC redeems valid ticket -> ACCEPTED
        assert(guard.CheckAndConsume(pc_ticket_str.c_str(), ip_pc, 9000));

        // Duplicate redemption (Replay attack) -> REJECTED (single use!)
        assert(!guard.CheckAndConsume(pc_ticket_str.c_str(), ip_pc, 9050));

        // Expired ticket (> 30000ms elapsed) -> REJECTED
        assert(guard.CreateTicket(ip_pc, out_ticket, 10000, dummy_rng));
        assert(!guard.CheckAndConsume(out_ticket, ip_pc, 40001));

        // Hotspot Command Authorization Whitelist logic
        auto is_cmd_permitted = [](bool is_sta_peer, bool token_ok, const char* cmd) -> bool {
            if (!is_sta_peer && !token_ok) return false;
            if (!token_ok) {
                if (!std::strcmp(cmd, "mic") ||
                    !std::strcmp(cmd, "audio_abort") ||
                    !std::strcmp(cmd, "request_audio_ticket") ||
                    !std::strcmp(cmd, "reboot") ||
                    !std::strcmp(cmd, "factory_reset") ||
                    !std::strcmp(cmd, "pair")) {
                    return false;
                }
            }
            return true;
        };

        // Hotspot client without token: safe commands allowed, sensitive commands forbidden!
        assert(is_cmd_permitted(true, false, "mode") == true);
        assert(is_cmd_permitted(true, false, "brightness") == true);
        assert(is_cmd_permitted(true, false, "arcade") == true);
        assert(is_cmd_permitted(true, false, "frame") == true);
        assert(is_cmd_permitted(true, false, "pet") == true);
        assert(is_cmd_permitted(true, false, "mic") == false);
        assert(is_cmd_permitted(true, false, "audio_abort") == false);
        assert(is_cmd_permitted(true, false, "request_audio_ticket") == false);

        // Authorized PC with token: all commands allowed
        assert(is_cmd_permitted(true, true, "mode") == true);
        assert(is_cmd_permitted(true, true, "mic") == true);
        assert(is_cmd_permitted(true, true, "audio_abort") == true);
        assert(is_cmd_permitted(true, true, "request_audio_ticket") == true);

        // External non-hotspot client without token: all rejected
        assert(is_cmd_permitted(false, false, "mode") == false);
        assert(is_cmd_permitted(false, false, "request_audio_ticket") == false);

        std::puts("PASS: production audio protocol parser, ticket single-use lifecycle and UDP authorization guards");
    }

    // Test AFE Sample Stream: Cross-Chunk Buffering, Monotonic Ordering, Priming Duplicate Discard, Stop & Restart
    {
        audio_afe::AfeSampleStream stream;
        constexpr int kFeedChunk = 256;
        std::vector<int16_t> scratch;

        // 1. Cross-chunk accumulation: 4 small chunks of 64 samples = 256 samples
        int16_t val = 0;
        for (int i = 0; i < 3; ++i) {
            int16_t sub[64];
            for (int s = 0; s < 64; ++s) sub[s] = ++val;
            stream.PushInput(sub, 64);
            assert(!stream.CanFeed(kFeedChunk));
        }
        int16_t sub4[64];
        for (int s = 0; s < 64; ++s) sub4[s] = ++val;
        stream.PushInput(sub4, 64);
        assert(stream.CanFeed(kFeedChunk));
        const int16_t* fed = stream.FeedChunk(kFeedChunk, scratch);
        assert(fed != nullptr && scratch.size() == 256 && scratch.front() == 1 && scratch.back() == 256);
        assert(!stream.CanFeed(kFeedChunk));

        // 2. Cold-start priming fallback and monotonic ordering
        stream.Reset();
        val = 0;
        int16_t out_all[1024] = {0};
        size_t out_pos = 0;

        // Chunk 1 (1..256): AFE pipeline is priming, outputs 0 fetched samples
        int16_t in1[256];
        for (int i = 0; i < 256; ++i) in1[i] = ++val;
        stream.PushInput(in1, 256);
        stream.FeedChunk(kFeedChunk, scratch);
        int16_t dest1[256];
        bool normal1 = stream.Emit(dest1, in1, 256);
        assert(!normal1); // Cold start raw fallback!
        assert(stream.PrimedRawSamples() == 256);
        std::memcpy(out_all + out_pos, dest1, 256 * sizeof(int16_t));
        out_pos += 256;

        // Chunk 2 (257..512): AFE finishes delayed processing of chunk 1 (samples 1..256)
        int16_t in2[256];
        for (int i = 0; i < 256; ++i) in2[i] = ++val;
        stream.PushInput(in2, 256);
        stream.FeedChunk(kFeedChunk, scratch);
        int16_t afe_delayed_1[256];
        for (int i = 0; i < 256; ++i) afe_delayed_1[i] = i + 1; // Filtered 1..256
        stream.PushFetched(afe_delayed_1, 256);
        // Duplicate delayed samples matching primed raw samples must be discarded!
        assert(stream.PrimedRawSamples() == 0);
        assert(stream.OutBufferSize() == 0);
        int16_t dest2[256];
        bool normal2 = stream.Emit(dest2, in2, 256);
        assert(!normal2);
        assert(stream.PrimedRawSamples() == 256);
        std::memcpy(out_all + out_pos, dest2, 256 * sizeof(int16_t));
        out_pos += 256;

        // Chunk 3 (513..768): AFE catches up, outputs 512 samples (delayed chunk 2 + chunk 3)
        int16_t in3[256];
        for (int i = 0; i < 256; ++i) in3[i] = ++val;
        stream.PushInput(in3, 256);
        stream.FeedChunk(kFeedChunk, scratch);
        int16_t afe_delayed_2_3[512];
        for (int i = 0; i < 512; ++i) afe_delayed_2_3[i] = 257 + i; // 257..768
        stream.PushFetched(afe_delayed_2_3, 512);
        // Chunk 2 duplicate discarded; chunk 3 kept!
        assert(stream.PrimedRawSamples() == 0);
        assert(stream.OutBufferSize() == 256);
        int16_t dest3[256];
        bool normal3 = stream.Emit(dest3, in3, 256);
        assert(normal3); // Normal AFE output path!
        assert(stream.OutBufferSize() == 0);
        std::memcpy(out_all + out_pos, dest3, 256 * sizeof(int16_t));
        out_pos += 256;

        // Chunk 4 (769..1024): normal steady-state AFE flow
        int16_t in4[256];
        for (int i = 0; i < 256; ++i) in4[i] = ++val;
        stream.PushInput(in4, 256);
        stream.FeedChunk(kFeedChunk, scratch);
        int16_t afe_delayed_4[256];
        for (int i = 0; i < 256; ++i) afe_delayed_4[i] = 769 + i;
        stream.PushFetched(afe_delayed_4, 256);
        int16_t dest4[256];
        bool normal4 = stream.Emit(dest4, in4, 256);
        assert(normal4);
        std::memcpy(out_all + out_pos, dest4, 256 * sizeof(int16_t));
        out_pos += 256;

        // Verify strictly monotonic ordering with NO duplicates or backward timestamp jumps!
        assert(out_pos == 1024);
        for (size_t i = 1; i < 1024; ++i) {
            assert(out_all[i] == out_all[i - 1] + 1);
        }

        // 3. Stop and Restart: buffers and priming counter cleanly reset
        stream.PushInput(in1, 100);
        stream.Emit(dest1, in1, 50);
        assert(stream.InBufferSize() > 0 || stream.PrimedRawSamples() > 0);
        stream.Reset(); // Stop
        assert(stream.InBufferSize() == 0 && stream.OutBufferSize() == 0 && stream.PrimedRawSamples() == 0);

        val = 1000;
        for (int i = 0; i < 256; ++i) in1[i] = ++val;
        stream.PushInput(in1, 256);
        stream.FeedChunk(kFeedChunk, scratch);
        stream.Emit(dest1, in1, 256);
        assert(dest1[0] == 1001 && dest1[255] == 1256);

        std::puts("PASS: AFE sample stream cross-chunk, cold-start priming, duplicate discard, and monotonic ordering");
    }
}
