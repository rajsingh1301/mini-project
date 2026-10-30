import { useEffect } from "react";
import { t } from "../lib/i18n.js";

/** Screen readers and the browser title follow the interface language. */
export function usePageLanguage(lang) {
  useEffect(() => {
    document.documentElement.lang = lang;
    document.title = t(lang, "appName");
  }, [lang]);
}
