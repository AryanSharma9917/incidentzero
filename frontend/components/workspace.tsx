"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import type { ReactNode } from "react";
import { RuntimeBanner } from "./runtime";

export function Workspace({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  return <main className="workspace">
    <aside className="sidebar">
      <Link href="/" className="brand">INCIDENT<span>ZERO</span></Link>
      <p className="eyebrow">Operations workspace</p>
      <nav aria-label="Workspace navigation">{[["/dashboard", "Dashboard"], ["/incidents", "Incidents"], ["/runs", "Agent Runs"]].map(([href, label]) =>
        <Link key={href} href={href} aria-current={pathname.startsWith(href) ? "page" : undefined}>{label}</Link>)}</nav>
      <div className="safety-note"><span className="dot" /> Controlled demo sandbox<p>Production remains read-only. All runs use real backend execution.</p></div>
    </aside>
    <div className="workspace-content"><RuntimeBanner />{children}</div>
  </main>;
}
export function Status({ value }: { value: string }) {
  return <span className={`status status-${value}`}>{value === "simulated" ? "Simulation passed" : value.replaceAll("_", " ")}</span>;
}
export function Alert({ message }: { message: string }) {
  return <p role="alert" className="error-box">{message}</p>;
}
export function Empty({ children }: { children: ReactNode }) {
  return <p className="empty">{children}</p>;
}
