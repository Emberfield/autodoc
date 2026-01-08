import { loadDashboardData } from "@/lib/data";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Package, FileCode, Shield, Code2 } from "lucide-react";

export const dynamic = "force-dynamic";

export default function PacksPage() {
  const data = loadDashboardData();
  const packs = data.config?.context_packs || [];

  // Match entities to packs (simple pattern matching)
  const getPackEntities = (pack: typeof packs[0]) => {
    if (!data.analysis?.entities || !pack.files) return [];

    return data.analysis.entities.filter(entity => {
      return pack.files?.some(pattern => {
        // Simple glob matching
        const regex = new RegExp(
          '^' + pattern.replace(/\*\*/g, '.*').replace(/\*/g, '[^/]*') + '$'
        );
        return regex.test(entity.file_path);
      });
    });
  };

  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Context Packs</h1>
        <p className="text-muted-foreground mt-1">
          Logical groupings of related code for focused AI context
        </p>
      </div>

      <Badge variant="outline" className="px-3 py-1">
        {packs.length} packs configured
      </Badge>

      {packs.length > 0 ? (
        <div className="space-y-4">
          {packs.map((pack) => {
            const packEntities = getPackEntities(pack);
            const uniqueFiles = new Set(packEntities.map(e => e.file_path));

            return (
              <Card key={pack.name}>
                <CardHeader>
                  <div className="flex items-start justify-between">
                    <div className="space-y-1">
                      <CardTitle className="flex items-center gap-2">
                        <Package className="h-5 w-5" />
                        {pack.display_name || pack.name}
                        {pack.security_level && (
                          <Badge
                            variant={pack.security_level === "critical" ? "destructive" : "secondary"}
                            className="gap-1"
                          >
                            <Shield className="h-3 w-3" />
                            {pack.security_level}
                          </Badge>
                        )}
                      </CardTitle>
                      {pack.description && (
                        <CardDescription>{pack.description}</CardDescription>
                      )}
                    </div>
                    <div className="flex gap-2">
                      <Badge variant="outline">{uniqueFiles.size} files</Badge>
                      <Badge variant="outline">{packEntities.length} entities</Badge>
                    </div>
                  </div>
                </CardHeader>
                <CardContent className="space-y-4">
                  {/* File patterns */}
                  {pack.files && pack.files.length > 0 && (
                    <div>
                      <p className="text-xs font-medium text-muted-foreground mb-2">Patterns</p>
                      <div className="flex flex-wrap gap-2">
                        {pack.files.map((pattern, i) => (
                          <code
                            key={i}
                            className="text-xs bg-muted px-2 py-1 rounded font-mono"
                          >
                            {pattern}
                          </code>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Sample entities */}
                  {packEntities.length > 0 && (
                    <div>
                      <p className="text-xs font-medium text-muted-foreground mb-2">
                        Key entities in this pack
                      </p>
                      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-2">
                        {packEntities
                          .filter(e => e.type === 'class' || e.type === 'function')
                          .slice(0, 6)
                          .map((entity, i) => (
                            <div
                              key={`${entity.file_path}:${entity.name}:${i}`}
                              className="p-2 bg-muted/50 rounded text-sm"
                            >
                              <div className="flex items-center gap-1">
                                <Code2 className="h-3 w-3 text-muted-foreground" />
                                <span className="font-mono font-medium truncate">
                                  {entity.name}
                                </span>
                              </div>
                              <span className="text-xs text-muted-foreground">
                                {entity.type}
                              </span>
                            </div>
                          ))}
                      </div>
                      {packEntities.length > 6 && (
                        <p className="text-xs text-muted-foreground mt-2">
                          +{packEntities.length - 6} more entities
                        </p>
                      )}
                    </div>
                  )}
                </CardContent>
              </Card>
            );
          })}
        </div>
      ) : (
        <Card className="border-dashed">
          <CardContent className="py-10 text-center">
            <Package className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
            <h2 className="text-xl font-semibold mb-2">No Packs Configured</h2>
            <p className="text-muted-foreground mb-4 max-w-md mx-auto">
              Context packs group related code together. Auto-generate them based on your
              codebase structure or define them manually.
            </p>
            <code className="bg-muted px-4 py-2 rounded text-sm">
              autodoc pack auto-generate --save
            </code>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
