import Image from "next/image";

const SIZES = {
  sm: { w: 82, h: 22 },
  md: { w: 112, h: 30 },
  lg: { w: 165, h: 44 },
};

export function Logo({ size = "md" }: { size?: "sm" | "md" | "lg" }) {
  const { w, h } = SIZES[size];
  return (
    <Image
      src="/brand/futurus-logo-dark.svg"
      alt="Futurus"
      width={w}
      height={h}
      className="shrink-0"
      unoptimized
    />
  );
}
