#pragma once

// Text payload only; transport framing removes CR/LF before calling this helper.
inline bool ParseSpectrumPacket(const char* s, int& beat, int bands[16])
{
    if (!s || s[0] != 'f' || s[1] != ',') return false;
    s += 2;
    int values[17];
    for (int i = 0; i < 17; ++i) {
        int value = 0, digits = 0;
        while (*s >= '0' && *s <= '9') {
            if (++digits > 2) return false;
            value = value * 10 + (*s++ - '0');
        }
        if (!digits || value > (i == 0 ? 1 : 15)) return false;
        values[i] = value;
        if (i < 16) { if (*s++ != ',') return false; }
        else if (*s != '\0') return false;
    }
    beat = values[0];
    for (int i = 0; i < 16; ++i) bands[i] = values[i + 1];
    return true;
}
