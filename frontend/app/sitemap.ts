import type { MetadataRoute } from "next";

const SITE = "https://futurus.dev";

/**
 * Public routes only (no auth-gated dashboard/simulation URLs).
 * Submit in GSC as: sitemap.xml  (with property https://futurus.dev/)
 */
export default function sitemap(): MetadataRoute.Sitemap {
  const now = new Date();

  return [
    { url: SITE, lastModified: now, changeFrequency: "weekly", priority: 1 },
    { url: `${SITE}/contact`, lastModified: now, changeFrequency: "monthly", priority: 0.8 },
    { url: `${SITE}/privacy`, lastModified: now, changeFrequency: "yearly", priority: 0.4 },
    { url: `${SITE}/terms`, lastModified: now, changeFrequency: "yearly", priority: 0.4 },
    { url: `${SITE}/sign-in`, lastModified: now, changeFrequency: "monthly", priority: 0.5 },
    { url: `${SITE}/sign-up`, lastModified: now, changeFrequency: "monthly", priority: 0.5 },
  ];
}
