import { loadDashboardData } from "@/lib/data";
import { SearchPageClient } from "./search-client";

export const dynamic = "force-dynamic";

export default function SearchPage() {
  const data = loadDashboardData();

  return (
    <SearchPageClient
      entities={data.analysis?.entities || []}
      enrichment={data.enrichment}
      features={data.features?.features ? Object.values(data.features.features) : []}
      packs={data.config?.context_packs || []}
    />
  );
}
