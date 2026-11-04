#pragma once
#include <stdint.h>
#include <stddef.h>
#include <stdio.h>
#include <string.h>

// Owned exclusively by the UDP receive task. No allocations in the input path.
// Full SHA-256 command digests; response copies are length checked, never truncated.
class UdpRequestGuard {
public:
    static constexpr size_t kReplySize = 2304;
    enum Result { Fresh, Replay, Conflict, Stale, Capacity };
    struct Entry {
        uint32_t peer = 0;
        char client[33] = {}, id[65] = {};
        uint64_t seq = 0;
        uint8_t digest[32] = {};
        char reply[kReplySize] = {};
    };
    Result Check(uint32_t peer, const char* client, const char* id, uint64_t seq,
                 const uint8_t digest[32], const char** reply) const {
        *reply = nullptr;
        if (!ValidKey(client,id,seq) || !digest) return Conflict;
        for (const auto& e : entries_) {
            if (!e.seq || e.peer != peer || strcmp(client, e.client)) continue;
            if (!strcmp(id, e.id) || seq == e.seq) {
                if (seq != e.seq || strcmp(id, e.id) || memcmp(digest, e.digest, 32)) return Conflict;
                *reply = e.reply; return Replay;
            }
        }
        for (const auto& c : clients_) {
            if (c.used && c.peer == peer && !strcmp(c.id, client))
                return seq <= c.last ? Stale : Fresh;
        }
        for (const auto& c : clients_) if (!c.used) return Fresh;
        return Capacity; // Never evict a replay watermark to accept an old request.
    }
    bool Store(uint32_t peer, const char* client, const char* id, uint64_t seq,
               const uint8_t digest[32], const char* reply) {
        if (!ValidKey(client,id,seq) || !digest || !reply || strlen(reply) >= kReplySize) return false;
        Client* target = nullptr;
        for (auto& c : clients_) if (c.used && c.peer == peer && !strcmp(c.id, client)) { target = &c; break; }
        if (!target) for (auto& c : clients_) if (!c.used) { target = &c; break; }
        if (!target) return false;
        target->used = true; target->peer = peer; strcpy(target->id, client); target->last = seq;
        auto& e = entries_[next_++ % 16];
        e.peer = peer; strcpy(e.client, client); strcpy(e.id, id); e.seq = seq;
        memcpy(e.digest, digest, 32); strcpy(e.reply, reply);
        return true;
    }
private:
    static bool ValidKey(const char* client,const char* id,uint64_t seq) {
        if (!client || !id || !seq || !strlen(client) || strlen(client)>32 || strlen(id)>64) return false;
        char prefix[24];
        snprintf(prefix,sizeof(prefix),"%llu_",(unsigned long long)seq);
        // Bind the ID to its sequence even after its full reply has left the ring.
        // Reusing an old ID with a new sequence can never execute a different payload.
        size_t length=strlen(prefix);
        return strlen(id)>length && !strncmp(id,prefix,length);
    }
    struct Client { bool used = false; uint32_t peer = 0; char id[33] = {}; uint64_t last = 0; };
    Entry entries_[16] = {};
    Client clients_[32] = {};
    size_t next_ = 0;
};
