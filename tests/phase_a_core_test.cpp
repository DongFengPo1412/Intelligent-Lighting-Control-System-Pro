// Compile the production score store, all registered cartridges and replay guard.
// NVS adapter is fault-injectable/file-backed HOST TEST support, not ESP32 hardware.
#include <cassert>
#include <map>
#include <string>
#include <fstream>
#include <iostream>
#include <thread>
#include <atomic>
#include <vector>
#include "nvs.h"
#include "arcade_score_store.h"
#define private public
#include "arcade_manager.h"
#include "game_001_mario.h"
#include "game_020_pong.h"
#undef private
#include "arcade_protocol.h"
#include "udp_request_guard.h"

static int opens=0, sets=0, commits=0;
static bool initialized=false, fail_open=false, fail_get=false, fail_set=false, fail_commit=false;
static int64_t tick_ms=0;
static std::map<std::string,uint32_t> durable, staged;
static std::string file;
int64_t esp_timer_get_time() { return tick_ms*1000; }
int nvs_open(const char*,int,nvs_handle_t* h) { assert(initialized);++opens;*h=1;return fail_open?ESP_FAIL:ESP_OK; }
int nvs_get_u32(nvs_handle_t,const char* key,uint32_t* out) {
    if(fail_get)return ESP_FAIL;
    auto found=durable.find(key);if(found==durable.end())return ESP_ERR_NVS_NOT_FOUND;
    *out=found->second;return ESP_OK;
}
int nvs_set_u32(nvs_handle_t,const char* key,uint32_t value) { ++sets;if(fail_set)return ESP_FAIL;staged[key]=value;return ESP_OK; }
int nvs_commit(nvs_handle_t) {
    ++commits;if(fail_commit)return ESP_FAIL;
    for(auto item:staged)durable[item.first]=item.second;
    std::ofstream output(file);for(auto item:durable)output<<item.first<<' '<<item.second<<'\n';
    return ESP_OK;
}
void nvs_close(nvs_handle_t) { staged.clear(); }
static void test_replay() {
    UdpRequestGuard guard; const char* reply=nullptr;uint8_t hash[32]={1},other[32]={1};other[31]=1;
    std::string frame="{\"status\":\"ok\",\"pixels\":\""+std::string(1536,'f')+"\"}";
    assert(guard.Check(1,"phone","1_frame",1,hash,&reply)==UdpRequestGuard::Fresh);
    assert(guard.Store(1,"phone","1_frame",1,hash,frame.c_str()));
    assert(guard.Check(1,"phone","1_frame",1,hash,&reply)==UdpRequestGuard::Replay);
    assert(std::string(reply)==frame); // Complete, parseable frame, not a truncated 1024-byte JSON.
    auto* json=cJSON_Parse(reply);assert(json);cJSON_Delete(json);
    assert(guard.Check(1,"phone","1_frame",1,other,&reply)==UdpRequestGuard::Conflict);
    assert(guard.Check(1,"phone","1_frame",2,hash,&reply)==UdpRequestGuard::Conflict);
    assert(guard.Check(2,"phone","1_frame",1,hash,&reply)==UdpRequestGuard::Fresh);
    assert(guard.Check(1,"pc","1_frame",1,hash,&reply)==UdpRequestGuard::Fresh);
    for(int i=2;i<=30;++i){auto id=std::to_string(i)+"_id";assert(guard.Store(1,"phone",id.c_str(),i,hash,"{}"));}
    assert(guard.Check(1,"phone","1_frame",1,hash,&reply)==UdpRequestGuard::Stale);
    assert(guard.Check(1,"phone","1_frame",31,other,&reply)==UdpRequestGuard::Conflict);
    assert(!guard.Store(1,"phone","31_oversize",31,hash,std::string(UdpRequestGuard::kReplySize,'x').c_str()));
    assert(!guard.Store(1,std::string(33,'x').c_str(),"31_bad",31,hash,"{}"));
    for(int i=0;i<31;++i){auto client="client"+std::to_string(i);assert(guard.Store(1,client.c_str(),"1_id",1,hash,"{}"));}
    assert(guard.Check(1,"overflow","1_id",1,hash,&reply)==UdpRequestGuard::Capacity);
}
static void test_protocol() {
    const char* bad[]={"{\"action\":\"select\",\"game_id\":257}","{\"action\":\"select\",\"game_id\":-255}",
        "{\"action\":\"select\",\"game_id\":1.5}","{\"action\":\"select\",\"game_id\":true}",
        "{\"action\":\"select\",\"game_id\":101}","{\"action\":\"unknown\"}","{}",
        "{\"action\":\"input\",\"down\":-1,\"pressed\":0}","{\"action\":\"input\",\"down\":256,\"pressed\":0}",
        "{\"action\":\"input\",\"down\":2,\"pressed\":\"16\"}"};
    for(auto text:bad){auto json=cJSON_Parse(text);assert(!arcade_protocol::Valid(json));cJSON_Delete(json);}
    auto json=cJSON_Parse("{\"action\":\"input\",\"down\":18,\"pressed\":16}");assert(arcade_protocol::Valid(json));cJSON_Delete(json);
}
#include "phase_b_core_test.h"
#include "phase_b2_core_test.h"
#include "phase_b3_core_test.h"

int main(int argc,char** argv) {
    assert(opens==0); // All 13 production static constructors have already run.
    if(argc==3 && std::string(argv[1])=="reopen") {
        file=argv[2];std::ifstream in(file);std::string key;uint32_t value;
        while(in>>key>>value)durable[key]=value;
        initialized=true;arcade::ArcadeScoreStore::SetReady(true);
        assert(arcade::ArcadeScoreStore::LoadHighScore(74)==900);
        std::cout<<"C++ fresh-process persisted score reload passed (host NVS adapter)\n";return 0;
    }
    assert(argc==2);file=argv[1];
    using Store=arcade::ArcadeScoreStore;
    assert(Store::LoadHighScore(1)==0 && opens==0);
    Store::SaveHighScore(1,12);Store::Flush();assert(opens==0 && Store::HasPending());
    initialized=true;Store::SetReady(true);Store::Flush();assert(!Store::HasPending());
    for(int fault=0;fault<4;++fault) {
        Store::SaveHighScore(74,100+fault);
        fail_open=fault==0;fail_get=fault==1;fail_set=fault==2;fail_commit=fault==3;
        Store::Flush();assert(Store::HasPending());
        fail_open=fail_get=fail_set=fail_commit=false;
        Store::Flush();assert(!Store::HasPending() && durable["hs_074"]==100u+fault);
    }
    int before=commits;
    for(int i=104;i<=900;++i)Store::SaveHighScore(74,i);
    assert(commits==before);Store::Flush();assert(commits==before+1);
    // Concurrent producers cannot lose a larger score while another flush runs.
    std::thread producer([]{for(unsigned i=1;i<=500;++i)Store::SaveHighScore(97,i);});
    for(int i=0;i<30;++i)Store::Flush();producer.join();Store::Flush();assert(durable["hs_097"]==500);
    auto& manager=arcade::ArcadeManager::GetInstance();manager.Init();
    const int ids[]={1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26,27,28,29,30,31,32,33,34,35,36,37,38,39,40,41,42,43,44,45,46,47,48,49,50,51,52,53,54,55,56,57,58,59,60,61,62,63,64,65,66,67,68,69,70,72,73,74,75,76,81,83,84,85,86,87,88,92,93,94,95,97,98};
    for(auto id:ids){
        assert(manager.SelectGame(id));assert(manager.GetCurrentGameId()==id);manager.Start();
        std::vector<uint8_t> guarded(800,0xa5);
        arcade::FixedStepClock physics;physics.Reset(tick_ms*1000);
        for(int frame=0;frame<1800;++frame) {
            tick_ms+=33+(frame%13);unsigned bit=1u<<((frame/9)%6);
            manager.HandleInput(frame%11?bit:0,frame%9==0?bit:0);
            assert(physics.Advance(tick_ms*1000,[&](float dt){manager.Update(dt);})<=4);
            manager.Render(guarded.data()+16);
            for(int i=0;i<16;++i)assert(guarded[i]==0xa5 && guarded[784+i]==0xa5);
        }
        manager.Reset();assert(manager.GetCurrentStatus().state==arcade::STATE_TITLE);
    }
    assert(manager.SelectGame(20));assert(manager.SetPlayerCount(2));
    assert(manager.GetCurrentStatus().player_count==2);manager.Start();
    auto* pong=static_cast<arcade::Game020Pong*>(manager.current_game_);
    float p1=pong->p1_y_,p2=pong->p2_y_;
    manager.HandleInput(arcade::KEY_UP|arcade::KEY_B,0);manager.Update(.016f);
    assert(pong->p1_y_<p1 && pong->p2_y_>p2);
    manager.Pause();assert(manager.SetPlayerCount(1));
    assert(manager.GetCurrentStatus().state==arcade::STATE_PAUSED);
    assert(manager.current_keys_down_==0);manager.Resume();manager.Reset();manager.Start();
    assert(manager.GetCurrentStatus().player_count==1);
    assert(!manager.SetPlayerCount(3));
    assert(manager.SelectGame(20));manager.Start();
    for(int i=0;i<20;++i)assert(manager.HandleInput(0,arcade::KEY_A));
    assert(manager.input_count_==20);
    for(int i=0;i<20;++i){manager.Update(.016f);assert(manager.input_count_==19u-i);}
    for(unsigned i=0;i<manager.kInputEvents;++i)assert(manager.HandleInput(0,arcade::KEY_A));
    assert(!manager.HandleInput(0,arcade::KEY_A));
    assert(manager.input_count_==0 && manager.GetCurrentStatus().state==arcade::STATE_PAUSED);
    tick_ms=0;assert(manager.SelectGame(1));manager.Start();manager.HandleInput(18,16);
    auto* mario=static_cast<arcade::Game001Mario*>(manager.current_game_);
    auto new_score=Store::LoadHighScore(1)+120;
    mario->game_.score_=new_score;manager.Update(.001f);
    assert(Store::LoadHighScore(1)==new_score); // Record in active play is queued in RAM.
    assert(manager.current_keys_down_==18);tick_ms=501;manager.Update(.033f);
    assert(manager.current_keys_down_==0 && manager.current_keys_pressed_==0);
    tick_ms=1001;manager.Update(.033f);assert(manager.GetCurrentStatus().state==arcade::STATE_PAUSED);
    manager.Resume();tick_ms=2002;manager.Update(.033f);
    assert(manager.GetCurrentStatus().state==arcade::STATE_PAUSED); // A new disconnect also pauses after explicit resume.
    manager.HandleInput(64,64);manager.Update(.033f);assert(manager.GetCurrentStatus().state==arcade::STATE_PAUSED);
    manager.Resume();assert(manager.GetCurrentStatus().state==arcade::STATE_PLAYING);
    manager.HandleInput(18,16);assert(manager.SelectGame(33));assert(!manager.current_keys_down_&&!manager.current_keys_pressed_);
    test_replay();test_protocol();test_phase_b_foundations();test_b2_audio();test_b2_rounds();test_b2_mechanisms();test_b3_rounds();
    std::cout<<"C++ production constructors/NVS failures/replay/protocol/watchdog tests passed\n";
}
