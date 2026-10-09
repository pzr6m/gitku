// Reads {words, texts, messages} as JSON on stdin; prints what the web engine makes of them.
// tests/test_web_parity.py compares this with the Python package, which must agree exactly.
const G = require("../../docs/gitku.js");

let input = "";
process.stdin.on("data", (chunk) => (input += chunk));
process.stdin.on("end", () => {
  const data = JSON.parse(input);
  // null-prototype object so adversarial keys like "__proto__" are stored as plain keys
  const out = { words: Object.create(null), texts: [], clean: [] };
  for (const w of data.words) out.words[w] = G.countWord(w);
  for (const t of data.texts) {
    const toks = G.tokenize(t);
    out.texts.push({
      tokens: toks.map((x) => [x.text, x.core, x.syllables]),
      strict: G.findWindows(toks, true).map((w) => [w.lines, w.score]),
      loose: G.findWindows(toks, false).map((w) => [w.lines, w.start, w.end, w.score]),
    });
  }
  for (const m of data.messages) out.clean.push(G.cleanMessage(m));
  process.stdout.write(JSON.stringify(out));
});
