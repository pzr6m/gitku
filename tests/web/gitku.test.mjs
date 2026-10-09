// Run with: node --test tests/web/gitku.test.mjs
import test from "node:test";
import assert from "node:assert/strict";
import { createRequire } from "node:module";

const G = createRequire(import.meta.url)("../../docs/gitku.js");

const commit = (sha, name, message, extra = {}) => ({
  sha,
  html_url: `https://github.com/o/r/commit/${sha}`,
  commit: { message, author: { name, date: "2025-03-04T12:00:00Z" } },
  author: { login: name.split(" ")[0].toLowerCase(), avatar_url: `https://avatars.example/${name}` },
  parents: [{ sha: "p" }],
  ...extra,
});

test("counts syllables", () => {
  assert.equal(G.countWord("api"), 3);
  assert.equal(G.countWord("playing"), 2);
  assert.equal(G.countWord("isn't"), 2);
  assert.equal(G.countWord("v2"), null);
});

test("finds a whole-message haiku", () => {
  const w = G.findWindows(G.tokenize("the build is broken nobody touched the config and yet here we are"), true);
  assert.deepEqual(w[0].lines, ["the build is broken", "nobody touched the config", "and yet here we are"]);
});

test("scans commits, skipping merges and cleaning trailers", () => {
  const { poems, commits } = G.scanCommits([
    commit("aaaaaaa111", "Ada Lovelace", "the build is broken nobody touched the config and yet here we are"),
    commit("bbbbbbb222", "Linus Example", "stop the retry loop before it eats the whole queue or we all lose sleep\n\nCo-Authored-By: X <x@y.z>"),
    commit("ccccccc333", "Ada Lovelace", "update dependencies"),
    commit("ddddddd444", "Merger", "the build is broken nobody touched the config and yet here we are", { parents: [{}, {}] }),
  ]);
  assert.equal(commits, 3); // the merge commit is not scanned
  assert.equal(poems.length, 2);
  assert.deepEqual(poems.map((p) => p.meta.sha).sort(), ["aaaaaaa", "bbbbbbb"]);
  assert.equal(poems[0].meta.date, "2025-03-04");
  assert.ok(poems.every((p) => !p.intentional));
});

test("flags deliberate three-line haiku as intentional and dedupes", () => {
  const msg = "the old cache is gone\nwe cleared it out of our disks\nspace returns to us";
  const { poems } = G.scanCommits([commit("eeeeeee555", "Ada Lovelace", msg)]);
  assert.equal(poems.length, 1);
  assert.equal(poems[0].intentional, true);
});

test("loose mode finds haiku hidden in a longer message", () => {
  const msg = "tidy retry logic\n\nCleaned up retries. The logs are quiet, the pager sleeps through the night, and nobody weeps.";
  const strict = G.scanCommits([commit("fffffff666", "Grace Hopper", msg)]);
  const loose = G.scanCommits([commit("fffffff666", "Grace Hopper", msg)], { loose: true });
  assert.equal(strict.poems.length, 0);
  assert.deepEqual(loose.poems[0].lines, ["The logs are quiet,", "the pager sleeps through the night,", "and nobody weeps."]);
});

test("ranks the poet laureate by accidental poems", () => {
  const { poems } = G.scanCommits([
    commit("a1", "Ada Lovelace", "the build is broken nobody touched the config and yet here we are"),
    commit("a2", "Ada Lovelace", "stop the retry loop before it eats the whole queue or we all lose sleep"),
    commit("b1", "Grace Hopper", "the old cache is gone\nwe cleared it out of our disks\nspace returns to us"),
  ]);
  const rows = G.laureate(poems);
  assert.equal(rows[0].author, "Ada Lovelace");
  assert.equal(rows[0].accidental, 2);
  assert.equal(rows[1].author, "Grace Hopper");
  assert.equal(rows[1].intentional, 1);
  assert.ok(rows[0].avatar.startsWith("https://avatars.example/"));
});

test("handles empty and odd input without throwing", () => {
  assert.deepEqual(G.scanCommits([]).poems, []);
  assert.deepEqual(G.scanCommits([{ sha: "x", commit: { message: "" } }]).poems, []);
  assert.deepEqual(G.poemsFromMessage("   \n  ", {}), []);
});
