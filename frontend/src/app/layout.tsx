import type { Metadata, Viewport } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Multi-Agent Stress Testing of LLM Ethical Reasoning",
  description: "EECS 6895 Final Project — dataset browser and demo trace viewer.",
  other: {
    "color-scheme": "light only",
  },
};

export const viewport: Viewport = {
  colorScheme: "light",
  themeColor: "#f8fafc",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en"
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased bg-slate-50 text-slate-900`}
    >
      <body className="min-h-full flex flex-col bg-slate-50 text-slate-900">
        <header className="border-b border-slate-200 bg-white">
          <nav className="mx-auto max-w-6xl px-6 py-4 flex items-center gap-6 text-sm">
            <a href="/" className="font-semibold">Ethics Stress-Test</a>
            <a href="/dataset" className="text-slate-600 hover:text-slate-900">Dataset</a>
            <a href="/traces" className="text-slate-600 hover:text-slate-900">Demo traces</a>
            <a href="/scorecard" className="text-slate-600 hover:text-slate-900">Scorecard</a>
            <a href="/models" className="text-slate-600 hover:text-slate-900">Models</a>
            <span className="ml-auto text-xs text-slate-400">EECS 6895 Spring 2026</span>
          </nav>
        </header>
        <main className="flex-1">{children}</main>
        <footer className="border-t border-slate-200 bg-white">
          <div className="mx-auto max-w-6xl px-6 py-4 text-xs text-slate-500">
            Multi-Agent Stress Testing of LLM Ethical Reasoning · 180 scenarios across Moral Machine, Scruples, Hendrycks ETHICS
          </div>
        </footer>
      </body>
    </html>
  );
}
