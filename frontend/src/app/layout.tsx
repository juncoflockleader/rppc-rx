import type { Metadata } from "next";
import Link from "next/link";
import "./globals.css";

export const metadata: Metadata = {
  title: "Podcast Synthesis",
  description: "Turn material into a persona-grounded podcast.",
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en" className="h-full antialiased">
      <body className="min-h-full bg-neutral-50 text-neutral-900">
        <header className="border-b border-neutral-200 bg-white">
          <div className="mx-auto flex max-w-5xl items-center justify-between px-6 py-3">
            <Link href="/projects" className="font-semibold tracking-tight">
              Podcast&nbsp;Synthesis
            </Link>
            <nav className="flex gap-4 text-sm text-neutral-500">
              <Link href="/projects" className="hover:text-neutral-900">
                Projects
              </Link>
              <Link href="/personas" className="hover:text-neutral-900">
                Personas
              </Link>
            </nav>
          </div>
        </header>
        <main className="mx-auto max-w-5xl px-6 py-8">{children}</main>
      </body>
    </html>
  );
}
