import type { Metadata } from "next";

import "./globals.css";

export const metadata: Metadata = {
  title: "IncidentZero — Autonomous incident resolution",
  description: "From production incident to verified fix — autonomously.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="en"><body>{children}</body></html>;
}
