import type { Metadata } from "next";
import "./globals.css";
import {Pwa} from "@/components/pwa";
export const metadata: Metadata = { title: "Siesco · Portal escolar", description: "Gestão escolar, pessoas e aprendizagem em um só lugar.",icons:{icon:"/icon-192.png",apple:"/icon-192.png"} };
export default function RootLayout({ children }: { children: React.ReactNode }) {
  return <html lang="pt-BR"><body><Pwa/>{children}</body></html>;
}

// Per-request script nonces require dynamic rendering.
export const dynamic = "force-dynamic";
