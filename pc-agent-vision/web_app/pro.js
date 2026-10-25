/* Compatibility entry only. All controls live in index.html + app.js. */
"use strict";
const legacyPages = {
  musicLibrary: "music",
  music: "music",
  matrix: "lights",
  arcade: "interaction",
  system: "settings",
};
const requested = location.hash.slice(1);
location.replace(
  "./#" +
    (legacyPages[requested] ||
      (["overview", "lights", "interaction", "settings"].includes(requested)
        ? requested
        : "overview")),
);
