const base=(process.env.SEO_BASE_URL||"http://localhost:3000").replace(/\/$/,"");
const canonicalBase=(process.env.NEXT_PUBLIC_SITE_URL||"https://agenticreconcilliation.netlify.app").replace(/\/$/,"");
const routes=["/","/pricing","/features","/how-it-works","/use-cases/bookkeepers","/use-cases/accounting-firms","/use-cases/ecommerce-reconciliation","/security","/data-retention","/privacy","/terms","/support"];
let failed=false;
for(const path of routes){
  const expected=path==="/"?canonicalBase:canonicalBase+path;
  const response=await fetch(base+path); const html=await response.text();
  const checks={status:response.status===200,title:/<title>[^<]+<\/title>/i.test(html),description:/name=["']description["']/i.test(html),canonical:html.includes(`rel=\"canonical\" href=\"${expected}\"`)||html.includes(`href=\"${expected}\" rel=\"canonical\"`),h1:/<h1[\s>]/i.test(html),indexable:!/<meta[^>]+name=["']robots["'][^>]+noindex/i.test(html),noLocalhost:!html.includes("localhost")};
  for(const [name,ok] of Object.entries(checks))if(!ok){failed=true;console.error(`${path}: ${name} failed`);}
}
const sitemap=await(await fetch(base+"/sitemap.xml")).text();
for(const path of routes){const expected=path==="/"?canonicalBase:canonicalBase+path;if(!sitemap.includes(expected)){failed=true;console.error(`Sitemap missing ${path}`)}}
for(const path of ["/dashboard","/files","/login"])if(sitemap.includes(canonicalBase+path)){failed=true;console.error(`Sitemap exposes ${path}`)}
const robots=await(await fetch(base+"/robots.txt")).text();if(!robots.includes(canonicalBase+"/sitemap.xml")||!robots.includes("/dashboard/")){failed=true;console.error("robots.txt checks failed")}
if(failed)process.exit(1);console.log(`Verified ${routes.length} public routes, sitemap, and robots at ${base}`);
