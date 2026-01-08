import { loadDashboardData } from "@/lib/data";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Sparkles, FileCode, Brain, ChevronRight, AlertCircle } from "lucide-react";

export const dynamic = "force-dynamic";

export default function FeaturesPage() {
  const data = loadDashboardData();
  const features = data.features?.features
    ? Object.values(data.features.features).sort((a, b) => b.file_count - a.file_count)
    : [];

  // Get enrichment for files
  const getFileEnrichment = (filePath: string) => {
    const enrichmentKeys = Object.keys(data.enrichment || {});
    const relevantKeys = enrichmentKeys.filter(k => k.includes(filePath.split('/').pop() || ''));
    if (relevantKeys.length === 0) return null;

    // Return first enrichment found for this file
    return data.enrichment?.[relevantKeys[0]];
  };

  // Get entities for a file
  const getFileEntities = (filePath: string) => {
    return data.analysis?.entities?.filter(e => e.file_path === filePath) || [];
  };

  return (
    <div className="p-6 space-y-8">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold flex items-center gap-3">
          <Sparkles className="h-8 w-8 text-primary" />
          Detected Features
        </h1>
        <p className="text-muted-foreground mt-2 max-w-2xl">
          These features were automatically discovered by analyzing code relationships using graph algorithms.
          Each feature represents a cohesive group of files that work together.
        </p>
      </div>

      {/* Stats */}
      {data.features && (
        <div className="flex gap-3 flex-wrap">
          <Badge variant="outline" className="px-3 py-1">
            {features.length} features
          </Badge>
          <Badge variant="outline" className="px-3 py-1">
            Modularity: {(data.features.modularity * 100).toFixed(0)}%
          </Badge>
          {features.filter(f => f.name).length > 0 && (
            <Badge variant="secondary" className="px-3 py-1">
              <Brain className="h-3 w-3 mr-1" />
              {features.filter(f => f.name).length} named
            </Badge>
          )}
        </div>
      )}

      {features.length > 0 ? (
        <div className="space-y-6">
          {features.map((feature) => (
            <Card key={feature.id} className="overflow-hidden">
              <CardHeader className="bg-muted/30">
                <div className="flex items-start justify-between">
                  <div className="space-y-1">
                    <CardTitle className="text-xl flex items-center gap-2">
                      <Sparkles className="h-5 w-5 text-primary" />
                      {feature.display_name || feature.name || `Feature ${feature.id}`}
                    </CardTitle>
                    {feature.reasoning && (
                      <CardDescription className="text-base">
                        {feature.reasoning}
                      </CardDescription>
                    )}
                  </div>
                  <Badge variant="outline" className="text-sm">
                    {feature.file_count} files
                  </Badge>
                </div>
              </CardHeader>

              <CardContent className="pt-4 space-y-4">
                {/* Files in this feature */}
                <div className="space-y-2">
                  <h4 className="text-sm font-medium text-muted-foreground flex items-center gap-2">
                    <FileCode className="h-4 w-4" />
                    Files in this feature
                  </h4>

                  <div className="grid grid-cols-1 lg:grid-cols-2 gap-2">
                    {feature.files.slice(0, 10).map((filePath, i) => {
                      const entities = getFileEntities(filePath);
                      const enrichment = getFileEnrichment(filePath);
                      const fileName = filePath.split('/').pop();

                      return (
                        <div
                          key={i}
                          className="p-3 rounded-lg bg-muted/50 hover:bg-muted transition-colors"
                        >
                          <div className="flex items-center gap-2">
                            <ChevronRight className="h-4 w-4 text-muted-foreground flex-shrink-0" />
                            <span className="font-mono text-sm truncate flex-1">
                              {filePath}
                            </span>
                            {entities.length > 0 && (
                              <Badge variant="outline" className="text-xs flex-shrink-0">
                                {entities.length} entities
                              </Badge>
                            )}
                          </div>

                          {/* Show what this file contains */}
                          {entities.length > 0 && (
                            <div className="mt-2 pl-6 space-y-1">
                              {entities.slice(0, 3).map((entity, j) => {
                                const entityEnrichment = data.enrichment?.[
                                  Object.keys(data.enrichment || {}).find(k =>
                                    k.includes(entity.name) && k.includes(fileName || '')
                                  ) || ''
                                ];

                                return (
                                  <div key={j} className="text-sm">
                                    <span className="text-muted-foreground">
                                      {entity.type === 'class' ? 'class ' : entity.type === 'function' ? 'fn ' : ''}
                                    </span>
                                    <span className="font-mono font-medium">
                                      {entity.name}
                                    </span>
                                    {entityEnrichment?.summary && (
                                      <span className="text-muted-foreground ml-2">
                                        - {entityEnrichment.summary.slice(0, 60)}
                                        {entityEnrichment.summary.length > 60 ? '...' : ''}
                                      </span>
                                    )}
                                  </div>
                                );
                              })}
                              {entities.length > 3 && (
                                <span className="text-xs text-muted-foreground">
                                  +{entities.length - 3} more
                                </span>
                              )}
                            </div>
                          )}
                        </div>
                      );
                    })}
                  </div>

                  {feature.files.length > 10 && (
                    <p className="text-sm text-muted-foreground pl-6">
                      +{feature.files.length - 10} more files
                    </p>
                  )}
                </div>

                {/* Prompt to name if unnamed */}
                {!feature.name && (
                  <div className="flex items-center gap-2 p-3 bg-amber-500/10 rounded-lg text-amber-600 dark:text-amber-400">
                    <AlertCircle className="h-4 w-4 flex-shrink-0" />
                    <span className="text-sm">
                      Run <code className="bg-muted px-1 rounded">autodoc features name --feature-id {feature.id}</code> to generate a semantic name
                    </span>
                  </div>
                )}
              </CardContent>
            </Card>
          ))}
        </div>
      ) : (
        <Card className="border-dashed">
          <CardContent className="py-12 text-center">
            <Sparkles className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
            <h2 className="text-xl font-semibold mb-2">No Features Detected Yet</h2>
            <p className="text-muted-foreground mb-6 max-w-md mx-auto">
              Feature detection uses graph analysis to find groups of related code.
              This requires Neo4j with the Graph Data Science plugin.
            </p>
            <div className="space-y-2 text-sm font-mono bg-muted p-4 rounded-lg inline-block text-left">
              <div className="text-muted-foreground"># Build the code graph</div>
              <div>autodoc graph --clear</div>
              <div className="text-muted-foreground mt-2"># Detect features using Louvain algorithm</div>
              <div>autodoc features detect</div>
              <div className="text-muted-foreground mt-2"># Generate semantic names with AI</div>
              <div>autodoc features name</div>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
