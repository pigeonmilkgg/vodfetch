/* Injects a floating "Download" button on Twitch VOD & clip pages.
   Click → opens the Twitch Downloader web app with the current link prefilled. */
(function () {
  // ↓ Change this to your own domain once it's set up (e.g. https://vodfetch.com/)
  var SITE = "https://vodfetch.com/";

  function isTarget() {
    var u = location.href;
    return /twitch\.tv\/videos\/\d+/.test(u) ||
           /clips\.twitch\.tv\/[A-Za-z0-9_-]+/.test(u) ||
           /twitch\.tv\/[^/]+\/clips?\//.test(u);
  }

  var btn = null;
  function ensure() {
    if (!isTarget()) { if (btn) { btn.remove(); btn = null; } return; }
    if (btn) return;
    btn = document.createElement("a");
    btn.textContent = "⬇ Download";
    btn.title = "Download this Twitch video as MP4";
    var s = btn.style;
    s.position = "fixed"; s.zIndex = "999999"; s.right = "18px"; s.bottom = "18px";
    s.background = "#9147ff"; s.color = "#fff";
    s.font = "600 14px/1 Inter,-apple-system,Arial,sans-serif";
    s.padding = "12px 16px"; s.borderRadius = "10px"; s.textDecoration = "none";
    s.boxShadow = "0 6px 20px rgba(0,0,0,.4)"; s.cursor = "pointer";
    btn.addEventListener("click", function (e) {
      e.preventDefault();
      window.open(SITE + "?url=" + encodeURIComponent(location.href) + "&go=1", "_blank", "noopener");
    });
    document.body.appendChild(btn);
  }

  ensure();
  // Twitch is a single-page app → re-check the URL periodically.
  var last = location.href;
  setInterval(function () { if (location.href !== last) { last = location.href; ensure(); } }, 1200);
})();
