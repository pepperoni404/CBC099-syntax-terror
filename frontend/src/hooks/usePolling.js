import { useEffect, useRef } from 'react';

/**
 * Custom polling hook
 * Default polling interval is exactly 5 seconds (5000ms).
 */
export function usePolling(callback, interval = 5000, enabled = true) {
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
