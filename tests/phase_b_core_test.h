// Called from the existing production-cartridge host harness, not ESP32 hardware.
#include "arcade_clock.h"
#include "arcade_sound.h"
#include "../firmware-s3/main/audio/audio_priority.h"
#define private public
#include "game_017_rhythm_lanes.h"
#include "game_085_lemmings_rescue.h"
#include "game_092_fruit_slice.h"
#include "game_095_super_hexagon.h"
#undef private

static uint32_t sound_now=0;
static uint32_t sound_clock(){return sound_now;}
static std::atomic<uint32_t> stress_now{0};
static uint32_t stress_clock(){return stress_now.load();}
static void test_phase_b_complete_rounds() {
    using namespace arcade;
    Sounds().SetClock(sound_clock);Sounds().Configure(true,25);Sounds().Invalidate();
    constexpr float dt=16667.f/1000000.f;
    for(unsigned level=0;level<3;++level) {
        Sounds().Invalidate(); // Separate direct-cartridge test sessions, like manager selection.
        Game017RhythmLanes rhythm;rhythm.SetDifficulty(level);rhythm.Init();rhythm.Start();
        uint8_t health_frame[768];rhythm.Render(health_frame);unsigned health_pixels=0;
        for(int x=0;x<16;++x)if(health_frame[3*x]==80 && health_frame[3*x+1]==230 && health_frame[3*x+2]==140)++health_pixels;
        assert(health_pixels==unsigned(rhythm.MaxMisses()));
        const uint16_t lanes[]={KEY_LEFT,KEY_DOWN,KEY_UP,KEY_RIGHT};
        unsigned beats=0,hits=0;
        for(int t=0;t<16000 && rhythm.state_==STATE_PLAYING;++t) {
            sound_now+=17;
            uint16_t keys=0;
            for(auto& n:rhythm.notes_)if(n.active && std::abs(n.y-13.f)<.16f)keys|=lanes[n.lane];
            rhythm.Update(dt,0,keys);
            arcade::SoundEvent sound;
            while(Sounds().Pop(sound)){if(sound.kind==Sound::Beat)++beats;if(sound.kind==Sound::Hit)++hits;}
        }
        assert(rhythm.state_==STATE_VICTORY && rhythm.notes_cleared_==64);
        assert(beats>=63 && hits==64);
        Game085LemmingsRescue lem;lem.SetDifficulty(level);lem.Init();lem.Start();
        bool flags[4]={};
        for(int t=0;t<16000 && lem.state_==STATE_PLAYING;++t) {
            int mark=lem.stage_==1?0:lem.stage_==2?1:!flags[2]?2:3;
            int x=mark==0||mark==2?6:7, y=mark==0||mark==2?4:mark==1?11:9;
            int skill=mark==0||mark==2?2:1;uint16_t pressed=0;
            if(!flags[mark]) {
                if(lem.cursor_x_!=x)pressed=lem.cursor_x_<x?KEY_RIGHT:KEY_LEFT;
                else if(lem.cursor_y_!=y)pressed=lem.cursor_y_<y?KEY_DOWN:KEY_UP;
                else if(lem.selected_skill_!=skill)pressed=KEY_B;
                else for(auto& lm:lem.lemmings_)if(lm.alive && lm.state==0 && lm.x==x && lm.y==y){pressed=KEY_A;flags[mark]=true;break;}
            }
            lem.Update(dt,0,pressed);
        }
        assert(lem.state_==STATE_VICTORY && lem.stage_==3 && lem.saved_count_>=lem.RequiredSaved());
        Game095SuperHexagon hex;hex.SetDifficulty(level);hex.Init();hex.Start();
        for(int t=0;t<16000 && hex.state_==STATE_PLAYING;++t) {
            int nearest=-1;float radius=100.f;
            for(int i=0;i<hex.kNumWalls;++i)if(hex.walls_[i].radius>=1.9f && hex.walls_[i].radius<radius){radius=hex.walls_[i].radius;nearest=i;}
            float best=100.f;
            if(nearest>=0)for(int i=0;i<6;++i)if(!(hex.walls_[nearest].solid_mask&(1<<i))) {
                float delta=std::remainder((i+.5f)*3.14159265f/3-hex.player_angle_,6.28318531f);
                if(std::abs(delta)<std::abs(best))best=delta;
            }
            uint16_t down=best>90?0:best>.07f?KEY_RIGHT:best<-.07f?KEY_LEFT:0;
            hex.Update(dt,down,0);
        }
        assert(hex.state_==STATE_VICTORY && (hex.walls_passed_>=30 || hex.survival_timer_>=45));
        Game092FruitSlice fruit;fruit.SetDifficulty(level);fruit.Init();fruit.Start();
        const int dirs[][3]={{1,0,KEY_RIGHT},{-1,0,KEY_LEFT},{0,1,KEY_DOWN},{0,-1,KEY_UP},
            {1,1,KEY_RIGHT|KEY_DOWN},{1,-1,KEY_RIGHT|KEY_UP},{-1,1,KEY_LEFT|KEY_DOWN},{-1,-1,KEY_LEFT|KEY_UP}};
        auto clamp=[](float v,float lo,float hi){return std::max(lo,std::min(hi,v));};
        for(int t=0;t<16000 && fruit.state_==STATE_PLAYING;++t) {
            uint16_t down=0,pressed=0;int best_hits=0;
            if(fruit.slash_timer_<=dt)for(auto& d:dirs) {
                float x=clamp(fruit.blade_x_+d[0]*14*dt,1.5f,14.5f),y=clamp(fruit.blade_y_+d[1]*14*dt,1.5f,14.5f);
                float norm=std::hypot(float(d[0]),float(d[1])),ux=d[0]/norm,uy=d[1]/norm;
                int hits=0;bool safe=true;
                for(auto& it:fruit.items_)if(it.active) {
                    float cx=it.x+1,cy=it.y+1,project=clamp((cx-x)*ux+(cy-y)*uy,-5,5);
                    float distance=std::hypot(cx-(x+project*ux),cy-(y+project*uy));
                    if(it.is_bomb && distance<=fruit.HitRadius()+.1f)safe=false;
                    if(!it.is_bomb && cy>=1 && cy<=15 && distance<=fruit.HitRadius()-.1f)++hits;
                }
                if(safe && hits>best_hits){best_hits=hits;down=d[2];pressed=KEY_A;}
            }
            if(!pressed) {
                int target=-1;float distance=100.f;
                for(int i=0;i<fruit.kMaxItems;++i) {
                    auto& it=fruit.items_[i];float score=std::abs(it.x+1-fruit.blade_x_)+std::abs(it.y+1-fruit.blade_y_);
                    if(it.active && !it.is_bomb && it.y<14.5f && score<distance){distance=score;target=i;}
                }
                if(target>=0) {
                    float x=fruit.items_[target].x+1;
                    down=x<fruit.blade_x_-.4f?KEY_LEFT:x>fruit.blade_x_+.4f?KEY_RIGHT:0;
                    if(fruit.blade_y_>8.5f)down|=KEY_UP;else if(fruit.blade_y_<7.5f)down|=KEY_DOWN;
                }
            }
            fruit.Update(dt,down,pressed);
        }
        assert(fruit.state_==STATE_VICTORY && fruit.fruits_sliced_>=40 && !fruit.exploded_);
        // Actual no-input loss paths, not manually forced terminal states.
        Cartridge* games[]={&rhythm,&lem,&fruit,&hex};
        for(auto* game:games) {
            game->Reset();game->Start();
            for(int t=0;t<16000 && game->GetStatus().state==STATE_PLAYING;++t)game->Update(dt,0,0);
            assert(game->GetStatus().state==STATE_GAMEOVER);
            game->Reset();game->Start();game->Pause();game->Update(dt,KEY_A,KEY_A);assert(game->GetStatus().state==STATE_PAUSED);
            game->Resume();assert(game->GetStatus().state==STATE_PLAYING);
        }
    }
    std::cout<<"Production C++ full rounds: 017/085/092/095 at Easy/Normal/Hard, all stages/goals, failure/pause/restart passed\n";
}
static void test_phase_b_foundations() {
    arcade::FixedStepClock clock;clock.Reset(0);uint64_t steps=0;
    // 30 simulated minutes with variable render overhead, not wall-clock stress.
    int64_t elapsed=0;for(int i=0;i<45000;++i){elapsed+=40000;clock.Advance(elapsed,[&](float dt){assert(dt>0 && dt<.017f);++steps;});}
    assert(steps==uint64_t(elapsed/clock.kStepUs) && clock.DroppedUs()==0);
    auto before=steps;clock.Advance(elapsed+2000000,[&](float){++steps;});
    assert(steps-before==4 && clock.DroppedUs()>1900000);
    assert(clock.Advance(elapsed-1,[&](float){assert(false);})==0);
    arcade::SoundBus bus(sound_clock);arcade::SoundEvent event;
    sound_now=100;assert(bus.Emit(arcade::Sound::Beat,17,0));
    assert(bus.Emit(arcade::Sound::Beat,17,0));assert(bus.Pop(event));assert(bus.Pop(event));
    int peak=0;for(unsigned i=0;i<1000;++i)peak=std::max(peak,std::abs(int(arcade::SoundSample(event,i,100))));
    assert(peak>1000 && peak<=4000);
    sound_now+=60;assert(bus.Emit(arcade::Sound::Win,17));bus.Invalidate();assert(!bus.Pop(event));
    sound_now+=60;assert(bus.Emit(arcade::Sound::Score,17));sound_now+=181;assert(!bus.Pop(event));
    for(int i=0;i<16;++i){sound_now+=60;assert(bus.Emit(arcade::Sound::Score,17));}
    sound_now+=60;assert(!bus.Emit(arcade::Sound::Score,17));
    bus.Configure(false,50);assert(!bus.Emit(arcade::Sound::Beat,17));assert(!bus.Pop(event));
    bus.Configure(true,0);assert(!bus.Emit(arcade::Sound::Beat,17));assert(!bus.Pop(event));
    arcade::SoundBus stress(stress_clock);std::atomic<bool> finished{false};
    std::thread producer([&]{for(int i=0;i<10000;++i){stress_now.fetch_add(60);stress.Emit(arcade::Sound::Hit,92);}finished=true;});
    while(!finished){arcade::SoundEvent e;if(stress.Pop(e))assert(e.kind==arcade::Sound::Hit && e.game==92);}
    producer.join();assert(stress.queued>0);
    AudioPriorityGate gate;assert(gate.GameAllowed(0));gate.External(100);assert(!gate.GameAllowed(599));assert(gate.GameAllowed(600));
    gate.Capture(true);assert(!gate.GameAllowed(99999));gate.Capture(false);assert(gate.GameAllowed(99999));
    gate.External(0xffffff00u);assert(!gate.GameAllowed(0xffffff10u));assert(gate.GameAllowed(244));
    arcade::Sounds().SetClock(sound_clock);
    auto& manager=arcade::ArcadeManager::GetInstance();assert(manager.SelectGame(17));
    assert(manager.Configure(false,15,0));assert(manager.GetCurrentStatus().difficulty==0);
    manager.Start();assert(!manager.Configure(true,90,2));assert(!arcade::Sounds().Enabled());
    manager.Configure(true,25,-1);sound_now+=60;manager.Pause();
    assert(arcade::Sounds().Pop(event) && event.kind==arcade::Sound::Pause);
    manager.Resume();
    manager.Reset();assert(manager.Configure(true,25,2));assert(manager.GetCurrentStatus().difficulty==2);
    assert(manager.SelectGame(20));assert(!manager.Configure(true,25,2));assert(manager.Configure(false,0,-1));
    for(auto text:{"{\"action\":\"config\",\"sound_enabled\":\"true\",\"sound_volume\":25}",
        "{\"action\":\"config\",\"sound_enabled\":true,\"sound_volume\":101}",
        "{\"action\":\"config\",\"sound_enabled\":true,\"sound_volume\":25,\"difficulty\":3}"}) {
        auto* json=cJSON_Parse(text);assert(!arcade_protocol::Valid(json));cJSON_Delete(json);
    }
    auto* valid=cJSON_Parse("{\"action\":\"config\",\"sound_enabled\":true,\"sound_volume\":25,\"difficulty\":2}");
    assert(arcade_protocol::Valid(valid));cJSON_Delete(valid);
    std::cout<<"Phase B fixed time, bounded sound/expiry, voice/capture priority and config contracts passed\n";
    test_phase_b_complete_rounds();
}
