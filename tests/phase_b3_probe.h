#pragma once
#include "game_007_downwell.h"
#include "game_008_jump_king.h"
#include "game_011_dino_runner.h"
#include "game_012_knife_hit.h"
#include "game_013_pendulum_toss.h"
#include "game_023_air_hockey.h"
#include <vector>
namespace arcade {
struct B3Probe {
    static std::vector<double> Read(Cartridge *game) {
        switch (game->GetId()) {
        case 7: {
            const auto &g = *static_cast<const Game007Downwell *>(game);
            return {double(g.x),    double(g.y),     double(g.vy),
                    double(g.ammo), double(g.kills), double(g.hp)};
        }
        case 8: {
            const auto &g = *static_cast<const Game008JumpKing *>(game);
            return {double(g.x),      double(g.y),      double(g.vx),      double(g.vy),
                    double(g.charge), double(g.facing), double(g.grounded)};
        }
        case 11: {
            const auto &g = *static_cast<const Game011DinoRunner *>(game);
            return {double(g.y),     double(g.vy),    double(g.distance), double(g.cleared),
                    double(g.ob[0]), double(g.ob[1]), double(g.ob[2])};
        }
        case 12: {
            const auto &g = *static_cast<const Game012KnifeHit *>(game);
            return {double(g.theta), double(g.knife_y), double(g.hits), double(g.flying)};
        }
        case 13: {
            const auto &g = *static_cast<const Game013PendulumToss *>(game);
            return {double(g.x),     double(g.y),    double(g.vx),    double(g.vy),
                    double(g.phase), double(g.hits), double(g.balls), double(g.flying)};
        }
        case 23: {
            const auto &g = *static_cast<const Game023AirHockey *>(game);
            return {double(g.paddle_x), double(g.paddle_y), double(g.ax),
                    double(g.x),        double(g.y),        double(g.vx),
                    double(g.vy),       double(g.goals),    double(g.against)};
        }
        default:
            return {};
        }
    }
};
} // namespace arcade
