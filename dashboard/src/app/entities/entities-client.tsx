"use client";

import { useState, useMemo } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Search, Code2, Box, Braces, Brain, ChevronDown, ChevronRight, FileCode } from "lucide-react";
import type { CodeEntity, EnrichmentData } from "@/lib/data";

interface EntitiesPageClientProps {
  entities: CodeEntity[];
  enrichment: EnrichmentData | null;
}

export function EntitiesPageClient({ entities, enrichment }: EntitiesPageClientProps) {
  const [search, setSearch] = useState("");
  const [typeFilter, setTypeFilter] = useState<string>("all");
  const [showEnrichedOnly, setShowEnrichedOnly] = useState(false);
  const [expandedEntity, setExpandedEntity] = useState<string | null>(null);

  const enrichedKeys = Object.keys(enrichment || {});

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

  const filteredEntities = useMemo(() => {
    return entities.filter((entity) => {
      const matchesSearch =
        search === "" ||
        entity.name.toLowerCase().includes(search.toLowerCase()) ||
        entity.file_path.toLowerCase().includes(search.toLowerCase()) ||
        entity.docstring?.toLowerCase().includes(search.toLowerCase()) ||
        getEnrichment(entity)?.summary?.toLowerCase().includes(search.toLowerCase());

      const matchesType = typeFilter === "all" || entity.type === typeFilter;
      const matchesEnriched = !showEnrichedOnly || isEnriched(entity);

      return matchesSearch && matchesType && matchesEnriched;
    });
  }, [entities, search, typeFilter, showEnrichedOnly]);

  const stats = useMemo(() => {
    return {
      functions: entities.filter((e) => e.type === "function").length,
      classes: entities.filter((e) => e.type === "class").length,
      methods: entities.filter((e) => e.type === "method").length,
      enriched: entities.filter(isEnriched).length,
    };
  }, [entities]);

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

  const getEntityKey = (entity: CodeEntity, i: number) =>
    `${entity.file_path}:${entity.name}:${i}`;

  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Code Entities</h1>
        <p className="text-muted-foreground mt-1">
          Browse and search functions, classes, and methods
        </p>
      </div>

      {/* Stats */}
      <div className="flex gap-3 flex-wrap">
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
        {stats.enriched > 0 && (
          <Badge
            variant={showEnrichedOnly ? "default" : "secondary"}
            className="px-3 py-1 cursor-pointer"
            onClick={() => setShowEnrichedOnly(!showEnrichedOnly)}
          >
            <Brain className="h-3 w-3 mr-1" />
            {stats.enriched} documented
            {showEnrichedOnly && " (filtered)"}
          </Badge>
        )}
      </div>

      {/* Search and Filter */}
      <div className="flex gap-4 flex-wrap">
        <div className="relative flex-1 min-w-[200px]">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="Search by name, file, or description..."
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

      {/* Results Count */}
      <p className="text-sm text-muted-foreground">
        Showing {Math.min(filteredEntities.length, 50)} of {filteredEntities.length} entities
        {showEnrichedOnly && " (documented only)"}
      </p>

      {/* Entity List */}
      <div className="space-y-3">
        {filteredEntities.slice(0, 50).map((entity, i) => {
          const entityKey = getEntityKey(entity, i);
          const enrichmentData = getEnrichment(entity);
          const isExpanded = expandedEntity === entityKey;
          const hasEnrichment = !!enrichmentData;

          return (
            <Card
              key={entityKey}
              className={`transition-colors ${hasEnrichment ? "hover:border-primary/50 cursor-pointer" : ""}`}
              onClick={() => hasEnrichment && setExpandedEntity(isExpanded ? null : entityKey)}
            >
              <CardContent className="py-4">
                <div className="flex items-start gap-3">
                  {/* Type Icon */}
                  <div className="mt-0.5 text-muted-foreground">
                    {typeIcon(entity.type)}
                  </div>

                  {/* Main Content */}
                  <div className="flex-1 min-w-0">
                    {/* Header Row */}
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="font-mono font-medium">
                        {entity.parent_class ? `${entity.parent_class}.` : ""}
                        {entity.name}
                      </span>
                      <Badge variant="outline" className="text-xs">
                        {entity.type}
                      </Badge>
                      {hasEnrichment && (
                        <Badge variant="secondary" className="text-xs gap-1">
                          <Brain className="h-3 w-3" />
                          documented
                        </Badge>
                      )}
                    </div>

                    {/* File Location */}
                    <div className="flex items-center gap-1 text-sm text-muted-foreground mt-1">
                      <FileCode className="h-3 w-3" />
                      <span className="font-mono text-xs truncate">
                        {entity.file_path}:{entity.line_number}
                      </span>
                    </div>

                    {/* Summary - Always visible */}
                    <p className="text-sm text-muted-foreground mt-2">
                      {enrichmentData?.summary ||
                        entity.docstring?.split("\n")[0] ||
                        "No description available"}
                    </p>

                    {/* Expanded Content */}
                    {isExpanded && enrichmentData && (
                      <div className="mt-4 pt-4 border-t space-y-4">
                        {enrichmentData.description && (
                          <div>
                            <h4 className="text-sm font-medium mb-1">Description</h4>
                            <p className="text-sm text-muted-foreground">
                              {enrichmentData.description}
                            </p>
                          </div>
                        )}

                        {enrichmentData.parameters && enrichmentData.parameters.length > 0 && (
                          <div>
                            <h4 className="text-sm font-medium mb-2">Parameters</h4>
                            <div className="space-y-2">
                              {enrichmentData.parameters.map((param, j) => (
                                <div key={j} className="text-sm">
                                  <code className="bg-muted px-1 rounded font-mono">
                                    {param.name}
                                  </code>
                                  <span className="text-muted-foreground ml-2">
                                    {param.description}
                                  </span>
                                </div>
                              ))}
                            </div>
                          </div>
                        )}

                        {enrichmentData.returns && (
                          <div>
                            <h4 className="text-sm font-medium mb-1">Returns</h4>
                            <p className="text-sm text-muted-foreground">
                              {enrichmentData.returns}
                            </p>
                          </div>
                        )}

                        {enrichmentData.examples && enrichmentData.examples.length > 0 && (
                          <div>
                            <h4 className="text-sm font-medium mb-2">Examples</h4>
                            {enrichmentData.examples.map((example, j) => (
                              <pre
                                key={j}
                                className="text-sm bg-muted p-3 rounded-lg overflow-x-auto font-mono"
                              >
                                {example}
                              </pre>
                            ))}
                          </div>
                        )}
                      </div>
                    )}
                  </div>

                  {/* Expand Indicator */}
                  {hasEnrichment && (
                    <div className="text-muted-foreground">
                      {isExpanded ? (
                        <ChevronDown className="h-5 w-5" />
                      ) : (
                        <ChevronRight className="h-5 w-5" />
                      )}
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>
          );
        })}
      </div>

      {filteredEntities.length > 50 && (
        <p className="text-center text-muted-foreground text-sm py-4">
          Showing first 50 results. Use search to narrow down.
        </p>
      )}

      {filteredEntities.length === 0 && (
        <Card>
          <CardContent className="py-10 text-center">
            <Search className="h-10 w-10 mx-auto text-muted-foreground mb-3" />
            <p className="text-muted-foreground">
              No entities found matching your search.
            </p>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
