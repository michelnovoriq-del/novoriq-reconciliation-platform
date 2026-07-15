const rawSiteUrl = process.env.NEXT_PUBLIC_SITE_URL?.trim();
const developmentFallback = "http://localhost:3000";

function normalizeSiteUrl(value: string | undefined) {
  if (!value) {
    if (process.env.NODE_ENV === "production") {
      throw new Error("NEXT_PUBLIC_SITE_URL is required in production.");
    }
    return developmentFallback;
  }

  let parsed: URL;
  try {
    parsed = new URL(value);
  } catch {
    throw new Error("NEXT_PUBLIC_SITE_URL must be an absolute URL.");
  }
  if (process.env.NODE_ENV === "production" && parsed.protocol !== "https:") {
    throw new Error("NEXT_PUBLIC_SITE_URL must use HTTPS in production.");
  }
  return parsed.toString().replace(/\/$/, "");
}

export const siteConfig = {
  name: "Novoriq",
  description: "CSV and Excel reconciliation software for accountants, bookkeepers, accounting firms, and finance teams.",
  url: normalizeSiteUrl(rawSiteUrl),
  supportEmail: "michelnovoriq@gmail.com",
  links: {
    pricing: "/pricing", features: "/features", howItWorks: "/how-it-works",
    bookkeepers: "/use-cases/bookkeepers", accountingFirms: "/use-cases/accounting-firms",
    ecommerceReconciliation: "/use-cases/ecommerce-reconciliation", security: "/security",
    dataRetention: "/data-retention", privacy: "/privacy", terms: "/terms", support: "/support",
  },
} as const;

export function absoluteUrl(path = "/") {
  return path === "/" ? siteConfig.url : `${siteConfig.url}${path.startsWith("/") ? path : `/${path}`}`;
}
