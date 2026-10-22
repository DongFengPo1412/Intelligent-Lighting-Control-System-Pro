#include "../firmware-s3/main/display/srgb_transfer.h"

constexpr bool TestAllLevels() {
    for (int brightness = 0; brightness <= 255; ++brightness) {
        for (int encoded = 0; encoded <= 255; ++encoded) {
            const int output = DisplayColor::SrgbToPwm(encoded, brightness);
            if (output > brightness) return false;
            if (encoded > 0 && output < DisplayColor::SrgbToPwm(encoded - 1, brightness)) return false;
            if (brightness > 0 && output < DisplayColor::SrgbToPwm(encoded, brightness - 1)) return false;
        }
        if (DisplayColor::SrgbToPwm(0, brightness) != 0) return false;
        if (DisplayColor::SrgbToPwm(255, brightness) != brightness) return false;
    }
    return true;
}

static_assert(TestAllLevels(), "Transfer must preserve black, white, bounds and monotonicity at every brightness");
static_assert(DisplayColor::SrgbToPwm(128, 255) == 55, "sRGB midpoint is about 21.6 percent linear light");
static_assert(DisplayColor::SrgbToPwm(141, 12) == 3, "Hair red stays below white peak");
static_assert(DisplayColor::SrgbToPwm(74, 12) == 1, "Hair green retains its contribution");
static_assert(DisplayColor::SrgbToPwm(215, 12) == 8, "Upper iris blue remains distinct from white");
