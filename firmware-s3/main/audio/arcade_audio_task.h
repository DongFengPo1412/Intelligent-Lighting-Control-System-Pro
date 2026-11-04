#pragma once
// Starts one shared, low-priority worker. Never call playback in game Update().
bool StartArcadeAudioTask();

#include <stdint.h>
// ESP-IDF returns minimum unused stack bytes, not words. Zero means not started.
uint32_t ArcadeAudioStackFreeBytes();
