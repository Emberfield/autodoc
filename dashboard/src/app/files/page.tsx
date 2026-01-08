import { loadDashboardData, buildFileTree } from "@/lib/data";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { FileTree } from "@/components/file-tree";
import { FolderTree } from "lucide-react";

export const dynamic = "force-dynamic";

export default function FilesPage() {
  const data = loadDashboardData();
  const fileTree = data.analysis?.entities
    ? buildFileTree(data.analysis.entities, data.enrichment)
    : null;

  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Files</h1>
        <p className="text-muted-foreground mt-1">
          Browse your codebase file structure
        </p>
      </div>

      <div className="flex gap-2">
        <Badge variant="outline">{data.stats.totalFiles} files</Badge>
        <Badge variant="outline">{data.stats.totalEntities} entities</Badge>
        {data.stats.enrichedCount > 0 && (
          <Badge variant="secondary">{data.stats.enrichedCount} enriched</Badge>
        )}
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <FolderTree className="h-5 w-5" />
            File Tree
          </CardTitle>
        </CardHeader>
        <CardContent>
          {fileTree ? (
            <FileTree node={fileTree} />
          ) : (
            <p className="text-muted-foreground">
              No files found. Run <code>autodoc analyze . --save</code> first.
            </p>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
