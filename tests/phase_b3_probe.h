#pragma once
#include "game_007_downwell.h"
#include "game_008_jump_king.h"
#include "game_011_dino_runner.h"
#include "game_012_knife_hit.h"
#include "game_013_pendulum_toss.h"
#include "game_023_air_hockey.h"
#include "game_024_peggle.h"
#include "game_025_marble_maze.h"
#include "game_032_defender.h"
#include "game_036_dig_dug.h"
#include "game_037_qbert.h"
#include "game_039_fog_maze.h"
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
        case 24: {
            const auto &g = *static_cast<const Game024Peggle *>(game);
            return {double(g.aim), double(g.x),    double(g.y),     double(g.vx),
                    double(g.vy),  double(g.mask), double(g.balls), double(g.flying)};
        }
        case 25: {
            const auto &g = *static_cast<const Game025MarbleMaze *>(game);
            return {double(g.x), double(g.y), double(g.vx), double(g.vy)};
        }
        case 32: {
            const auto &g = *static_cast<const Game032Defender *>(game);
            return {double(g.x),          double(g.y),        double(g.hp),
                    double(g.kills),      double(g.ey[0]),    double(g.ey[1]),
                    double(g.ey[2]),      double(g.ey[3]),    double(g.human[0]),
                    double(g.human[1]),   double(g.human[2]), double(g.human[3]),
                    double(g.carrying[0])};
        }
        case 36: {
            const auto &g = *static_cast<const Game036DigDug *>(game);
            return {double(g.x),     double(g.y),     double(g.face),  double(g.hp),
                    double(g.kills), double(g.ex[0]), double(g.ey[0]), double(g.inflate[0]),
                    double(g.ex[1]), double(g.ey[1]), double(g.ex[2]), double(g.ey[2])};
        }
        case 37: {
            const auto &g = *static_cast<const Game037Qbert *>(game);
            return {double(g.row), double(g.col), double(g.er),
                    double(g.ec),  double(g.hp),  double(g.mask)};
        }
        case 39: {
            const auto &g = *static_cast<const Game039FogMaze *>(game);
            return {double(g.x), double(g.y), double(g.moves), double(g.explored),
                    double(g.layout_hash)};
        }
        default:
            return {};
        }
    }
};
} // namespace arcade
