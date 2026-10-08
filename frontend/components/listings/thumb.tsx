"use client";
import { ImageOff } from "lucide-react";
import { useState } from "react";
import { imageUrl } from "@/lib/api";
import type { ImageOut } from "@/lib/types";

export function Thumb({ image, alt, size = 48, className = "" }: { image: ImageOut | null | undefined; alt: string; size?: number; className?: string }) {
  const [err, setErr] = useState(false);
  const src = imageUrl(image?.url);
  return (
    <div className={`flex shrink-0 items-center justify-center overflow-hidden rounded border border-border bg-elev-2 ${className}`} style={{ width: size, height: size }}>
      {src && !err ? (
        // eslint-disable-next-line @next/next/no-img-element
        <img src={src} alt={alt} width={size} height={size} loading="lazy" className="h-full w-full object-cover" onError={() => setErr(true)} />
      ) : (
        <ImageOff size={Math.max(12, size / 3)} className="text-dim" />
      )}
    </div>
  );
}
