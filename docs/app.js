/* gitku web UI: fetches commits from GitHub's public API and runs them through gitku.js. */
(function () {
  "use strict";

  var $ = function (id) { return document.getElementById(id); };
  var PAGE = 12; // cards shown per "show more"
  var state = { poems: [], shown: 0, repo: "", running: 0 };

  var SEAL = '<svg class="seal" viewBox="0 0 32 32" aria-hidden="true"><rect width="32" height="32" rx="9" fill="currentColor"/><g fill="#fff"><rect x="8" y="9" width="11.4" height="3" rx="1.5"/><rect x="8" y="14.5" width="16" height="3" rx="1.5"/><rect x="8" y="20" width="11.4" height="3" rx="1.5"/></g></svg>';
  var CROWN = '<svg class="crown" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M3 8l4.5 4L12 5l4.5 7L21 8l-2 11H5L3 8Z"/></svg>';

  /* ---------- small helpers ---------- */

  function el(tag, cls, text) {
    var n = document.createElement(tag);
    if (cls) n.className = cls;
    if (text != null) n.textContent = text;
    return n;
  }

  function safeUrl(u) {
    return typeof u === "string" && /^https:\/\/(github\.com|avatars\.githubusercontent\.com)\//.test(u) ? u : null;
  }

  function parseRepo(raw) {
    var s = String(raw || "").trim();
    s = s.replace(/^https?:\/\/(www\.)?github\.com\//i, "").replace(/^github\.com\//i, "");
    s = s.replace(/\.git$/i, "").replace(/[?#].*$/, "").replace(/\/+$/, "");
    var m = /^([A-Za-z0-9](?:[A-Za-z0-9-]{0,38}))\/([A-Za-z0-9._-]{1,100})/.exec(s);
    return m ? m[1] + "/" + m[2] : null;
  }

  function setStatus(kind, msg, sub, progress) {
    var box = $("status");
    box.hidden = false;
    box.className = "status" + (kind === "error" ? " error" : "");
    box.textContent = "";
    box.appendChild(el("p", "msg", msg));
    if (sub) box.appendChild(el("p", "sub", sub));
    if (progress != null) {
      var bar = el("div", "bar");
      var i = document.createElement("i");
      i.style.width = Math.round(progress * 100) + "%";
      bar.appendChild(i);
      box.appendChild(bar);
    }
  }

  function clearStatus() { var b = $("status"); b.hidden = true; b.textContent = ""; }

  /* ---------- GitHub ---------- */

  function fetchCommits(repo, want, onProgress) {
    var out = [];
    function page(n) {
      var url = "https://api.github.com/repos/" + repo + "/commits?per_page=100&page=" + n;
      return fetch(url, { headers: { Accept: "application/vnd.github+json" } }).then(function (res) {
        if (res.status === 404) throw userError("I can't find " + repo + ". Check the spelling, and that it's public.");
        if (res.status === 403 || res.status === 429) {
          var reset = res.headers.get("x-ratelimit-reset");
          var when = reset ? new Date(Number(reset) * 1000).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }) : "a little while";
          throw userError("GitHub's anonymous rate limit is used up.", "It resets around " + when + ". The command line tool has no such limit.");
        }
        if (res.status === 409) throw userError("That repository is empty.");
        if (!res.ok) throw userError("GitHub answered with an error (" + res.status + ").");
        return res.json();
      }).then(function (batch) {
        out = out.concat(batch);
        onProgress(Math.min(1, out.length / want));
        if (batch.length < 100 || out.length >= want) return out.slice(0, want);
        return page(n + 1);
      });
    }
    return page(1);
  }

  function userError(msg, sub) { var e = new Error(msg); e.sub = sub; e.user = true; return e; }

  /* ---------- rendering ---------- */

  function renderCard(p, i) {
    var card = el("article", "card");
    card.style.setProperty("--i", String(i % PAGE));
    card.insertAdjacentHTML("beforeend", SEAL);

    var poem = el("p", "poem");
    p.lines.forEach(function (l) { poem.appendChild(el("span", null, l)); });
    card.appendChild(poem);

    var credit = el("div", "credit");
    var av = safeUrl(p.meta.avatar);
    if (av) {
      var img = el("img", "avatar");
      img.src = av + (av.indexOf("?") < 0 ? "?s=56" : "&s=56");
      img.alt = "";
      img.loading = "lazy";
      img.width = 28; img.height = 28;
      credit.appendChild(img);
    } else {
      credit.appendChild(el("span", "avatar"));
    }
    var who = el("div", "who");
    who.appendChild(el("b", null, p.meta.author));
    var link = el("a", null, p.meta.sha + (p.meta.date ? " · " + p.meta.date : ""));
    var u = safeUrl(p.meta.url);
    if (u) { link.href = u; link.target = "_blank"; link.rel = "noopener"; }
    who.appendChild(link);
    credit.appendChild(who);
    if (p.intentional) credit.appendChild(el("span", "tag", "on purpose"));
    card.appendChild(credit);

    var actions = el("div", "actions");
    var copy = el("button", "act", "Copy");
    copy.type = "button";
    copy.addEventListener("click", function () {
      copyText(p.lines.join("\n") + "\n— " + p.meta.author + ", " + state.repo + "@" + p.meta.sha).then(function () {
        flash(copy, "Copied", "Copy");
      });
    });
    var png = el("button", "act", "Save image");
    png.type = "button";
    png.addEventListener("click", function () { saveImage(p); });
    var tweet = el("a", "act", "Share");
    tweet.href = "https://twitter.com/intent/tweet?text=" + encodeURIComponent(
      p.lines.join("\n") + "\n\nan accidental haiku from " + state.repo + "'s git history\n") +
      "&url=" + encodeURIComponent("https://pzr6m.github.io/gitku/?repo=" + state.repo);
    tweet.target = "_blank"; tweet.rel = "noopener";
    actions.appendChild(copy); actions.appendChild(png); actions.appendChild(tweet);
    card.appendChild(actions);
    return card;
  }

  function showMore() {
    var grid = $("grid");
    var end = Math.min(state.poems.length, state.shown + PAGE);
    for (var i = state.shown; i < end; i++) grid.appendChild(renderCard(state.poems[i], i));
    state.shown = end;
    $("more").hidden = state.shown >= state.poems.length;
  }

  function renderBoard(rows) {
    var list = $("board");
    list.textContent = "";
    rows.slice(0, 10).forEach(function (r, i) {
      var li = el("li");
      li.appendChild(el("span", "rank", String(i + 1)));
      var av = safeUrl(r.avatar);
      if (av) {
        var img = el("img", "avatar");
        img.src = av + (av.indexOf("?") < 0 ? "?s=80" : "&s=80");
        img.alt = ""; img.loading = "lazy"; img.width = 40; img.height = 40;
        li.appendChild(img);
      } else li.appendChild(el("span", "avatar"));
      var name = el("div", "name");
      if (i === 0) name.insertAdjacentHTML("beforeend", CROWN);
      name.appendChild(el("span", null, r.author));
      li.appendChild(name);
      var count = el("div", "count");
      count.appendChild(el("b", null, String(r.total)));
      count.appendChild(document.createTextNode(r.total === 1 ? "haiku" : "haiku"));
      li.appendChild(count);
      li.appendChild(el("p", "best", r.best.lines.join(" / ")));
      list.appendChild(li);
    });
    $("board-wrap").hidden = rows.length < 2;
  }

  function showResults(repo, poems, scanned) {
    state.poems = poems; state.shown = 0; state.repo = repo;
    $("grid").textContent = "";
    var accidental = poems.filter(function (p) { return !p.intentional; }).length;
    $("results-title").textContent = poems.length ? repo : repo;
    var stats = $("stats");
    stats.textContent = "";
    if (poems.length) {
      var b = document.createElement("b");
      b.textContent = String(poems.length);
      stats.appendChild(b);
      stats.appendChild(document.createTextNode(
        (poems.length === 1 ? " haiku" : " haiku") + " in " + scanned + " commits · " + accidental + " by accident"));
    }
    $("results").hidden = false;
    if (!poems.length) {
      var empty = el("div", "status");
      empty.style.gridColumn = "1 / -1";
      empty.appendChild(el("p", "msg", "No haiku in the last " + scanned + " commits."));
      empty.appendChild(el("p", "sub", "Short, tidy messages rarely scan as 5-7-5. Try “Also look inside long messages”, or read more commits."));
      $("grid").appendChild(empty);
      $("more").hidden = true;
      $("board-wrap").hidden = true;
      return;
    }
    showMore();
    renderBoard(Gitku.laureate(poems));
  }

  /* ---------- actions ---------- */

  function copyText(text) {
    if (navigator.clipboard && navigator.clipboard.writeText) {
      return navigator.clipboard.writeText(text).catch(function () { return legacyCopy(text); });
    }
    return Promise.resolve(legacyCopy(text));
  }
  function legacyCopy(text) {
    var ta = document.createElement("textarea");
    ta.value = text; ta.style.position = "fixed"; ta.style.opacity = "0";
    document.body.appendChild(ta); ta.select();
    try { document.execCommand("copy"); } catch (e) { /* ignore */ }
    document.body.removeChild(ta);
  }
  function flash(btn, on, off) {
    btn.textContent = on;
    setTimeout(function () { btn.textContent = off; }, 1400);
  }

  function saveImage(p) {
    var dark = document.documentElement.getAttribute("data-theme") === "dark";
    var c = dark
      ? { bg: "#131210", ink: "#f1ebde", muted: "#8f8772", accent: "#e6664a", line: "#2d2a23" }
      : { bg: "#f3eee2", ink: "#1c1a16", muted: "#857d6a", accent: "#c4432b", line: "#ddd4c0" };
    var W = 1200, H = 630, S = 2;
    var cv = document.createElement("canvas");
    cv.width = W * S; cv.height = H * S;
    var g = cv.getContext("2d");
    g.scale(S, S);
    g.fillStyle = c.bg; g.fillRect(0, 0, W, H);

    // seal
    g.fillStyle = c.accent;
    roundRect(g, W - 128, 64, 56, 56, 16); g.fill();
    g.fillStyle = "#fff";
    [[0, 0, 24], [0, 11, 34], [0, 22, 24]].forEach(function (r) { roundRect(g, W - 128 + 11 + r[0], 64 + 14 + r[1], r[2], 6, 3); g.fill(); });

    var serif = '"Fraunces", "Iowan Old Style", Georgia, serif';
    g.fillStyle = c.ink; g.textBaseline = "alphabetic";
    var size = 62;
    g.font = "italic 400 " + size + "px " + serif;
    var widest = Math.max.apply(null, p.lines.map(function (l) { return g.measureText(l).width; })) + 70;
    if (widest > W - 200) { size = Math.floor(size * (W - 200) / widest); g.font = "italic 400 " + size + "px " + serif; }
    var y = 220;
    p.lines.forEach(function (l, i) {
      g.fillText(l, 96 + (i === 1 ? 60 : 0), y);
      y += size * 1.45;
    });

    g.strokeStyle = c.line; g.lineWidth = 2;
    g.beginPath(); g.moveTo(96, H - 120); g.lineTo(W - 96, H - 120); g.stroke();
    g.font = '600 26px "Inter", system-ui, sans-serif';
    g.fillStyle = c.ink;
    g.fillText(p.meta.author, 96, H - 66);
    g.font = '22px "JetBrains Mono", ui-monospace, monospace';
    g.fillStyle = c.muted;
    g.fillText(state.repo + "@" + p.meta.sha, 96, H - 32);
    g.textAlign = "right";
    g.fillStyle = c.accent;
    g.font = 'italic 500 30px ' + serif;
    g.fillText("gitku", W - 96, H - 40);

    cv.toBlob(function (blob) {
      if (!blob) return;
      var a = document.createElement("a");
      a.href = URL.createObjectURL(blob);
      a.download = "gitku-" + state.repo.replace("/", "-") + "-" + p.meta.sha + ".png";
      document.body.appendChild(a); a.click(); document.body.removeChild(a);
      setTimeout(function () { URL.revokeObjectURL(a.href); }, 2000);
    }, "image/png");
  }

  function roundRect(g, x, y, w, h, r) {
    g.beginPath();
    g.moveTo(x + r, y); g.arcTo(x + w, y, x + w, y + h, r); g.arcTo(x + w, y + h, x, y + h, r);
    g.arcTo(x, y + h, x, y, r); g.arcTo(x, y, x + w, y, r); g.closePath();
  }

  /* ---------- main flow ---------- */

  function run(raw, pushUrl) {
    var repo = parseRepo(raw);
    if (!repo) { setStatus("error", "That doesn't look like owner/repo.", "Try something like pallets/flask."); return; }
    var token = ++state.running;
    var depth = Number($("depth").value) || 300;
    var loose = $("loose").checked;
    $("repo").value = repo;
    $("results").hidden = true;
    $("go").disabled = true;
    setStatus("info", "Reading " + repo + "…", "Counting syllables in commit messages", 0.02);
    if (pushUrl && window.history && history.replaceState) {
      try { history.replaceState(null, "", "?repo=" + repo); } catch (e) { /* file:// etc. */ }
    }

    fetchCommits(repo, depth, function (f) {
      if (token === state.running) setStatus("info", "Reading " + repo + "…", "Counting syllables in commit messages", f);
    }).then(function (commits) {
      if (token !== state.running) return;
      var res = Gitku.scanCommits(commits, { loose: loose, minScore: loose ? 0.7 : 0.5 });
      clearStatus();
      showResults(repo, res.poems, res.commits);
      var r = $("results");
      if (r.scrollIntoView) r.scrollIntoView({ behavior: "smooth", block: "start" });
    }).catch(function (e) {
      if (token !== state.running) return;
      if (e && e.user) setStatus("error", e.message, e.sub);
      else setStatus("error", "Couldn't reach GitHub.", "Check your connection and try again.");
    }).then(function () {
      if (token === state.running) $("go").disabled = false;
    });
  }

  document.addEventListener("DOMContentLoaded", function () {
    // give the submit button an id for enable/disable
    document.querySelector(".go").id = "go";

    $("finder").addEventListener("submit", function (e) { e.preventDefault(); run($("repo").value, true); });
    Array.prototype.forEach.call(document.querySelectorAll(".chip"), function (b) {
      b.addEventListener("click", function () { run(b.getAttribute("data-repo"), true); });
    });
    $("more").addEventListener("click", showMore);

    $("theme").addEventListener("click", function () {
      var root = document.documentElement;
      var next = root.getAttribute("data-theme") === "dark" ? "light" : "dark";
      root.setAttribute("data-theme", next);
      try { localStorage.setItem("gitku-theme", next); } catch (e) { /* private mode */ }
      var m = document.querySelector('meta[name="theme-color"]');
      if (m) m.setAttribute("content", next === "dark" ? "#131210" : "#f3eee2");
    });

    $("copy-cmd").addEventListener("click", function () {
      copyText($("cmd").textContent).then(function () { flash($("copy-cmd"), "Copied", "Copy"); });
    });

    var q = new URLSearchParams(location.search).get("repo");
    if (q) run(q, false);
  });
})();
