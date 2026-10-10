import { useEffect, useRef } from 'react';

/**
 * Custom polling hook per Section 3.3 of frontend-spec.md
 * Default polling interval is exactly 30 seconds (30000ms).
 */
export function usePolling(callback, interval = 30000, enabled = true) {
  const savedCallback = useRef(callback);

  useEffect(() => {
    savedCallback.current = callback;
  }, [callback]);

  useEffect(() => {
    if (!enabled) return;

    const tick = () => {
      if (savedCallback.current) {
        savedCallback.current();
      }
    };

    // Immediate first call
    tick();

    const id = setInterval(tick, interval);
    return () => clearInterval(id);
  }, [interval, enabled]);
}

export default usePolling;
