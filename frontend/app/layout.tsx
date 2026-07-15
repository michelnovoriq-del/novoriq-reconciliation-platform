import type { Metadata } from "next";
import "./globals.css";
import { Providers } from "@/components/layout/providers";
import { siteConfig } from "@/lib/site-config";
import { JsonLd } from "@/components/seo/json-ld";

export const metadata: Metadata = {
  metadataBase: new URL(siteConfig.url),
  title: { default: "Novoriq | CSV and Excel Reconciliation Software", template: "%s | Novoriq" },
  description: "Novoriq helps accountants, bookkeepers, accounting firms, and finance teams map financial files, review likely matches, investigate exceptions, and export reviewed reconciliation results.",
  applicationName: "Novoriq", creator: "Novoriq", publisher: "Novoriq", category: "Business Software",
  keywords: ["financial reconciliation", "CSV reconciliation", "Excel reconciliation", "exception review"],
  alternates: { canonical: "/" },
  openGraph: { type: "website", siteName: "Novoriq", locale: "en_US", url: siteConfig.url, title: "Novoriq | CSV and Excel Reconciliation Software", description: siteConfig.description },
  twitter: { card: "summary_large_image", title: "Novoriq | CSV and Excel Reconciliation Software", description: siteConfig.description },
  robots: { index: true, follow: true },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="font-sans antialiased">
        <JsonLd data={{ "@context": "https://schema.org", "@type": "Organization", name: "Novoriq", url: siteConfig.url, email: siteConfig.supportEmail }} />
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
