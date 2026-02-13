"use client";
import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";
import MainTabBar from "@/components/app/MainTabBar";
import { ConfigProvider } from '@/hooks/ConfigContext';
import { FeaturesProvider } from '@/hooks/FeaturesContext';

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
      <body className="h-screen w-full min-h-screen flex flex-col overflow-hidden bg-neutral-950">
      <ConfigProvider>
      <FeaturesProvider>
        <MainTabBar />
        <main className="flex-1 min-h-0">{children}</main>
      </FeaturesProvider>
      </ConfigProvider>
      </body>
    </html>
  );
}
