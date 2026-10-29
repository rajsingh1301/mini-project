import { test } from "node:test";
import assert from "node:assert/strict";
import { arrowFor, fitSize, kindFor, sameText, vibrationFor, zoneSummary } from "./guidance.js";

test("sameText ignores case, punctuation and small OCR differences", () => {
  assert.ok(sameText("EXIT", "exit"));
  assert.ok(sameText("Room 204 Computer Lab", "Room 204, Computer Lab."));
  assert.ok(!sameText("Room 204", "Toilets this way"));
  assert.ok(!sameText("", "EXIT"));
});

test("arrowFor follows the direction word", () => {
  assert.equal(arrowFor("Chair on your left"), "←");
  assert.equal(arrowFor("Caution, stairs on your right"), "→");
  assert.equal(arrowFor("Stop! person ahead"), "↑");
  assert.equal(arrowFor("Path clear"), "✓");
});

test("kindFor and vibrationFor treat stop and stairs as urgent", () => {
  assert.equal(kindFor("Stop! stairs ahead", true), "stop");
  assert.equal(kindFor("Path clear", false), "clear");
  assert.equal(kindFor("Door on your left", false), "info");
  assert.deepEqual(vibrationFor("Stop! person ahead", true), [300, 100, 300]);
  assert.ok(vibrationFor("Stairs ahead, slow down", false));
  assert.equal(vibrationFor("Chair on your left", false), null);
});

test("zoneSummary keeps the closest object in each zone", () => {
  const zones = zoneSummary([
    { label: "chair", direction: "left", proximity: "far", confidence: 0.9 },
    { label: "person", direction: "left", proximity: "near", confidence: 0.5 },
    { label: "door", direction: "ahead", proximity: "far", confidence: 0.7 },
  ]);
  assert.equal(zones.left.label, "person");
  assert.equal(zones.ahead.label, "door");
  assert.equal(zones.right, null);
});

test("fitSize keeps aspect ratio and never upscales", () => {
  assert.deepEqual(fitSize(1920, 1080, 640), { width: 640, height: 360 });
  assert.deepEqual(fitSize(720, 1280, 640), { width: 360, height: 640 });
  assert.deepEqual(fitSize(320, 240, 640), { width: 320, height: 240 });
});
