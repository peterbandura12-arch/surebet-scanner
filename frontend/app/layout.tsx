import type { Metadata } from "next";
import "./globals.css";
import { LiveProvider } from "@/components/providers/live";
import { AppShell } from "@/components/app-shell";

export const metadata: Metadata = {
  title: "Surebet Scanner — Demo",
  description:
    "Sports odds arbitrage scanning platform (DEMO). All data is simulated; no real-money betting is possible.",
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-ink text-bright antialiased">
        <LiveProvider>
          <AppShell>{children}</AppShell>
        </LiveProvider>
      </body>
    </html>
  );
}
