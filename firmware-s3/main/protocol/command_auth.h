#pragma once

#include <cstring>
#include <cctype>

#ifdef _WIN32
#ifndef strcasecmp
#define strcasecmp _stricmp
#endif
#ifndef strncasecmp
#define strncasecmp _strnicmp
#endif
#endif

#if defined(__has_include)
  #if __has_include(<cJSON.h>)
    #include <cJSON.h>
    #define HAS_CJSON 1
  #elif __has_include("cJSON.h")
    #include "cJSON.h"
    #define HAS_CJSON 1
  #endif
#endif

#ifndef HAS_CJSON
struct cJSON {
    struct cJSON* next;
    struct cJSON* prev;
    struct cJSON* child;
    int type;
    char* valuestring;
    int valueint;
    double valuedouble;
    char* string;
};
#define cJSON_Invalid (0)
#define cJSON_False  (1 << 0)
#define cJSON_True   (1 << 1)
#define cJSON_NULL   (1 << 2)
#define cJSON_Number (1 << 3)
#define cJSON_String (1 << 4)
#define cJSON_Array  (1 << 5)
#define cJSON_Object (1 << 6)
#define cJSON_Raw    (1 << 7)

inline int cJSON_IsObject(const cJSON* const item) {
    return (item != nullptr) && (item->type & 0xFF) == cJSON_Object;
}
inline int cJSON_IsString(const cJSON* const item) {
    return (item != nullptr) && (item->type & 0xFF) == cJSON_String;
}
inline cJSON* cJSON_GetObjectItem(const cJSON* const object, const char* const string) {
    if (!object || !string) return nullptr;
    cJSON* current = object->child;
    while (current) {
        if (current->string && strcmp(current->string, string) == 0) return current;
        current = current->next;
    }
    return nullptr;
}
#endif

namespace command_auth {

/**
 * Checks whether an incoming command (JSON or plain text) is permitted
 * for unauthenticated hotspot clients.
 *
 * Ordinary entertainment, display, arcade, desk pet, and lighting controls
 * are allowed passwordless on the hotspot network.
 * Sensitive operations (microphone capture/streaming, audio abort, audio ticket,
 * reboot, factory reset, pairing) strictly require valid pairing credentials.
 */
inline bool IsPermittedUnauthenticated(const char* raw_cmd, const cJSON* validated_json) {
    if (!raw_cmd) return false;

    // Strip leading whitespace
    while (*raw_cmd == ' ' || *raw_cmd == '\t' || *raw_cmd == '\r' || *raw_cmd == '\n') {
        raw_cmd++;
    }
    if (*raw_cmd == '\0') return false;

    // 1. Validated JSON command
    if (validated_json && cJSON_IsObject(validated_json)) {
        cJSON* cmd_item = cJSON_GetObjectItem(validated_json, "cmd");
        if (cJSON_IsString(cmd_item) && cmd_item->valuestring) {
            const char* name = cmd_item->valuestring;
            // Explicit whitelist of ordinary, safe operations
            if (!strcasecmp(name, "mode") ||
                !strcasecmp(name, "color") ||
                !strcasecmp(name, "brightness") ||
                !strcasecmp(name, "b") ||
                !strcasecmp(name, "off") ||
                !strcasecmp(name, "stop") ||
                !strcasecmp(name, "countdown") ||
                !strcasecmp(name, "stop_countdown") ||
                !strcasecmp(name, "stop_cd") ||
                !strcasecmp(name, "spectrum") ||
                !strcasecmp(name, "bands") ||
                !strcasecmp(name, "frame") ||
                !strcasecmp(name, "status") ||
                !strcasecmp(name, "face") ||
                !strcasecmp(name, "emoji") ||
                !strcasecmp(name, "arcade") ||
                !strcasecmp(name, "pet") ||
                !strcasecmp(name, "kurisu") ||
                !strcasecmp(name, "board_led") ||
                !strcasecmp(name, "led") ||
                !strcasecmp(name, "volume") ||
                !strcasecmp(name, "v") ||
                !strcasecmp(name, "beep") ||
                !strcasecmp(name, "key")) {
                return true;
            }
        }
        return false;
    }

    // 2. Plain text command: Spectrum streaming
    if (strncmp(raw_cmd, "f,", 2) == 0) return true;

    // Plain text: Status & diagnostics (safe queries)
    if (!strcasecmp(raw_cmd, "status")) return true;

    // Plain text: Faces & emotions
    if (!strcasecmp(raw_cmd, "happy") || !strcasecmp(raw_cmd, "angry") ||
        !strcasecmp(raw_cmd, "sad") || !strcasecmp(raw_cmd, "thinking") ||
        !strcasecmp(raw_cmd, "breathe") || !strcasecmp(raw_cmd, "cry") ||
        !strcasecmp(raw_cmd, "neutral") || !strcasecmp(raw_cmd, "dynamic") ||
        !strcasecmp(raw_cmd, "face") || !strcasecmp(raw_cmd, "emoji")) {
        return true;
    }

    // Plain text: Games & pet
    if (!strcasecmp(raw_cmd, "kurisu") || !strcasecmp(raw_cmd, "pet") ||
        !strcasecmp(raw_cmd, "snake") || !strcasecmp(raw_cmd, "tetris") ||
        !strcasecmp(raw_cmd, "fire") || !strcasecmp(raw_cmd, "matrix") ||
        !strcasecmp(raw_cmd, "spectrum") || !strcasecmp(raw_cmd, "beep")) {
        return true;
    }

    // Plain text: Off / Stop
    if (!strcasecmp(raw_cmd, "off") || !strcasecmp(raw_cmd, "stop") ||
        !strcasecmp(raw_cmd, "stop_countdown") || !strcasecmp(raw_cmd, "stop_cd")) {
        return true;
    }

    // Plain text commands with parameters (safe prefixes)
    auto match_prefix = [](const char* s, const char* prefix, size_t len) {
        if (strncasecmp(s, prefix, len) == 0) {
            char next = s[len];
            return next == ' ' || next == '\t' || next == '\0';
        }
        return false;
    };

    if (match_prefix(raw_cmd, "mode", 4)) return true;
    if (match_prefix(raw_cmd, "color", 5)) return true;
    if (match_prefix(raw_cmd, "brightness", 10)) return true;
    if (match_prefix(raw_cmd, "b", 1)) return true;
    if (match_prefix(raw_cmd, "countdown", 9)) return true;
    if (match_prefix(raw_cmd, "volume", 6)) return true;
    if (match_prefix(raw_cmd, "v", 1)) return true;
    if (match_prefix(raw_cmd, "board_led", 9)) return true;
    if (match_prefix(raw_cmd, "led", 3)) return true;
    if (match_prefix(raw_cmd, "arcade", 6)) return true;

    // All other commands (mic on, mic off, reboot, pair, audio_abort, etc.)
    // are rejected for unauthenticated clients.
    return false;
}

} // namespace command_auth
