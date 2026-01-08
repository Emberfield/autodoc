import { loadDashboardData } from "@/lib/data";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Code2, FileCode, Package, Sparkles, Brain } from "lucide-react";

export const dynamic = "force-dynamic";

export default function OverviewPage() {
  const data = loadDashboardData();

  const statCards = [
    {
      title: "Total Entities",
      value: data.stats.totalEntities,
      icon: Code2,
      description: "Functions, classes, and methods",
    },
    {
      title: "Files Analyzed",
      value: data.stats.totalFiles,
      icon: FileCode,
      description: "Source files in codebase",
    },
    {
      title: "Enriched",
      value: data.stats.enrichedCount,
      icon: Brain,
      description: "AI-documented entities",
    },
    {
      title: "Context Packs",
      value: data.stats.packCount,
      icon: Package,
      description: "Logical code groupings",
    },
    {
      title: "Features",
      value: data.stats.featureCount,
      icon: Sparkles,
      description: "Auto-detected clusters",
    },
  ];

  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Dashboard Overview</h1>
        <p className="text-muted-foreground mt-1">
          Exploring: <code className="text-sm bg-muted px-2 py-0.5 rounded">{data.projectRoot}</code>
        </p>
      </div>

      {/* Status */}
      <div className="flex gap-2">
        {data.analysis ? (
          <Badge variant="default">Analysis loaded</Badge>
        ) : (
          <Badge variant="destructive">No analysis found</Badge>
        )}
        {data.enrichment && <Badge variant="secondary">Enrichment available</Badge>}
        {data.config && <Badge variant="secondary">Config loaded</Badge>}
        {data.features && <Badge variant="secondary">Features detected</Badge>}
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4">
        {statCards.map((stat) => {
          const Icon = stat.icon;
          return (
            <Card key={stat.title}>
              <CardHeader className="flex flex-row items-center justify-between pb-2">
                <CardTitle className="text-sm font-medium text-muted-foreground">
                  {stat.title}
                </CardTitle>
                <Icon className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{stat.value}</div>
                <p className="text-xs text-muted-foreground mt-1">
                  {stat.description}
                </p>
              </CardContent>
            </Card>
          );
        })}
      </div>

      {/* Context Packs */}
      {data.config?.context_packs && data.config.context_packs.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Context Packs</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
              {data.config.context_packs.map((pack) => (
                <div
                  key={pack.name}
                  className="p-3 border rounded-lg hover:bg-accent transition-colors"
                >
                  <div className="flex items-center justify-between">
                    <span className="font-medium">{pack.display_name || pack.name}</span>
                    <Badge variant="outline">{pack.files?.length || 0} files</Badge>
                  </div>
                  {pack.description && (
                    <p className="text-sm text-muted-foreground mt-1 line-clamp-2">
                      {pack.description}
                    </p>
                  )}
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Features */}
      {data.features && Object.keys(data.features.features).length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Sparkles className="h-5 w-5" />
              Detected Features
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
              {Object.values(data.features.features).map((feature) => (
                <div
                  key={feature.id}
                  className="p-3 border rounded-lg hover:bg-accent transition-colors"
                >
                  <div className="flex items-center justify-between">
                    <span className="font-medium">
                      {feature.display_name || feature.name || `Feature ${feature.id}`}
                    </span>
                    <Badge variant="outline">{feature.file_count} files</Badge>
                  </div>
                  {feature.reasoning && (
                    <p className="text-sm text-muted-foreground mt-1 line-clamp-2">
                      {feature.reasoning}
                    </p>
                  )}
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* No Data State */}
      {!data.analysis && (
        <Card>
          <CardContent className="py-10 text-center">
            <Code2 className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
            <h2 className="text-xl font-semibold mb-2">No Analysis Found</h2>
            <p className="text-muted-foreground mb-4">
              Run autodoc to analyze your codebase first.
            </p>
            <code className="bg-muted px-4 py-2 rounded text-sm">
              autodoc analyze . --save
            </code>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
