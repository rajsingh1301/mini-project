import { useEffect, useRef } from "react";

/** Native focus trapping, with background scrolling paused while settings is open. */
export function useDialog(open) {
  const ref = useRef(null);
  useEffect(() => {
    const dialog = ref.current;
    if (!dialog) return undefined;
    if (!open) {
      if (dialog.open) dialog.close();
      return undefined;
    }
    if (!dialog.open) dialog.showModal();
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.body.style.overflow = previousOverflow;
    };
  }, [open]);
  return ref;
}
