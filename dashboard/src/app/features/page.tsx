import { loadDashboardData } from "@/lib/data";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Sparkles, FileCode, Brain } from "lucide-react";

export const dynamic = "force-dynamic";

export default function FeaturesPage() {
  const data = loadDashboardData();
  const features = data.features?.features
    ? Object.values(data.features.features)
    : [];

  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Detected Features</h1>
        <p className="text-muted-foreground mt-1">
          Code clusters automatically detected using graph analysis
        </p>
      </div>

      {data.features && (
        <div className="flex gap-2">
          <Badge variant="outline">{features.length} features</Badge>
          <Badge variant="secondary">
            Modularity: {data.features.modularity.toFixed(2)}
          </Badge>
        </div>
      )}

      {features.length > 0 ? (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {features.map((feature) => (
            <Card key={feature.id}>
              <CardHeader>
                <CardTitle className="flex items-center justify-between">
                  <span className="flex items-center gap-2">
                    <Sparkles className="h-5 w-5 text-primary" />
                    {feature.display_name || feature.name || `Feature ${feature.id}`}
                  </span>
                  <Badge variant="outline">{feature.file_count} files</Badge>
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                {feature.reasoning && (
                  <p className="text-sm text-muted-foreground">
                    {feature.reasoning}
                  </p>
                )}

                {feature.sample_files && feature.sample_files.length > 0 && (
                  <div className="space-y-2">
                    <p className="text-xs font-medium text-muted-foreground">
                      Sample files:
                    </p>
                    <div className="space-y-1">
                      {feature.sample_files.slice(0, 5).map((file, i) => (
                        <div
                          key={i}
                          className="flex items-start gap-2 text-sm p-2 rounded bg-muted/50"
                        >
                          <FileCode className="h-4 w-4 text-muted-foreground flex-shrink-0 mt-0.5" />
                          <div className="flex-1 min-w-0">
                            <p className="font-mono text-xs truncate">
                              {file.path}
                            </p>
                            {file.summary && (
                              <p className="text-xs text-muted-foreground mt-0.5 line-clamp-1">
                                {file.summary}
                              </p>
                            )}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {!feature.name && (
                  <div className="flex items-center gap-2 text-sm text-muted-foreground">
                    <Brain className="h-4 w-4" />
                    <span>
                      Run <code className="text-xs bg-muted px-1 py-0.5 rounded">autodoc features name</code> to generate semantic names
                    </span>
                  </div>
                )}
              </CardContent>
            </Card>
          ))}
        </div>
      ) : (
        <Card>
          <CardContent className="py-10 text-center">
            <Sparkles className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
            <h2 className="text-xl font-semibold mb-2">No Features Detected</h2>
            <p className="text-muted-foreground mb-4">
              Run feature detection to discover code clusters.
            </p>
            <div className="space-y-2">
              <code className="bg-muted px-4 py-2 rounded text-sm block">
                autodoc graph --clear
              </code>
              <code className="bg-muted px-4 py-2 rounded text-sm block">
                autodoc features detect
              </code>
            </div>
            <p className="text-xs text-muted-foreground mt-4">
              Requires Neo4j with Graph Data Science plugin
            </p>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
