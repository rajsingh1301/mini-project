import { test } from "node:test";
import assert from "node:assert/strict";
import { LANGUAGES, STRING_TABLES, detectLanguage, languageInfo, nextLanguage, t } from "./i18n.js";

const placeholders = (text) => [...text.matchAll(/\{(\w+)\}/g)].map((m) => m[1]).sort();

test("every language has every message, with the same placeholders", () => {
  const english = Object.keys(STRING_TABLES.en);
  for (const { code } of LANGUAGES) {
    assert.deepEqual(Object.keys(STRING_TABLES[code]).sort(), [...english].sort(), `keys of ${code}`);
    for (const key of english) {
      assert.deepEqual(placeholders(STRING_TABLES[code][key]), placeholders(STRING_TABLES.en[key]), `${code}.${key}`);
      assert.ok(STRING_TABLES[code][key].trim(), `${code}.${key} is empty`);
    }
  }
});

test("t fills placeholders and falls back to English, then to the key", () => {
  assert.equal(t("en", "switchLanguage", { language: "Hindi" }), "Switch language to Hindi");
  assert.equal(t("hi", "stop"), "रोकें");
  assert.equal(t("fr", "stop"), "Stop");
  assert.equal(t("en", "no such key"), "no such key");
  assert.equal(t("en", "switchLanguage", {}), "Switch language to {language}");
});

test("detectLanguage picks the first supported browser language", () => {
  assert.equal(detectLanguage(["hi-IN", "en-US"]), "hi");
  assert.equal(detectLanguage(["fr-FR", "HI"]), "hi");
  assert.equal(detectLanguage(["fr-FR", "de"]), "en");
  assert.equal(detectLanguage(undefined), "en");
});

test("nextLanguage cycles and languageInfo falls back to English", () => {
  assert.equal(nextLanguage("en"), "hi");
  assert.equal(nextLanguage("hi"), "en");
  assert.equal(languageInfo("hi").speech, "hi-IN");
  assert.equal(languageInfo("xx").code, "en");
});
