#pragma once
#include <cstddef>
#include <cstdint>
#include <cstring>

#ifdef _WIN32
#ifndef WIN32_LEAN_AND_MEAN
#define WIN32_LEAN_AND_MEAN
#endif
#ifndef NOMINMAX
#define NOMINMAX
#endif
#include <winsock2.h>
#else
#include <netinet/in.h>
#endif

namespace pcm_transport {

constexpr size_t kMaxAudioRx = 2048;
constexpr char kHelloPrefix[] = "pcm16le/16000/mono/v2";

enum class ParseFrameStatus {
    OkAudio,
    OkControlEcho,
    RejectHeader,
    RejectOversized,
    RejectZeroLength,
    RejectOddLength,
    RejectUnknownKind
};

inline ParseFrameStatus ValidateFrameHeader(const uint8_t header[7], size_t& out_bytes) {
    if (header[0] != 'K' || header[1] != 'A' || header[2] != 'P' || header[3] != '1') {
        return ParseFrameStatus::RejectHeader;
    }
    out_bytes = (static_cast<size_t>(header[5]) << 8) | header[6];
    if (out_bytes == 0) return ParseFrameStatus::RejectZeroLength;
    if (out_bytes > kMaxAudioRx) return ParseFrameStatus::RejectOversized;
    uint8_t kind = header[4];
    if (kind == 1) {
        if (out_bytes % 2 != 0) return ParseFrameStatus::RejectOddLength;
        return ParseFrameStatus::OkAudio;
    } else if (kind == 5) {
        return ParseFrameStatus::OkControlEcho;
    }
    return ParseFrameStatus::RejectUnknownKind;
}

inline bool ValidateHandshakePayload(const uint8_t header[7], const uint8_t* payload, size_t payload_len,
                                    const char*& out_token_64) {
    if (header[0] != 'K' || header[1] != 'A' || header[2] != 'P' || header[3] != '1' || header[4] != 4) {
        return false;
    }
    size_t wire_size = (static_cast<size_t>(header[5]) << 8) | header[6];
    if (wire_size != payload_len || payload_len >= 256) return false;
    const size_t prefix_len = sizeof(kHelloPrefix) - 1;
    if (payload_len != prefix_len + 1 + 64) return false;
    if (std::memcmp(payload, kHelloPrefix, prefix_len) != 0 || payload[prefix_len] != '|') {
        return false;
    }
    out_token_64 = reinterpret_cast<const char*>(payload + prefix_len + 1);
    return true;
}

class AudioTicketGuard {
public:
    template <typename FillRandom>
    bool CreateTicket(struct in_addr ip, char* out_ticket_64, uint32_t now_ms, FillRandom fill_random) {
        if (!out_ticket_64) return false;
        if (ticket_[0] != '\0' && expire_ms_ > now_ms && ticket_ip_.s_addr != ip.s_addr) {
            return false;
        }
        unsigned char rand_bytes[32];
        fill_random(rand_bytes, sizeof(rand_bytes));
        const char* hex = "0123456789abcdef";
        for (size_t i = 0; i < 32; ++i) {
            out_ticket_64[2 * i] = hex[rand_bytes[i] >> 4];
            out_ticket_64[2 * i + 1] = hex[rand_bytes[i] & 15];
        }
        out_ticket_64[64] = '\0';
        std::memcpy(ticket_, out_ticket_64, 65);
        ticket_ip_ = ip;
        expire_ms_ = now_ms + 30000;
        return true;
    }

    bool CheckAndConsume(const char* token, struct in_addr ip, uint32_t now_ms) {
        if (!token || std::strlen(token) != 64) return false;
        if (ticket_[0] == '\0' || expire_ms_ <= now_ms) return false;
        if (ticket_ip_.s_addr != ip.s_addr) return false;
        unsigned char diff = 0;
        for (size_t i = 0; i < 64; ++i) diff |= ticket_[i] ^ token[i];
        if (diff == 0) {
            ticket_[0] = '\0';
            expire_ms_ = 0;
            return true;
        }
        return false;
    }

    void Clear() {
        ticket_[0] = '\0';
        expire_ms_ = 0;
    }

private:
    char ticket_[65] = {};
    struct in_addr ticket_ip_ = {};
    uint32_t expire_ms_ = 0;
};

// A TCP stream cannot resume at the next header after a partial frame fails.
// Caller holds its transport mutex and invalidates/shuts down this connection.
template <typename Write, typename Disconnect>
bool WriteFrame(uint8_t kind, const void* data, size_t bytes,
                Write write, Disconnect disconnect) {
    if (!data || bytes == 0 || bytes > 2048) return false;
    const uint8_t header[] = {'K', 'A', 'P', '1', kind,
        static_cast<uint8_t>(bytes >> 8), static_cast<uint8_t>(bytes)};
    auto all = [&write](const void* buffer, size_t length) {
        auto* cursor = static_cast<const uint8_t*>(buffer);
        while (length) {
            const auto count = write(cursor, length);
            if (count <= 0 || static_cast<size_t>(count) > length) return false;
            cursor += count;
            length -= static_cast<size_t>(count);
        }
        return true;
    };
    if (all(header, sizeof(header)) && all(data, bytes)) return true;
    disconnect();
    return false;
}

}  // namespace pcm_transport
