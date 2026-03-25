import { useEffect, useState } from "react";

export function useCountUp(target: number, duration = 1200, decimals = 0): number {
  const [value, setValue] = useState(0);

  useEffect(() => {
    if (target === 0) {
      setValue(0);
      return;
    }
    let startTime: number | undefined;
    let frameId: number;

    const step = (timestamp: number) => {
      if (startTime === undefined) startTime = timestamp;
      const progress = Math.min((timestamp - startTime) / duration, 1);
      const eased = 1 - Math.pow(1 - progress, 3);
      const next = parseFloat((eased * target).toFixed(decimals));
      setValue(next);
      if (progress < 1) frameId = requestAnimationFrame(step);
    };

    setValue(0);
    frameId = requestAnimationFrame(step);
    return () => cancelAnimationFrame(frameId);
  }, [target, duration, decimals]);

  return value;
}
