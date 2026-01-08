import { loadDashboardData } from "@/lib/data";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Sparkles, ArrowRight, Brain, Code2, Layers } from "lucide-react";
import Link from "next/link";

export const dynamic = "force-dynamic";

export default function OverviewPage() {
  const data = loadDashboardData();

  const features = data.features?.features
    ? Object.values(data.features.features).sort((a, b) => b.file_count - a.file_count)
    : [];

  // Get top enriched entities to showcase
  const enrichedEntities = data.analysis?.entities?.filter(entity => {
    const enrichmentKeys = Object.keys(data.enrichment || {});
    return enrichmentKeys.some(k =>
      k.includes(entity.name) && k.includes(entity.file_path.split("/").pop() || "")
    );
  }).slice(0, 6) || [];

  const getEnrichment = (entity: typeof enrichedEntities[0]) => {
    const enrichmentKeys = Object.keys(data.enrichment || {});
    const key = enrichmentKeys.find(k =>
      k.includes(entity.name) && k.includes(entity.file_path.split("/").pop() || "")
    );
    return key ? data.enrichment?.[key] : null;
  };

  // Identify key classes (likely architectural pillars)
  const keyClasses = data.analysis?.entities?.filter(e => e.type === "class").slice(0, 8) || [];

  return (
    <div className="p-6 space-y-8">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold">Codebase Overview</h1>
        <p className="text-muted-foreground mt-1">
          <code className="text-sm bg-muted px-2 py-0.5 rounded">{data.projectRoot.split('/').pop()}</code>
        </p>
      </div>

      {/* Quick Stats - Minimal */}
      <div className="flex gap-3 flex-wrap">
        <Badge variant="outline" className="px-3 py-1">
          {data.stats.totalFiles} files
        </Badge>
        <Badge variant="outline" className="px-3 py-1">
          {data.stats.totalEntities} entities
        </Badge>
        {data.stats.enrichedCount > 0 && (
          <Badge variant="secondary" className="px-3 py-1">
            <Brain className="h-3 w-3 mr-1" />
            {data.stats.enrichedCount} documented
          </Badge>
        )}
        {features.length > 0 && (
          <Badge variant="secondary" className="px-3 py-1">
            <Sparkles className="h-3 w-3 mr-1" />
            {features.length} features detected
          </Badge>
        )}
      </div>

      {/* Main Content: What This Codebase Does */}
      {features.length > 0 ? (
        <section className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-xl font-semibold flex items-center gap-2">
                <Sparkles className="h-5 w-5 text-primary" />
                What This Codebase Does
              </h2>
              <p className="text-sm text-muted-foreground">
                Auto-detected features based on code relationships
              </p>
            </div>
            <Link
              href="/features"
              className="text-sm text-primary hover:underline flex items-center gap-1"
            >
              View all features <ArrowRight className="h-4 w-4" />
            </Link>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {features.slice(0, 6).map((feature) => (
              <Link key={feature.id} href={`/features/${feature.id}`}>
                <Card className="hover:border-primary/50 transition-colors cursor-pointer h-full">
                  <CardHeader className="pb-2">
                    <CardTitle className="text-lg flex items-center justify-between">
                      <span>{feature.display_name || feature.name || `Feature ${feature.id}`}</span>
                      <Badge variant="outline" className="text-xs">
                        {feature.file_count} files
                      </Badge>
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    {feature.reasoning ? (
                      <p className="text-sm text-muted-foreground leading-relaxed">
                        {feature.reasoning}
                      </p>
                    ) : (
                      <p className="text-sm text-muted-foreground italic">
                        Run <code className="text-xs bg-muted px-1 rounded">autodoc features name</code> for AI description
                      </p>
                    )}
                  </CardContent>
                </Card>
              </Link>
            ))}
          </div>
        </section>
      ) : (
        <Card className="border-dashed">
          <CardContent className="py-8 text-center">
            <Sparkles className="h-10 w-10 mx-auto text-muted-foreground mb-3" />
            <h3 className="font-semibold mb-2">Discover What This Codebase Does</h3>
            <p className="text-sm text-muted-foreground mb-4 max-w-md mx-auto">
              Run feature detection to automatically identify the main capabilities and modules in your code.
            </p>
            <div className="space-y-1 text-sm font-mono bg-muted p-3 rounded inline-block text-left">
              <div>autodoc graph --clear</div>
              <div>autodoc features detect</div>
              <div>autodoc features name</div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Key Components - Only show if we have enriched data */}
      {enrichedEntities.length > 0 && (
        <section className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-xl font-semibold flex items-center gap-2">
                <Brain className="h-5 w-5 text-primary" />
                Key Components
              </h2>
              <p className="text-sm text-muted-foreground">
                AI-documented functions and classes
              </p>
            </div>
            <Link
              href="/entities"
              className="text-sm text-primary hover:underline flex items-center gap-1"
            >
              Browse all <ArrowRight className="h-4 w-4" />
            </Link>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {enrichedEntities.map((entity, i) => {
              const enrichment = getEnrichment(entity);
              return (
                <Card key={`${entity.file_path}:${entity.name}:${i}`}>
                  <CardHeader className="pb-2">
                    <div className="flex items-center gap-2">
                      <Code2 className="h-4 w-4 text-muted-foreground" />
                      <CardTitle className="text-base font-mono">
                        {entity.parent_class ? `${entity.parent_class}.` : ''}{entity.name}
                      </CardTitle>
                      <Badge variant="outline" className="text-xs">
                        {entity.type}
                      </Badge>
                    </div>
                    <CardDescription className="text-xs font-mono">
                      {entity.file_path}:{entity.line_number}
                    </CardDescription>
                  </CardHeader>
                  <CardContent>
                    <p className="text-sm text-muted-foreground">
                      {enrichment?.summary || entity.docstring?.split('\n')[0] || 'No description available'}
                    </p>
                  </CardContent>
                </Card>
              );
            })}
          </div>
        </section>
      )}

      {/* Architecture Overview - Key Classes */}
      {keyClasses.length > 0 && (
        <section className="space-y-4">
          <div>
            <h2 className="text-xl font-semibold flex items-center gap-2">
              <Layers className="h-5 w-5 text-primary" />
              Core Abstractions
            </h2>
            <p className="text-sm text-muted-foreground">
              Main classes that define the architecture
            </p>
          </div>

          <Card>
            <CardContent className="pt-4">
              <div className="flex flex-wrap gap-2">
                {keyClasses.map((cls, i) => (
                  <div
                    key={`${cls.file_path}:${cls.name}:${i}`}
                    className="px-3 py-2 bg-muted rounded-lg"
                  >
                    <span className="font-mono text-sm font-medium">{cls.name}</span>
                    <span className="text-xs text-muted-foreground ml-2">
                      {cls.file_path.split('/').pop()}
                    </span>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </section>
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
