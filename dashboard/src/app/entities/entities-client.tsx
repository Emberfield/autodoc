"use client";

import { useState, useMemo } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Search, Code2, Box, Braces } from "lucide-react";
import type { CodeEntity, EnrichmentData } from "@/lib/data";

interface EntitiesPageClientProps {
  entities: CodeEntity[];
  enrichment: EnrichmentData | null;
}

export function EntitiesPageClient({ entities, enrichment }: EntitiesPageClientProps) {
  const [search, setSearch] = useState("");
  const [typeFilter, setTypeFilter] = useState<string>("all");

  const enrichedKeys = Object.keys(enrichment || {});

  const filteredEntities = useMemo(() => {
    return entities.filter((entity) => {
      const matchesSearch =
        search === "" ||
        entity.name.toLowerCase().includes(search.toLowerCase()) ||
        entity.file_path.toLowerCase().includes(search.toLowerCase()) ||
        entity.docstring?.toLowerCase().includes(search.toLowerCase());

      const matchesType = typeFilter === "all" || entity.type === typeFilter;

      return matchesSearch && matchesType;
    });
  }, [entities, search, typeFilter]);

  const stats = useMemo(() => {
    return {
      functions: entities.filter((e) => e.type === "function").length,
      classes: entities.filter((e) => e.type === "class").length,
      methods: entities.filter((e) => e.type === "method").length,
    };
  }, [entities]);

  const isEnriched = (entity: CodeEntity) => {
    return enrichedKeys.some(
      (k) => k.includes(entity.name) && k.includes(entity.file_path.split("/").pop() || "")
    );
  };

  const getEnrichment = (entity: CodeEntity) => {
    const key = enrichedKeys.find(
      (k) => k.includes(entity.name) && k.includes(entity.file_path.split("/").pop() || "")
    );
    return key ? enrichment?.[key] : null;
  };

  const typeIcon = (type: string) => {
    switch (type) {
      case "function":
        return <Braces className="h-4 w-4" />;
      case "class":
        return <Box className="h-4 w-4" />;
      case "method":
        return <Code2 className="h-4 w-4" />;
      default:
        return <Code2 className="h-4 w-4" />;
    }
  };

  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Entities</h1>
        <p className="text-muted-foreground mt-1">
          Browse all functions, classes, and methods in your codebase
        </p>
      </div>

      {/* Stats */}
      <div className="flex gap-4">
        <Badge variant="outline" className="px-3 py-1">
          <Braces className="h-3 w-3 mr-1" />
          {stats.functions} functions
        </Badge>
        <Badge variant="outline" className="px-3 py-1">
          <Box className="h-3 w-3 mr-1" />
          {stats.classes} classes
        </Badge>
        <Badge variant="outline" className="px-3 py-1">
          <Code2 className="h-3 w-3 mr-1" />
          {stats.methods} methods
        </Badge>
      </div>

      {/* Search and Filter */}
      <div className="flex gap-4">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="Search entities by name, file, or docstring..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-10"
          />
        </div>
        <Tabs value={typeFilter} onValueChange={setTypeFilter}>
          <TabsList>
            <TabsTrigger value="all">All</TabsTrigger>
            <TabsTrigger value="function">Functions</TabsTrigger>
            <TabsTrigger value="class">Classes</TabsTrigger>
            <TabsTrigger value="method">Methods</TabsTrigger>
          </TabsList>
        </Tabs>
      </div>

      {/* Results */}
      <Card>
        <CardHeader>
          <CardTitle className="text-sm font-medium">
            Showing {filteredEntities.length} of {entities.length} entities
          </CardTitle>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="w-8"></TableHead>
                <TableHead>Name</TableHead>
                <TableHead>File</TableHead>
                <TableHead>Line</TableHead>
                <TableHead>Description</TableHead>
                <TableHead className="w-20">Status</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {filteredEntities.slice(0, 100).map((entity, i) => {
                const enrichmentData = getEnrichment(entity);
                return (
                  <TableRow key={`${entity.file_path}:${entity.name}:${i}`}>
                    <TableCell>{typeIcon(entity.type)}</TableCell>
                    <TableCell className="font-mono font-medium">
                      {entity.parent_class ? `${entity.parent_class}.` : ""}
                      {entity.name}
                    </TableCell>
                    <TableCell className="text-muted-foreground text-sm">
                      {entity.file_path}
                    </TableCell>
                    <TableCell className="text-muted-foreground">
                      {entity.line_number}
                    </TableCell>
                    <TableCell className="max-w-md truncate text-sm">
                      {enrichmentData?.summary ||
                        entity.docstring?.split("\n")[0] ||
                        "-"}
                    </TableCell>
                    <TableCell>
                      {isEnriched(entity) ? (
                        <Badge variant="default" className="text-xs">
                          Enriched
                        </Badge>
                      ) : (
                        <Badge variant="outline" className="text-xs">
                          Basic
                        </Badge>
                      )}
                    </TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
          {filteredEntities.length > 100 && (
            <p className="text-center text-muted-foreground text-sm mt-4">
              Showing first 100 results. Use search to narrow down.
            </p>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
