import type { Metadata } from "next";
import "./globals.css";
import { ToastProvider } from "@/components/ui/toast";
import { Shell } from "@/components/layout/shell";

export const metadata: Metadata = {
  title: "OUTLIER - Auction Intelligence",
  description: "AI-powered auction intelligence and sourcing for vintage clothing and jewelry resellers.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <ToastProvider>
          <Shell>{children}</Shell>
        </ToastProvider>
      </body>
    </html>
  );
}
