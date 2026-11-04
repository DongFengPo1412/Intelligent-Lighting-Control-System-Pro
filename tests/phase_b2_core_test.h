#include "../firmware-s3/main/audio/game_audio_stream.h"
#include "game_035_boulder_dash.h"
#include "game_057_rush_hour.h"
#include "game_058_program_robot.h"
#include "game_081_qix.h"
#include "game_098_lunar_lander.h"
#include <filesystem>
#include <sstream>
#define private public
#include "game_055_mirror_laser.h"
#undef private

static void test_b2_audio() {
    using namespace arcade;
    assert(GameWriteFromBytes(160, 640, AudioWriteState::Busy).samples == 80);
    assert(GameWriteFromBytes(160, 0, AudioWriteState::Busy).samples == 0);
    assert(GameWriteFromBytes(160, 1279, AudioWriteState::Ready).state == AudioWriteState::Fault);
    assert(GameWriteFromBytes(160, 1288, AudioWriteState::Ready).state == AudioWriteState::Fault);
    SoundBus bus(sound_clock);
    SoundEvent event;
    sound_now = 1000;
    assert(bus.Emit(Sound::Hit, 92, 1, 11));
    assert(!bus.Emit(Sound::Hit, 92, 1, 11));
    assert(bus.Emit(Sound::Hit, 92, 1, 12));
    assert(bus.Emit(Sound::Hit, 17, 1, 11));
    assert(bus.Emit(Sound::Hit, 92, 2, 11));
    assert(bus.duplicates == 1);
    bus.Invalidate();
    assert(bus.Emit(Sound::Hit, 92, 1, 11));
    bus.Invalidate();
    for (int i = 0; i < 16; ++i)
        assert(bus.Emit(Sound::Hit, 92, i % 4));
    assert(!bus.Emit(Sound::Hit, 92));
    for (int i = 0; i < 16; ++i)
        assert(bus.Pop(event));
    assert(!bus.Pop(event));
    // Short writes and DMA busy: record the accepted prefix and independently
    // compare every sample, not just the final offset or a mock return value.
    sound_now = 2000;
    assert(bus.Emit(Sound::Win, 35));
    SoundEvent expected{Sound::Win, 35, 0, bus.Generation(), sound_now};
    GameAudioStream stream(bus);
    std::vector<int16_t> accepted;
    int calls = 0;
    for (unsigned t = 0; t < 200; ++t) {
        sound_now = 2000 + t;
        stream.Poll(sound_now, [&](const int16_t *pcm, unsigned count) {
            if (++calls <= 2)
                return AudioWriteResult{0, AudioWriteState::Busy};
            unsigned n = std::min(80u, count);
            accepted.insert(accepted.end(), pcm, pcm + n);
            return AudioWriteResult{n, n < count ? AudioWriteState::Busy : AudioWriteState::Ready};
        });
    }
    assert(bus.played == 1 && bus.busy > 0 && bus.short_writes > 0 && bus.late == 0);
    assert(accepted.size() == ToneFor(expected).duration_ms * 16);
    for (unsigned i = 0; i < accepted.size(); ++i)
        assert(accepted[i] == SoundSample(expected, i, 25));
    sound_now = 3000;
    assert(bus.Emit(Sound::Hit, 92));
    for (unsigned t = 0; t < 40; ++t) {
        sound_now = 3000 + t;
        stream.Poll(sound_now, [](const int16_t *, unsigned) {
            return AudioWriteResult{0, AudioWriteState::Busy};
        });
    }
    assert(!stream.Active() && bus.late == 1 && bus.played == 1);
    // Speech/music/capture priority is checked at every write, with no retry of
    // interrupted suffixes after the external priority window has passed.
    AudioPriorityGate gate;
    sound_now = 4000;
    assert(bus.Emit(Sound::Win, 55));
    auto writer = [&](const int16_t *, unsigned n) {
        return gate.GameAllowed(sound_now) ? AudioWriteResult{n, AudioWriteState::Ready}
                                           : AudioWriteResult{0, AudioWriteState::Preempted};
    };
    stream.Poll(sound_now, writer);
    gate.External(4001);
    sound_now = 4010;
    stream.Poll(sound_now, writer);
    assert(bus.preempted == 1 && !stream.Active());
    sound_now = 4600;
    stream.Poll(sound_now, writer);
    assert(bus.played == 1);
    gate.Capture(true);
    assert(bus.Emit(Sound::Hit, 92));
    stream.Poll(sound_now, writer);
    assert(bus.preempted == 2);
    gate.Capture(false);
    sound_now = 4700;
    assert(bus.Emit(Sound::Hit, 92));
    for (unsigned t = 0; t < 50; ++t) {
        sound_now = 4700 + t;
        stream.Poll(sound_now, writer);
    }
    assert(bus.played == 2);
    sound_now = 4800;
    assert(bus.Emit(Sound::Win, 55));
    stream.Poll(sound_now, writer);
    bus.Configure(false, 25);
    sound_now += 10;
    stream.Poll(sound_now, writer);
    assert(!stream.Active());
    bus.Configure(true, 25);
    sound_now = 4900;
    assert(bus.Emit(Sound::Hit, 92));
    stream.Poll(sound_now, [](const int16_t *, unsigned n) {
        return AudioWriteResult{n + 1, AudioWriteState::Ready};
    });
    assert(bus.faults == 1);
    // Scheduling resumes from the sample deadline: a 10ms tick is not followed
    // by an extra fixed sleep proportional to how long the write itself took.
    sound_now = 5000;
    assert(bus.Emit(Sound::Win, 35));
    for (unsigned t = 0; t <= 160; t += 10) {
        sound_now = 5000 + t;
        stream.Poll(sound_now, writer);
    }
    assert(bus.played == 3);
    sound_now = 6000;
    assert(bus.Emit(Sound::Win, 35));
    stream.Poll(sound_now, writer);
    sound_now += 50;
    stream.Poll(sound_now, writer);
    assert(bus.late == 2);
    std::cout << "B2 audio: distinct rapid events, identity dedup, prefix-exact short writes, "
                 "bounded busy/jitter, priority/mute/recovery passed\n";
}

static void test_b2_rounds() {
    using namespace arcade;
    constexpr float dt = 16667.f / 1000000.f;
    auto path =
        std::filesystem::path(__FILE__).parent_path() / "fixtures/phase_b2_input_paths.json";
    std::ifstream input(path);
    assert(input);
    std::stringstream buffer;
    buffer << input.rdbuf();
    auto *json = cJSON_Parse(buffer.str().c_str());
    assert(json);
    auto *cases = cJSON_GetObjectItemCaseSensitive(json, "cases");
    auto &manager = ArcadeManager::GetInstance();
    int count = 0;
    cJSON *row = nullptr;
    cJSON_ArrayForEach(row, cases) {
        int id = cJSON_GetObjectItemCaseSensitive(row, "id")->valueint,
            level = cJSON_GetObjectItemCaseSensitive(row, "difficulty")->valueint;
        assert(manager.SelectGame(id));
        auto *game = manager.current_game_;
        assert(game);
        if (id != 55)
            assert(game->SetDifficulty(level));
        game->Init();
        game->Start();
        game->Pause();
        std::vector<uint8_t> paused(768);
        game->Render(paused.data());
        game->Update(dt, KEY_A, KEY_A);
        assert(game->GetStatus().state == STATE_PAUSED);
        game->Resume();
        cJSON *action = nullptr;
        auto *steps = cJSON_GetObjectItemCaseSensitive(row, "inputs");
        unsigned sound_count = 0;
        Sounds().Invalidate();
        Sounds().Configure(true, 25);
        Sounds().SetClock(sound_clock);
        cJSON_ArrayForEach(action, steps) {
            int n = cJSON_GetArrayItem(action, 0)->valueint,
                down = cJSON_GetArrayItem(action, 1)->valueint,
                pressed = cJSON_GetArrayItem(action, 2)->valueint;
            for (int i = 0; i < n; ++i) {
                sound_now += 17;
                game->Update(dt, down, pressed);
                SoundEvent e;
                while (Sounds().Pop(e))
                    ++sound_count;
            }
            std::vector<uint8_t> guarded(800, 0xa5);
            game->Render(guarded.data() + 16);
            for (int i = 0; i < 16; ++i)
                assert(guarded[i] == 0xa5 && guarded[784 + i] == 0xa5);
        }
        auto status = game->GetStatus();
        if (status.state != STATE_VICTORY)
            std::cerr << "B2 witness failed " << id << " level " << level << " state "
                      << int(status.state) << "\n";
        assert(status.state == STATE_VICTORY && status.score > 0 && sound_count > 0);
        if (id == 58)
            assert(status.progress == 100 && status.lives == 3);
        game->Reset();
        assert(game->GetStatus().state == STATE_TITLE);
        game->Start();
        game->Pause();
        game->Resume();
        assert(game->GetStatus().state == STATE_PLAYING);
        if (id != 55) {
            for (int i = 0; i < 8000 && game->GetStatus().state == STATE_PLAYING; ++i)
                game->Update(dt, 0, 0);
            assert(game->GetStatus().state == STATE_GAMEOVER);
        }
        ++count;
    }
    cJSON_Delete(json);
    assert(count == 16);
    std::cout << "B2 production C++: five new games x three difficulties and all four Mirror Laser "
                 "stages, input-only victory/failure/pause/reset/frame bounds passed\n";
}

namespace arcade {
struct B2MechanismProbe {
    static void Run() {
        using namespace arcade;
        constexpr float dt = 16667.f / 1000000.f;
        // Local deterministic collision fixtures, never used to fake a solved round.
        Game035BoulderDash rocks;
        rocks.Init();
        rocks.Start();
        rocks.Update(dt, 0, KEY_RIGHT);
        assert(rocks.gems_ == 1);
        rocks.grid_[4][5] = 3;
        rocks.grid_[4][6] = 0;
        rocks.x_ = 4;
        rocks.y_ = 4;
        rocks.Update(dt, 0, KEY_RIGHT);
        assert(rocks.x_ == 5 && rocks.grid_[4][6] == 3);
        rocks.x_ = 3;
        rocks.y_ = 5;
        rocks.grid_[3][3] = 3;
        rocks.grid_[4][3] = rocks.grid_[5][3] = 0;
        for (int i = 0; i < 12; ++i)
            rocks.Update(.05f, 0, 0);
        assert(rocks.GetStatus().state == STATE_GAMEOVER);
        Game057RushHour rush;
        rush.SetDifficulty(2);
        rush.Init();
        rush.Start();
        rush.Update(dt, 0, KEY_RIGHT);
        assert(rush.moves_ == 0);
        for (int i = 0; i < 4; ++i)
            rush.Update(dt, 0, KEY_A);
        for (int i = 0; i < 16; ++i)
            rush.Update(dt, 0, i % 2 ? KEY_LEFT : KEY_RIGHT);
        assert(rush.moves_ == 16 && rush.GetStatus().state == STATE_GAMEOVER);
        Game058ProgramRobot robot;
        robot.SetDifficulty(2);
        robot.Init();
        robot.Start();
        for (int i = 0; i < 30; ++i)
            robot.Update(dt, 0, KEY_UP);
        assert(robot.length_ == 14);
        robot.Reset();
        robot.Start();
        for (int i = 0; i < 4; ++i)
            robot.Update(dt, 0, KEY_UP);
        for (int run = 0; run < 3; ++run) {
            robot.Update(dt, 0, KEY_A);
            for (int i = 0; i < 100 && robot.running_; ++i)
                robot.Update(dt, 0, 0);
            assert(robot.attempts_ == 2 - run);
        }
        assert(robot.GetStatus().state == STATE_GAMEOVER);
        Game081Qix qix;
        qix.Init();
        qix.Start();
        for (auto key : {KEY_A, KEY_RIGHT, KEY_RIGHT, KEY_DOWN, KEY_LEFT, KEY_UP})
            qix.Update(dt, 0, key);
        assert(qix.GetStatus().state == STATE_GAMEOVER);
        qix.Reset();
        qix.Start();
        qix.grid_[qix.ey_ + qix.vy_][qix.ex_ + qix.vx_] = 2;
        for (int i = 0; i < 10; ++i)
            qix.Update(dt, 0, 0);
        assert(qix.GetStatus().state == STATE_GAMEOVER);
        Game098LunarLander lander;
        lander.Init();
        lander.Start();
        float fuel = lander.fuel_;
        for (int i = 0; i < 10; ++i)
            lander.Update(.05f, KEY_A | KEY_RIGHT, 0);
        assert(lander.fuel_ < fuel && lander.vx_ > 0 && lander.angle_ > 0);
        lander.x_ = 8;
        lander.y_ = 12.99f;
        lander.vy_ = 3;
        lander.Update(dt, 0, 0);
        assert(lander.GetStatus().state == STATE_GAMEOVER);
        Game055MirrorLaser laser;
        laser.Init();
        laser.Start();
        for (int lives = 2; lives >= 0; --lives) {
            laser.Update(dt, 0, KEY_A);
            for (int i = 0; i < 60; ++i)
                laser.Update(dt, 0, 0);
            assert(laser.lives_ == lives + 1);
            laser.Update(dt, 0, KEY_B);
            for (int i = 0; i < 35; ++i)
                laser.Update(dt, 0, 0);
            assert(laser.lives_ == lives);
        }
        assert(laser.GetStatus().state == STATE_GAMEOVER);
        std::cout << "B2 directed production mechanics: rock crush/push, blocked vehicles/budget, "
                     "program gate/failures, Qix trail/enemy, unsafe landings, safe laser "
                     "edit/fire passed\n";
    }
};
} // namespace arcade
static void test_b2_mechanisms() { arcade::B2MechanismProbe::Run(); }
