import { loadDashboardData } from "@/lib/data";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { BookOpen, Layers, Sparkles, Code2, ArrowRight, Brain } from "lucide-react";

export const dynamic = "force-dynamic";

export default function ArchitecturePage() {
  const data = loadDashboardData();

  const features = data.features?.features
    ? Object.values(data.features.features).sort((a, b) => b.file_count - a.file_count)
    : [];

  // Get enriched classes (architectural pillars)
  const enrichedClasses = data.analysis?.entities?.filter(e => {
    if (e.type !== "class") return false;
    const enrichmentKeys = Object.keys(data.enrichment || {});
    return enrichmentKeys.some(k =>
      k.includes(e.name) && k.includes(e.file_path.split("/").pop() || "")
    );
  }) || [];

  const getEnrichment = (entity: typeof enrichedClasses[0]) => {
    const enrichmentKeys = Object.keys(data.enrichment || {});
    const key = enrichmentKeys.find(k =>
      k.includes(entity.name) && k.includes(entity.file_path.split("/").pop() || "")
    );
    return key ? data.enrichment?.[key] : null;
  };

  // Group files by directory for structure overview
  const directoryStats = new Map<string, number>();
  data.analysis?.entities?.forEach(e => {
    const dir = e.file_path.split('/').slice(0, -1).join('/') || '.';
    directoryStats.set(dir, (directoryStats.get(dir) || 0) + 1);
  });

  const topDirectories = Array.from(directoryStats.entries())
    .sort((a, b) => b[1] - a[1])
    .slice(0, 8);

  const projectName = data.projectRoot.split('/').pop() || 'Project';

  return (
    <div className="p-6 space-y-8 max-w-4xl">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold flex items-center gap-3">
          <BookOpen className="h-8 w-8 text-primary" />
          How It Works
        </h1>
        <p className="text-muted-foreground mt-2">
          Understanding the architecture and design of <code className="bg-muted px-2 py-0.5 rounded">{projectName}</code>
        </p>
      </div>

      {/* Executive Summary */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Overview</CardTitle>
        </CardHeader>
        <CardContent className="prose prose-sm dark:prose-invert max-w-none">
          <p className="text-muted-foreground leading-relaxed">
            This codebase contains <strong>{data.stats.totalEntities}</strong> code entities
            (functions, classes, and methods) across <strong>{data.stats.totalFiles}</strong> files.
            {features.length > 0 && (
              <> Analysis has identified <strong>{features.length} distinct features</strong> - cohesive
              groups of code that work together to provide specific functionality.</>
            )}
            {data.stats.enrichedCount > 0 && (
              <> <strong>{data.stats.enrichedCount}</strong> entities have been documented with
              AI-generated descriptions.</>
            )}
          </p>
        </CardContent>
      </Card>

      {/* Main Features Section */}
      {features.length > 0 && (
        <section className="space-y-4">
          <h2 className="text-xl font-semibold flex items-center gap-2">
            <Sparkles className="h-5 w-5 text-primary" />
            Main Capabilities
          </h2>

          <div className="space-y-4">
            {features.map((feature, index) => (
              <Card key={feature.id}>
                <CardContent className="pt-4">
                  <div className="flex items-start gap-4">
                    <div className="flex items-center justify-center w-8 h-8 rounded-full bg-primary/10 text-primary font-semibold text-sm flex-shrink-0">
                      {index + 1}
                    </div>
                    <div className="flex-1">
                      <h3 className="font-semibold text-lg">
                        {feature.display_name || feature.name || `Feature ${feature.id}`}
                      </h3>
                      {feature.reasoning ? (
                        <p className="text-muted-foreground mt-1 leading-relaxed">
                          {feature.reasoning}
                        </p>
                      ) : (
                        <p className="text-muted-foreground mt-1 italic">
                          No description available yet
                        </p>
                      )}
                      <div className="flex items-center gap-2 mt-3 text-sm text-muted-foreground">
                        <Code2 className="h-4 w-4" />
                        <span>Implemented across {feature.file_count} files</span>
                      </div>
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </section>
      )}

      {/* Key Abstractions */}
      {enrichedClasses.length > 0 && (
        <section className="space-y-4">
          <h2 className="text-xl font-semibold flex items-center gap-2">
            <Layers className="h-5 w-5 text-primary" />
            Key Abstractions
          </h2>
          <p className="text-sm text-muted-foreground">
            These classes form the architectural foundation of the codebase:
          </p>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {enrichedClasses.slice(0, 8).map((cls, i) => {
              const enrichment = getEnrichment(cls);
              return (
                <Card key={`${cls.file_path}:${cls.name}:${i}`}>
                  <CardContent className="pt-4">
                    <div className="flex items-center gap-2 mb-2">
                      <Badge variant="outline" className="text-xs">class</Badge>
                      <span className="font-mono font-medium">{cls.name}</span>
                    </div>
                    <p className="text-sm text-muted-foreground">
                      {enrichment?.summary || cls.docstring?.split('\n')[0] || 'No description'}
                    </p>
                    <p className="text-xs text-muted-foreground mt-2 font-mono">
                      {cls.file_path}
                    </p>
                  </CardContent>
                </Card>
              );
            })}
          </div>
        </section>
      )}

      {/* Directory Structure */}
      {topDirectories.length > 0 && (
        <section className="space-y-4">
          <h2 className="text-xl font-semibold flex items-center gap-2">
            <Code2 className="h-5 w-5 text-primary" />
            Code Organization
          </h2>
          <p className="text-sm text-muted-foreground">
            Where the code lives:
          </p>

          <Card>
            <CardContent className="pt-4">
              <div className="space-y-3">
                {topDirectories.map(([dir, count]) => (
                  <div key={dir} className="flex items-center gap-3">
                    <div className="flex-1">
                      <span className="font-mono text-sm">{dir || '.'}/</span>
                    </div>
                    <Badge variant="outline">{count} entities</Badge>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </section>
      )}

      {/* Next Steps */}
      {(!features.length || !data.stats.enrichedCount) && (
        <Card className="border-dashed">
          <CardContent className="py-6">
            <h3 className="font-semibold mb-3 flex items-center gap-2">
              <Brain className="h-5 w-5" />
              Improve This Documentation
            </h3>
            <div className="space-y-3 text-sm">
              {!features.length && (
                <div className="flex items-start gap-2">
                  <ArrowRight className="h-4 w-4 mt-0.5 text-muted-foreground" />
                  <div>
                    <p className="font-medium">Detect features</p>
                    <code className="text-xs bg-muted px-2 py-1 rounded block mt-1">
                      autodoc graph --clear && autodoc features detect && autodoc features name
                    </code>
                  </div>
                </div>
              )}
              {!data.stats.enrichedCount && (
                <div className="flex items-start gap-2">
                  <ArrowRight className="h-4 w-4 mt-0.5 text-muted-foreground" />
                  <div>
                    <p className="font-medium">Generate AI documentation</p>
                    <code className="text-xs bg-muted px-2 py-1 rounded block mt-1">
                      autodoc enrich --inline --limit 50
                    </code>
                  </div>
                </div>
              )}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
