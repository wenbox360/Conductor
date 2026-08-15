import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Conductor",
  description: "Map embedded hardware into MCP tools and generated firmware.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="antialiased">
        <div className="bg-gradient-mesh pointer-events-none" />
        <header className="site-header">
          <div className="container header-inner">
            <div className="brand">
              <div className="dot" />
              <span>Conductor</span>
            </div>
            <nav>
              <a href="#setup">Setup</a>
              <a href="#discover">Tools</a>
              <a href="#events">Logs</a>
            </nav>
          </div>
        </header>
        <main className="container px-5 py-10">{children}</main>
        <footer className="container py-10 text-muted text-sm">
          Conductor • Configure, control, and deploy
        </footer>
      </body>
    </html>
  );
}
