#pragma once
#include <array>
#include <cstddef>
#include <cstdint>
#include <cstring>

namespace pcm_transport {
enum class TxState { Progress, Blocked, Fault };
struct TxWrite { size_t bytes; TxState state; };
enum class FlushResult { Idle, Pending, Fault, Expired };

// Storage is allocated once in PSRAM by NetworkAudio. No per-frame allocation.
// FIFO preserves partially sent frames and TCP control-barrier ordering.
class PcmTxQueue {
public:
    PcmTxQueue()=default;
    PcmTxQueue(const PcmTxQueue&)=delete;
    PcmTxQueue& operator=(const PcmTxQueue&)=delete;
    static constexpr size_t kSlots=64;
    static constexpr size_t kPayload=2048;
    static constexpr uint32_t kMaxAgeMs=1500;

    bool Enqueue(uint8_t kind,const void* data,size_t bytes,uint32_t now) {
        if(!data || !bytes || bytes>kPayload || (kind!=2 && kind!=5) || (kind==2 && bytes%2))return false;
        // Reserve two slots for heartbeat/abort-barrier echoes.
        if(count_ >= (kind==2 ? kSlots-2 : kSlots)) {
            if(kind==2)dropped_samples_+=static_cast<uint32_t>(bytes/2);
            return false;
        }
        Frame& frame=frames_[(head_+count_)%kSlots];
        const uint8_t header[]={'K','A','P','1',kind,static_cast<uint8_t>(bytes>>8),static_cast<uint8_t>(bytes)};
        std::memcpy(frame.data.data(),header,sizeof(header));
        std::memcpy(frame.data.data()+sizeof(header),data,bytes);
        frame.length=static_cast<uint16_t>(bytes+sizeof(header));
        frame.offset=0;frame.queued_ms=now;
        ++count_;return true;
    }

    template<typename Write>
    FlushResult Flush(uint32_t now,Write write,unsigned budget=8) {
        while(count_ && budget--) {
            Frame& frame=frames_[head_];
            if(uint32_t(now-frame.queued_ms)>kMaxAgeMs)return FlushResult::Expired;
            const size_t remaining=frame.length-frame.offset;
            const TxWrite result=write(frame.data.data()+frame.offset,remaining);
            if(result.state==TxState::Blocked) {
                if(result.bytes)return FlushResult::Fault;
                ++busy_;return FlushResult::Pending;
            }
            if(result.state==TxState::Fault || !result.bytes || result.bytes>remaining)return FlushResult::Fault;
            frame.offset+=static_cast<uint16_t>(result.bytes);
            if(frame.offset==frame.length) {head_=(head_+1)%kSlots;--count_;}
        }
        return count_ ? FlushResult::Pending : FlushResult::Idle;
    }

    void Clear() {
        while(count_) {
            const Frame& frame=frames_[head_];
            if(frame.data[4]==2)dropped_samples_+=(frame.length-7u)/2u;
            head_=(head_+1)%kSlots;--count_;
        }
        head_=0;
    }
    uint32_t Queued() const {return static_cast<uint32_t>(count_);}
    uint32_t Busy() const {return busy_;}
    uint32_t DroppedSamples() const {return dropped_samples_;}
private:
    struct Frame {
        std::array<uint8_t,kPayload+7> data{};
        uint32_t queued_ms=0;
        uint16_t length=0,offset=0;
    };
    std::array<Frame,kSlots> frames_{};
    size_t head_=0,count_=0;
    uint32_t busy_=0,dropped_samples_=0;
};
} // namespace pcm_transport
