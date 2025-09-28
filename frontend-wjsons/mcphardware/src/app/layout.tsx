// File: mcphardware/src/app/layout.tsx
import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import { Sora } from "next/font/google";
import "./globals.css";

const sora = Sora({ subsets: ["latin"], variable: "--font-sora" });
const geistSans = Geist({ variable: "--font-geist-sans", subsets: ["latin"] });
const geistMono = Geist_Mono({ variable: "--font-geist-mono", subsets: ["latin"] });

export const metadata: Metadata = {
  title: "Hardware Hub",
  description: "Connect and control your hardware devices with AI assistance.",
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
              <span>Hardware Hub</span>
            </div>
            <nav>
              <a href="#setup">Setup</a>
              <a href="#discover">Tools</a>
              <a href="#control">Control</a>
              <a href="#events">Logs</a>
            </nav>
          </div>
        </header>
        <main className="container px-5 py-10">{children}</main>
        <footer className="container py-10 text-muted text-sm">
          Hardware Hub • Connect, control, automate
        </footer>
      </body>
    </html>
  );
}
