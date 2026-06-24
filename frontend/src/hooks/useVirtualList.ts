import { useState, useRef, useCallback, useEffect } from 'react';

interface UseVirtualListOptions {
  itemHeight: number;
  overscan?: number;
}

export function useVirtualList<T>(items: T[], options: UseVirtualListOptions) {
  const { itemHeight, overscan = 5 } = options;
  const containerRef = useRef<HTMLDivElement>(null);
  const [scrollTop, setScrollTop] = useState(0);

  const totalHeight = items.length * itemHeight;
  const containerHeight = containerRef.current?.clientHeight || 0;

  const startIndex = Math.max(0, Math.floor(scrollTop / itemHeight) - overscan);
  const endIndex = Math.min(
    items.length - 1,
    Math.ceil((scrollTop + containerHeight) / itemHeight) + overscan
  );

  const visibleItems = items.slice(startIndex, endIndex + 1);
  const offsetY = startIndex * itemHeight;

  const onScroll = useCallback((e: React.UIEvent<HTMLDivElement>) => {
    setScrollTop(e.currentTarget.scrollTop);
  }, []);

  // Recalculate on resize
  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    const resizeObserver = new ResizeObserver(() => {
      setScrollTop(el.scrollTop);
    });
    resizeObserver.observe(el);
    return () => resizeObserver.disconnect();
  }, []);

  return {
    containerRef,
    visibleItems,
    totalHeight,
    offsetY,
    onScroll,
    startIndex,
  };
}
