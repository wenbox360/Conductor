// File: mcphardware/src/app/layout.tsx
import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import { Sora } from "next/font/google";
import "./globals.css";

const sora = Sora({ subsets: ["latin"], variable: "--font-sora" });
const geistSans = Geist({ variable: "--font-geist-sans", subsets: ["latin"] });
const geistMono = Geist_Mono({ variable: "--font-geist-mono", subsets: ["latin"] });

export const metadata: Metadata = {
  title: "MCP GPIO Control",
  description: "Let AI discover and use your tools.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className={`${sora.variable} ${geistSans.variable} ${geistMono.variable} antialiased`}>
        <div className="bg-gradient-mesh pointer-events-none" />
        <header className="site-header">
          <div className="container header-inner">
            <div className="brand">
              <div className="dot" />
              <span>MCP GPIO</span>
            </div>
            <nav>
              <a href="#discover">Discover</a>
              <a href="#control">Control</a>
              <a href="#events">Events</a>
              <a href="https://github.com" target="_blank" rel="noreferrer">GitHub</a>
            </nav>
          </div>
        </header>
        <main className="container px-5 py-10">{children}</main>
        <footer className="container py-10 opacity-70 text-sm">
          Built with FastMCP • Designed for clarity & speed
        </footer>
      </body>
    </html>
  );
}
