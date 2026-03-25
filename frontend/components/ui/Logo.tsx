import Image from "next/image";

export function Logo({ size = "md" }: { size?: "sm" | "md" | "lg" }) {
  const sizes = { sm: 20, md: 28, lg: 40 };
  const px = sizes[size];
  const textSizes = { sm: "text-sm", md: "text-lg", lg: "text-2xl" };

  return (
    <div className="flex items-center gap-2.5">
      <Image
        src="/brand/futurus-mark.svg"
        alt=""
        width={px}
        height={px}
        className="shrink-0"
        unoptimized
        aria-hidden
      />
      <span
        style={{ fontFamily: "var(--font-serif), Georgia, serif" }}
        className={`${textSizes[size]} font-normal tracking-tight text-white`}
      >
        Futurus
      </span>
    </div>
  );
}
