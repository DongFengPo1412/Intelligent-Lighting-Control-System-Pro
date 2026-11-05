#pragma once
#include <stddef.h>
#include <string.h>

// One 16x16 RGB888 frame, without heap allocation. 768 is divisible by 3.
namespace frame_encoding {
inline bool HexToBase64(const char* hex, char* out, size_t capacity) {
    if (!hex || !out || strlen(hex) != 1536 || capacity < 1025) return false;
    const char* digits = "0123456789abcdef";
    const char* alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";
    for (size_t i=0;i<256;++i) {
        unsigned value=0;
        for (size_t n=0;n<6;++n) {
            const char* digit=strchr(digits,hex[i*6+n]);
            if (!digit) return false;
            value=(value<<4)|unsigned(digit-digits);
        }
        for (size_t n=0;n<4;++n) out[i*4+n]=alphabet[(value>>(18-6*n))&63];
    }
    out[1024]=0;
    return true;
}
}
