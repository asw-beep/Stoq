import type { Metadata } from "next";
import { Figtree, Geist_Mono, Libre_Caslon_Display } from "next/font/google";
import "./globals.css";
import { Providers } from "./providers";

// Type pairing inspired by typespiration.com "Rethink Possible":
// Libre Caslon Display (serif) for headings, Figtree (sans) for body.
const figtree = Figtree({
  variable: "--font-sans",
  subsets: ["latin"],
});

const libreCaslon = Libre_Caslon_Display({
  variable: "--font-heading",
  weight: "400",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Stoq — Financial Intelligence",
  description: "Stock forecasting, news sentiment, and portfolio analytics.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en"
      className={`${figtree.variable} ${libreCaslon.variable} ${geistMono.variable} h-full antialiased`}
    >
      <body className="min-h-full flex flex-col">
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
