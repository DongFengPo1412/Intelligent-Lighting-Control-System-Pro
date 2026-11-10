#pragma once
#include <cJSON.h>
#include "display_manager.h"
// -1: not this module; 0: malformed; 1: accepted. Validate before mutation.
int HandleInteractionCommand(const char* cmd, cJSON* root, DisplayManager& display,
                             DisplayManager::CanvasSource source = DisplayManager::CanvasSource::MANUAL_USER);

