import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "CasAfrique",
  description: "TBD — placeholder metadata pending project scope confirmation.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
