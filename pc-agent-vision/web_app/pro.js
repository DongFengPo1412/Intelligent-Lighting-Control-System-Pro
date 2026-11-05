/* Compatibility entry only. All controls live in index.html + app.js. */
"use strict";
const legacyPages = {
  musicLibrary: "music",
  music: "music",
  matrix: "lights",
  arcade: "interaction",
  system: "settings",
  mario: "mario",
  marioContainer: "mario",
};
const requested = location.pathname.endsWith("/mario_controller.html") ? "mario" : location.hash.slice(1);
location.replace(
  "./index.html#" +
    (legacyPages[requested] ||
      (["overview", "lights", "interaction", "settings"].includes(requested)
        ? requested
        : "overview")),
);
