import { READ_ONLY } from "../../api/backend";
import { useEffect, useState } from "react";

const NARROW = "(max-width: 700px)";

function narrow(): boolean {
  return typeof window.matchMedia === "function"
    ? window.matchMedia(NARROW).matches
    : false;
}

/** The phone layout: the phone link always, or any window as narrow as a phone. */
export default function usePhoneLayout(): boolean {
  const [isNarrow, setNarrow] = useState(narrow);
  useEffect(() => {
    if (typeof window.matchMedia !== "function") {
      return;
    }
    const query = window.matchMedia(NARROW);
    const onChange = () => setNarrow(query.matches);
    query.addEventListener("change", onChange);
    return () => query.removeEventListener("change", onChange);
  }, []);
  return READ_ONLY || isNarrow;
}
