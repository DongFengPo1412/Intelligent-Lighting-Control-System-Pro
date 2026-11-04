#pragma once
#include <stddef.h>

// Local pairing credential. Plain LAN transport: access control, not encryption.
// The key is persisted in NVS and disclosed only by the explicit USB `pair` command.
class NetworkAuth {
public:
    static NetworkAuth& GetInstance();
    bool Init(bool nvs_ready);
    bool Check(const char* token) const;
    const char* TokenForUsbPairing() const { return ready_ ? token_ : ""; }
    const char* BootId() const { return boot_id_; }
private:
    bool ready_ = false;
    char token_[65] = {};
    char boot_id_[33] = {};
};
