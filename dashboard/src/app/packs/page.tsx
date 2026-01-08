import { loadDashboardData } from "@/lib/data";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Package, FileCode, Shield } from "lucide-react";

export const dynamic = "force-dynamic";

export default function PacksPage() {
  const data = loadDashboardData();
  const packs = data.config?.context_packs || [];

  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Context Packs</h1>
        <p className="text-muted-foreground mt-1">
          Logical groupings of related code for focused context
        </p>
      </div>

      <Badge variant="outline">{packs.length} packs</Badge>

      {packs.length > 0 ? (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {packs.map((pack) => (
            <Card key={pack.name}>
              <CardHeader>
                <CardTitle className="flex items-center justify-between">
                  <span className="flex items-center gap-2">
                    <Package className="h-5 w-5" />
                    {pack.display_name || pack.name}
                  </span>
                  {pack.security_level && (
                    <Badge
                      variant={
                        pack.security_level === "critical"
                          ? "destructive"
                          : "secondary"
                      }
                      className="gap-1"
                    >
                      <Shield className="h-3 w-3" />
                      {pack.security_level}
                    </Badge>
                  )}
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                {pack.description && (
                  <p className="text-sm text-muted-foreground">
                    {pack.description}
                  </p>
                )}

                <div className="flex items-center gap-2">
                  <FileCode className="h-4 w-4 text-muted-foreground" />
                  <span className="text-sm">
                    {pack.files?.length || 0} file patterns
                  </span>
                </div>

                {pack.files && pack.files.length > 0 && (
                  <div className="space-y-1">
                    <p className="text-xs font-medium text-muted-foreground">
                      Patterns:
                    </p>
                    <div className="flex flex-wrap gap-1">
                      {pack.files.slice(0, 5).map((file, i) => (
                        <Badge key={i} variant="outline" className="text-xs font-mono">
                          {file}
                        </Badge>
                      ))}
                      {pack.files.length > 5 && (
                        <Badge variant="outline" className="text-xs">
                          +{pack.files.length - 5} more
                        </Badge>
                      )}
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>
          ))}
        </div>
      ) : (
        <Card>
          <CardContent className="py-10 text-center">
            <Package className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
            <h2 className="text-xl font-semibold mb-2">No Packs Defined</h2>
            <p className="text-muted-foreground mb-4">
              Auto-generate context packs based on your codebase structure.
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
