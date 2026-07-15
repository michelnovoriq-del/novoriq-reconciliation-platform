# Custom-domain SEO migration

1. Set `NEXT_PUBLIC_SITE_URL` to the new HTTPS origin.
2. Rebuild and deploy.
3. Verify canonicals, sitemap, and robots use the new origin.
4. Configure permanent redirects from each old public URL to its new equivalent.
5. Add and verify the new Search Console property.
6. Submit the new sitemap and monitor redirects and canonical selection.

Do not configure redirects until the custom domain exists and is production-ready.
