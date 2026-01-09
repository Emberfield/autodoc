import { loadDashboardData, buildFileTree } from "@/lib/data";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { FileTree } from "@/components/file-tree";
import { FolderTree, Brain, Code2 } from "lucide-react";

export const dynamic = "force-dynamic";

export default function FilesPage() {
  const data = loadDashboardData();
  const fileTree = data.analysis?.entities
    ? buildFileTree(data.analysis.entities, data.enrichment)
    : null;

  // Group files by enrichment status for quick filtering
  const fileStats = new Map<string, { entityCount: number; enrichedCount: number }>();
  data.analysis?.entities?.forEach(e => {
    const existing = fileStats.get(e.file_path) || { entityCount: 0, enrichedCount: 0 };
    existing.entityCount++;

    const enrichmentKeys = Object.keys(data.enrichment || {});
    if (enrichmentKeys.some(k => k.includes(e.name) && k.includes(e.file_path.split('/').pop() || ''))) {
      existing.enrichedCount++;
    }
    fileStats.set(e.file_path, existing);
  });

  const enrichedFiles = Array.from(fileStats.entries())
    .filter(([_, stats]) => stats.enrichedCount > 0)
    .sort((a, b) => b[1].enrichedCount - a[1].enrichedCount);

  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Files</h1>
        <p className="text-muted-foreground mt-1">
          Browse the codebase structure
        </p>
      </div>

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
            {enrichedFiles.length} files with docs
          </Badge>
        )}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* File Tree */}
        <Card className="lg:col-span-2">
          <CardHeader className="pb-3">
            <CardTitle className="text-base flex items-center gap-2">
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

        {/* Documented Files */}
        {enrichedFiles.length > 0 && (
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-base flex items-center gap-2">
                <Brain className="h-5 w-5" />
                Documented Files
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-2">
                {enrichedFiles.slice(0, 15).map(([filePath, stats]) => (
                  <div
                    key={filePath}
                    className="flex items-center justify-between p-2 rounded hover:bg-muted/50"
                  >
                    <span className="font-mono text-xs truncate flex-1 mr-2">
                      {filePath.split('/').pop()}
                    </span>
                    <Badge variant="secondary" className="text-xs">
                      {stats.enrichedCount}/{stats.entityCount}
                    </Badge>
                  </div>
                ))}
                {enrichedFiles.length > 15 && (
                  <p className="text-xs text-muted-foreground text-center pt-2">
                    +{enrichedFiles.length - 15} more files
                  </p>
                )}
              </div>
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  );
}
