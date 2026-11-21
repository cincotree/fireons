'use client';

import { useEffect, useRef, useState } from 'react';

function isPlainObject(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

export function useLocalStorageState<T>(key: string, initialValue: T) {
  const [state, setState] = useState<T>(initialValue);
  const hasHydrated = useRef(false);
  const initialValueRef = useRef(initialValue);

  useEffect(() => {
    try {
      const stored = window.localStorage.getItem(key);
      if (stored !== null) {
        const parsed = JSON.parse(stored);
        const mergedWithDefaults = isPlainObject(parsed) && isPlainObject(initialValueRef.current)
          ? { ...initialValueRef.current, ...parsed }
          : parsed;
        // eslint-disable-next-line react-hooks/set-state-in-effect
        setState(mergedWithDefaults);
      }
    } catch {
      // ignore malformed/inaccessible storage
    }
    hasHydrated.current = true;
  }, [key]);

  useEffect(() => {
    if (!hasHydrated.current) return;
    try {
      window.localStorage.setItem(key, JSON.stringify(state));
    } catch {
      // ignore quota/private-browsing errors
    }
  }, [key, state]);

  return [state, setState] as const;
}
