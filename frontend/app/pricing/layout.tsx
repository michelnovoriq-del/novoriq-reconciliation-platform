import type { Metadata } from "next";
import { pageMetadata } from "@/lib/metadata";
export const metadata: Metadata = { ...pageMetadata("Novoriq Pricing | Free Forever Reconciliation Software", "Start with Novoriq Free Forever or compare Professional and Firm plans for higher reconciliation volume, more users, and longer history.", "/pricing"), title: { absolute: "Novoriq Pricing | Free Forever Reconciliation Software" } };
export default function PricingLayout({children}:{children:React.ReactNode}) { return children; }
