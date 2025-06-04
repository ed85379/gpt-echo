"use client";
import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";
import MainTabBar from "./components/MainTabBar";
import { ConfigProvider } from './hooks/ConfigContext';

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});


export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body className="h-screen w-full min-h-screen flex flex-col bg-neutral-950">
      <ConfigProvider>
        <MainTabBar />
        <main>{children}</main>
      </ConfigProvider>
      </body>
    </html>
  );
}
