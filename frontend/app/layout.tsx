import type { Metadata } from "next";
import type { ReactNode } from "react";

import "./globals.css";

export const metadata: Metadata = {
  title: "OCPP-Demo",
  description: "Operations dashboard for OCPP lifecycle demo",
  icons: {
    icon: "/assets/brand/elephant-logo.ico",
    shortcut: "/assets/brand/elephant-logo.ico",
    apple: "/assets/brand/elephant-logo.png",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: ReactNode;
}>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
