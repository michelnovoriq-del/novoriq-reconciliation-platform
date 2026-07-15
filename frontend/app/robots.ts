import type { MetadataRoute } from "next"; import { absoluteUrl,siteConfig } from "@/lib/site-config";
export default function robots():MetadataRoute.Robots{return {rules:{userAgent:"*",allow:"/",disallow:["/api/","/dashboard/","/files/","/reconciliation-runs/","/settings/","/billing/return"]},sitemap:absoluteUrl("/sitemap.xml"),host:siteConfig.url};}
