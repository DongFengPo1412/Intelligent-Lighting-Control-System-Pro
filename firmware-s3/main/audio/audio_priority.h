#pragma once
#include <atomic>
#include <stdint.h>

class AudioPriorityGate {
public:
    void External(uint32_t now){until_.store(now+500,std::memory_order_release);seen_=true;}
    void Capture(bool active){capture_=active;}
    bool GameAllowed(uint32_t now) const {
        return !capture_.load() && (!seen_.load() || int32_t(now-until_.load(std::memory_order_acquire))>=0);
    }
private:
    std::atomic<uint32_t> until_{0};std::atomic<bool> seen_{false};
    std::atomic<bool> capture_{false};
};
