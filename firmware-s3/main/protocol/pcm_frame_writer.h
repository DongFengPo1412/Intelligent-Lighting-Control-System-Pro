#pragma once
#include <cstddef>
#include <cstdint>

namespace pcm_transport {
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
