#pragma once
#include <atomic>
#include <stdint.h>
#include <cmath>

namespace arcade {
enum class Sound : uint8_t { Select,Start,Pause,Score,Hurt,Win,Lose,Action,Beat,Hit,Jump,Shot,Collision,Count };
struct SoundEvent {Sound kind;uint8_t game,detail;uint32_t generation,at;};

// No heap allocation or waiting in the game/display producer. An occupied lock,
// full queue, stale event or repeated explicit operation identity is dropped.
class SoundBus {
public:
    using Clock=uint32_t(*)();
    explicit SoundBus(Clock clock=nullptr):clock_(clock) {}
    void SetClock(Clock clock) {clock_=clock;} // Before starting the worker only.
    void Configure(bool enabled,uint8_t volume) {enabled_=enabled;volume_=volume;if(!enabled || !volume)Invalidate();}
    bool Enabled() const {return enabled_;}
    uint8_t Volume() const {return volume_;}
    uint32_t Generation() const {return generation_;}
    void Invalidate() {++generation_;if(!lock_.test_and_set(std::memory_order_acquire)){head_=count_=0;lock_.clear(std::memory_order_release);}}
    bool Emit(Sound kind,uint8_t game,uint8_t detail=0,uint32_t operation=0) {
        if(!enabled_ || !volume_ || kind>=Sound::Count)return false;
        if(lock_.test_and_set(std::memory_order_acquire)){++dropped;return false;}
        uint32_t now=clock_?clock_():0;
        bool duplicate=false;
        // Zero denotes a fresh gameplay event: rapid hits/chords remain distinct.
        // Explicit identities are optional local operation IDs, scoped to this session.
        if(operation)for(auto& key:recent_)if(key.id==operation && key.game==game && key.kind==kind && key.detail==detail && key.generation==generation_)duplicate=true;
        bool accepted=count_<kCapacity && !duplicate;
        if(accepted){events_[(head_+count_)%kCapacity]={kind,game,detail,generation_,now};++count_;++queued;
            if(operation){recent_[recent_pos_]={operation,generation_,game,detail,kind};recent_pos_=(recent_pos_+1)%kCapacity;}}
        else {++dropped;if(duplicate)++duplicates;}
        lock_.clear(std::memory_order_release);return accepted;
    }
    bool Pop(SoundEvent& out) {
        if(lock_.test_and_set(std::memory_order_acquire))return false;
        bool found=false;uint32_t now=clock_?clock_():0;
        while(count_) {
            out=events_[head_];head_=(head_+1)%kCapacity;--count_;
            if(enabled_ && volume_ && out.generation==generation_ && uint32_t(now-out.at)<=180){found=true;break;}
            ++dropped;
        }
        lock_.clear(std::memory_order_release);return found;
    }
    std::atomic<uint32_t> queued{0},dropped{0},played{0},preempted{0},busy{0},short_writes{0},late{0},faults{0},duplicates{0};
private:
    static constexpr unsigned kCapacity=16;
    std::atomic_flag lock_=ATOMIC_FLAG_INIT;
    SoundEvent events_[kCapacity]={};unsigned head_=0,count_=0;
    struct Identity {uint32_t id=0,generation=0;uint8_t game=0,detail=0;Sound kind=Sound::Select;};
    Identity recent_[kCapacity]{};unsigned recent_pos_=0;
    std::atomic<bool> enabled_{true};std::atomic<uint8_t> volume_{25};
    std::atomic<uint32_t> generation_{1};Clock clock_;
};
inline SoundBus& Sounds(){static SoundBus bus;return bus;}

struct SoundTone {unsigned frequency,duration_ms;};
inline SoundTone ToneFor(const SoundEvent& e) {
    static const SoundTone tones[]={{420,35},{660,70},{310,35},{880,40},{180,55},{1046,120},{130,120},{520,30},{262,22},{784,28},{400,55},{1200,20},{160,45}};
    SoundTone t=tones[unsigned(e.kind)];
    if(e.kind==Sound::Beat){static const unsigned notes[]={262,330,392,523};t.frequency=notes[e.detail%4];}
    else t.frequency+=(e.game%5)*22;
    if(e.kind==Sound::Action || e.kind==Sound::Hit)t.frequency+=(e.detail%4)*70;
    return t;
}
// Small enveloped synthesized tones; neither licensed recordings nor a PCM cache.
inline int16_t SoundSample(const SoundEvent& e,unsigned sample,uint8_t volume) {
    auto t=ToneFor(e);unsigned total=t.duration_ms*16;
    if(sample>=total || volume>100)return 0;
    float envelope=std::fmin(1.f,std::fmin(sample/48.f,(total-1-sample)/80.f));
    float pitch=t.frequency;
    if(e.kind==Sound::Start || e.kind==Sound::Win)pitch*=1.f+0.3f*sample/total;
    if(e.kind==Sound::Lose || e.kind==Sound::Hurt)pitch*=1.f-0.35f*sample/total;
    return int16_t(std::sin(6.28318530718f*pitch*sample/16000.f)*4000.f*volume/100.f*envelope);
}
}
