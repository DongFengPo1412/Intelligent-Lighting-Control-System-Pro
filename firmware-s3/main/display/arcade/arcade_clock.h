#pragma once
#include <stdint.h>
#include <algorithm>

namespace arcade {
// Fixed integer timebase shared by every cartridge; never an unbounded catch-up.
class FixedStepClock {
public:
    static constexpr int64_t kStepUs = 16667; // approximately 60 Hz
    static constexpr unsigned kMaxSteps = 4;
    void Reset(int64_t now) { last_=now; accumulated_=0; initialized_=true; }
    template<class Update> unsigned Advance(int64_t now, Update update) {
        if (!initialized_ || now<last_) { Reset(now);return 0; }
        int64_t elapsed=now-last_;last_=now;
        accumulated_+=elapsed;
        unsigned steps=0;
        while(accumulated_>=kStepUs && steps<kMaxSteps) {
            update(float(kStepUs)/1000000.0f);
            accumulated_-=kStepUs;++steps;++total_steps_;
        }
        if(accumulated_>=kStepUs) {
            int64_t drop=accumulated_-(accumulated_%kStepUs);
            dropped_+=drop;accumulated_-=drop;
        }
        return steps;
    }
    uint64_t DroppedUs() const {return dropped_;}
    uint64_t Steps() const {return total_steps_;}
private:
    bool initialized_=false;
    int64_t last_=0,accumulated_=0;
    uint64_t dropped_=0,total_steps_=0;
};
}
