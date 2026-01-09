import { loadDashboardData } from "@/lib/data";
import { EntitiesPageClient } from "./entities-client";

export const dynamic = "force-dynamic";

export default function EntitiesPage() {
  const data = loadDashboardData();

  return (
    <EntitiesPageClient
      entities={data.analysis?.entities || []}
      enrichment={data.enrichment}
    />
  );
}
