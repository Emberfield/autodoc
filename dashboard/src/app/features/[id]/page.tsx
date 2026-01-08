import { loadDashboardData } from "@/lib/data";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Sparkles, FileCode, Brain, ChevronLeft, Code2, Braces, Box } from "lucide-react";
import Link from "next/link";
import { notFound } from "next/navigation";

export const dynamic = "force-dynamic";

interface PageProps {
  params: Promise<{ id: string }>;
}

export default async function FeatureDetailPage({ params }: PageProps) {
  const { id } = await params;
  const data = loadDashboardData();

  const feature = data.features?.features?.[id];

  if (!feature) {
    notFound();
  }

  // Get entities for files in this feature
  const getFileEntities = (filePath: string) => {
    return data.analysis?.entities?.filter(e => e.file_path === filePath) || [];
  };

  // Get enrichment for an entity
  const getEnrichment = (entity: ReturnType<typeof getFileEntities>[0]) => {
    const enrichmentKeys = Object.keys(data.enrichment || {});
    const key = enrichmentKeys.find(k =>
      k.includes(entity.name) && k.includes(entity.file_path.split('/').pop() || '')
    );
    return key ? data.enrichment?.[key] : null;
  };

  const typeIcon = (type: string) => {
    switch (type) {
      case "function":
        return <Braces className="h-4 w-4" />;
      case "class":
        return <Box className="h-4 w-4" />;
      default:
        return <Code2 className="h-4 w-4" />;
    }
  };

  return (
    <div className="p-6 space-y-6 max-w-5xl">
      {/* Back link */}
      <Link
        href="/features"
        className="inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground"
      >
        <ChevronLeft className="h-4 w-4" />
        Back to Features
      </Link>

      {/* Header */}
      <div className="space-y-2">
        <h1 className="text-3xl font-bold flex items-center gap-3">
          <Sparkles className="h-8 w-8 text-primary" />
          {feature.display_name || feature.name || `Feature ${feature.id}`}
        </h1>
        {feature.reasoning && (
          <p className="text-lg text-muted-foreground max-w-2xl">
            {feature.reasoning}
          </p>
        )}
        <div className="flex gap-2 pt-2">
          <Badge variant="outline">{feature.file_count} files</Badge>
          <Badge variant="outline">Feature ID: {feature.id}</Badge>
        </div>
      </div>

      {/* Files with full entity details */}
      <div className="space-y-4">
        <h2 className="text-xl font-semibold">Files in this Feature</h2>

        {feature.files.map((filePath, i) => {
          const entities = getFileEntities(filePath);

          return (
            <Card key={i}>
              <CardHeader className="pb-2">
                <CardTitle className="text-base font-mono flex items-center gap-2">
                  <FileCode className="h-5 w-5 text-muted-foreground" />
                  {filePath}
                </CardTitle>
                <CardDescription>
                  {entities.length} entities
                </CardDescription>
              </CardHeader>
              <CardContent>
                {entities.length > 0 ? (
                  <div className="space-y-3">
                    {entities.map((entity, j) => {
                      const enrichment = getEnrichment(entity);
                      return (
                        <div
                          key={j}
                          className="p-3 rounded-lg bg-muted/50 space-y-2"
                        >
                          <div className="flex items-center gap-2">
                            {typeIcon(entity.type)}
                            <span className="font-mono font-medium">
                              {entity.parent_class ? `${entity.parent_class}.` : ''}
                              {entity.name}
                            </span>
                            <Badge variant="outline" className="text-xs">
                              {entity.type}
                            </Badge>
                            <span className="text-xs text-muted-foreground">
                              line {entity.line_number}
                            </span>
                            {enrichment && (
                              <Badge variant="secondary" className="text-xs gap-1">
                                <Brain className="h-3 w-3" />
                                documented
                              </Badge>
                            )}
                          </div>

                          {/* Description */}
                          <p className="text-sm text-muted-foreground">
                            {enrichment?.summary || entity.docstring?.split('\n')[0] || 'No description'}
                          </p>

                          {/* Full enrichment details if available */}
                          {enrichment && (
                            <div className="pt-2 space-y-2 border-t border-border/50">
                              {enrichment.description && enrichment.description !== enrichment.summary && (
                                <p className="text-sm text-muted-foreground">
                                  {enrichment.description}
                                </p>
                              )}

                              {enrichment.parameters && enrichment.parameters.length > 0 && (
                                <div className="text-sm">
                                  <span className="font-medium">Parameters: </span>
                                  {enrichment.parameters.map((p, k) => (
                                    <span key={k} className="text-muted-foreground">
                                      <code className="bg-background px-1 rounded">{p.name}</code>
                                      {p.description && ` - ${p.description}`}
                                      {k < enrichment.parameters!.length - 1 && '; '}
                                    </span>
                                  ))}
                                </div>
                              )}

                              {enrichment.returns && (
                                <div className="text-sm">
                                  <span className="font-medium">Returns: </span>
                                  <span className="text-muted-foreground">{enrichment.returns}</span>
                                </div>
                              )}
                            </div>
                          )}

                          {/* Signature if no enrichment */}
                          {!enrichment && entity.signature && (
                            <code className="text-xs bg-muted px-2 py-1 rounded block overflow-x-auto">
                              {entity.signature}
                            </code>
                          )}
                        </div>
                      );
                    })}
                  </div>
                ) : (
                  <p className="text-sm text-muted-foreground">
                    No entities found in this file
                  </p>
                )}
              </CardContent>
            </Card>
          );
        })}
      </div>
    </div>
  );
}
