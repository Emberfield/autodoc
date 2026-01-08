import { loadDashboardData } from "@/lib/data";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Sparkles, FileCode, Brain, ChevronLeft, Code2, Braces, Box, ArrowRight, Link2 } from "lucide-react";
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

  // Get all entities in this feature
  const allFeatureEntities = feature.files.flatMap(getFileEntities);

  // Get enrichment for an entity
  const getEnrichment = (entity: ReturnType<typeof getFileEntities>[0]) => {
    const enrichmentKeys = Object.keys(data.enrichment || {});
    const key = enrichmentKeys.find(k =>
      k.includes(entity.name) && k.includes(entity.file_path.split('/').pop() || '')
    );
    return key ? data.enrichment?.[key] : null;
  };

  // Find potential connections between entities (classes and their methods, functions that might call each other)
  const entityConnections: Array<{from: string; to: string; type: string}> = [];

  // Find class -> method relationships
  const classes = allFeatureEntities.filter(e => e.type === 'class');
  const methods = allFeatureEntities.filter(e => e.type === 'method' || e.type === 'function');

  classes.forEach(cls => {
    const clsMethods = methods.filter(m =>
      m.parent_class === cls.name ||
      (m.file_path === cls.file_path && m.line_number > cls.line_number && (!cls.end_line || m.line_number < cls.end_line))
    );
    clsMethods.forEach(method => {
      entityConnections.push({
        from: cls.name,
        to: method.name,
        type: 'contains'
      });
    });
  });

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

  // Group entities by type for summary
  const classCount = allFeatureEntities.filter(e => e.type === 'class').length;
  const funcCount = allFeatureEntities.filter(e => e.type === 'function').length;
  const methodCount = allFeatureEntities.filter(e => e.type === 'method').length;
  const enrichedCount = allFeatureEntities.filter(e => getEnrichment(e)).length;

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
      </div>

      {/* Stats */}
      <div className="flex gap-2 flex-wrap">
        <Badge variant="outline">{feature.file_count} files</Badge>
        {classCount > 0 && <Badge variant="outline">{classCount} classes</Badge>}
        {funcCount > 0 && <Badge variant="outline">{funcCount} functions</Badge>}
        {methodCount > 0 && <Badge variant="outline">{methodCount} methods</Badge>}
        {enrichedCount > 0 && (
          <Badge variant="secondary">
            <Brain className="h-3 w-3 mr-1" />
            {enrichedCount} documented
          </Badge>
        )}
      </div>

      {/* Entity Connections visualization */}
      {entityConnections.length > 0 && (
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-base flex items-center gap-2">
              <Link2 className="h-5 w-5" />
              Entity Relationships
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {entityConnections.slice(0, 10).map((conn, i) => (
                <div key={i} className="flex items-center gap-2 text-sm">
                  <Badge variant="outline" className="font-mono">{conn.from}</Badge>
                  <ArrowRight className="h-4 w-4 text-muted-foreground" />
                  <Badge variant="secondary" className="font-mono">{conn.to}</Badge>
                  <span className="text-xs text-muted-foreground">({conn.type})</span>
                </div>
              ))}
              {entityConnections.length > 10 && (
                <p className="text-xs text-muted-foreground">
                  +{entityConnections.length - 10} more relationships
                </p>
              )}
            </div>
          </CardContent>
        </Card>
      )}

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
                  <div className="space-y-4">
                    {entities.map((entity, j) => {
                      const enrichment = getEnrichment(entity);
                      return (
                        <div
                          key={j}
                          className="p-4 rounded-lg bg-muted/50 space-y-3"
                        >
                          {/* Entity header */}
                          <div className="flex items-center gap-2 flex-wrap">
                            {typeIcon(entity.type)}
                            <span className="font-mono font-medium text-lg">
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

                          {/* Signature/Code */}
                          {entity.code && (
                            <code className="text-sm bg-background px-3 py-2 rounded block overflow-x-auto font-mono border">
                              {entity.code}
                            </code>
                          )}

                          {/* Description */}
                          <p className="text-sm text-muted-foreground">
                            {enrichment?.summary || entity.docstring?.split('\n')[0] || 'No description'}
                          </p>

                          {/* Key Features */}
                          {enrichment?.key_features && enrichment.key_features.length > 0 && (
                            <div className="flex flex-wrap gap-2">
                              {enrichment.key_features.map((feat, k) => (
                                <Badge key={k} variant="secondary" className="text-xs">
                                  {feat}
                                </Badge>
                              ))}
                            </div>
                          )}

                          {/* Full enrichment details */}
                          {enrichment && (
                            <div className="pt-3 space-y-3 border-t border-border/50">
                              {enrichment.description && enrichment.description !== enrichment.summary && (
                                <p className="text-sm text-muted-foreground">
                                  {enrichment.description}
                                </p>
                              )}

                              {enrichment.parameters && enrichment.parameters.length > 0 && (
                                <div>
                                  <p className="text-sm font-medium mb-2">Parameters</p>
                                  <div className="space-y-1">
                                    {enrichment.parameters.map((p, k) => (
                                      <div key={k} className="text-sm flex items-start gap-2">
                                        <code className="bg-background px-1.5 py-0.5 rounded font-mono text-primary">
                                          {p.name}
                                        </code>
                                        <span className="text-muted-foreground">{p.description}</span>
                                      </div>
                                    ))}
                                  </div>
                                </div>
                              )}

                              {enrichment.returns && (
                                <div>
                                  <p className="text-sm font-medium mb-1">Returns</p>
                                  <p className="text-sm text-muted-foreground">{enrichment.returns}</p>
                                </div>
                              )}

                              {/* Usage Examples */}
                              {(enrichment.usage_examples || enrichment.examples)?.length > 0 && (
                                <div>
                                  <p className="text-sm font-medium mb-2">Usage Example</p>
                                  {(enrichment.usage_examples || enrichment.examples)?.map((example, k) => (
                                    <pre
                                      key={k}
                                      className="text-xs bg-background p-3 rounded-lg overflow-x-auto font-mono border"
                                    >
                                      {example}
                                    </pre>
                                  ))}
                                </div>
                              )}
                            </div>
                          )}

                          {/* Entity parameters from AST */}
                          {!enrichment && entity.parameters && entity.parameters.length > 0 && (
                            <div>
                              <p className="text-sm font-medium mb-2">Parameters</p>
                              <div className="flex flex-wrap gap-2">
                                {entity.parameters.map((param, k) => (
                                  <code key={k} className="text-xs bg-background px-2 py-1 rounded font-mono">
                                    {param.name}
                                    {param.type && <span className="text-primary">: {param.type}</span>}
                                    {param.default && <span className="text-muted-foreground"> = {param.default}</span>}
                                  </code>
                                ))}
                              </div>
                            </div>
                          )}

                          {/* Return type */}
                          {entity.return_type && (
                            <div className="text-sm">
                              <span className="font-medium">Returns: </span>
                              <code className="text-primary font-mono">{entity.return_type}</code>
                            </div>
                          )}

                          {/* Decorators */}
                          {entity.decorators && entity.decorators.length > 0 && (
                            <div className="flex flex-wrap gap-1">
                              {entity.decorators.map((dec, k) => (
                                <code key={k} className="text-xs bg-background px-2 py-1 rounded font-mono text-muted-foreground">
                                  @{dec}
                                </code>
                              ))}
                            </div>
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
