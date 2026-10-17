import type { Metadata } from "next";

import "./globals.css";
import { RuntimeProvider } from "@/components/runtime";

export const metadata: Metadata = {
  title: "IncidentZero — Autonomous incident resolution",
  description: "From production incident to verified fix — autonomously.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="en"><body><RuntimeProvider>{children}</RuntimeProvider></body></html>;
}
