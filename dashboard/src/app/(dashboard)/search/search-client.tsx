"use client";

import { useState, useMemo } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Search, Code2, Braces, Box, Brain, Sparkles, FileCode, Package } from "lucide-react";
import type { CodeEntity, EnrichmentData, DetectedFeature, ContextPack } from "@/lib/data";

interface SearchPageClientProps {
  entities: CodeEntity[];
  enrichment: EnrichmentData | null;
  features: DetectedFeature[];
  packs: ContextPack[];
}

interface SearchResult {
  type: "entity" | "feature" | "pack";
  score: number;
  item: CodeEntity | DetectedFeature | ContextPack;
  matchReason: string;
  enrichment?: EnrichmentData[string];
}

export function SearchPageClient({ entities, enrichment, features, packs }: SearchPageClientProps) {
  const [query, setQuery] = useState("");

  const getEnrichment = (entity: CodeEntity) => {
    const enrichmentKeys = Object.keys(enrichment || {});
    const key = enrichmentKeys.find(k =>
      k.includes(entity.name) && k.includes(entity.file_path.split("/").pop() || "")
    );
    return key ? enrichment?.[key] : undefined;
  };

  // Simple scoring function based on keyword matching
  const scoreMatch = (text: string, searchTerms: string[]): { score: number; matched: string[] } => {
    const lowerText = text.toLowerCase();
    const matched: string[] = [];
    let score = 0;

    for (const term of searchTerms) {
      if (lowerText.includes(term)) {
        score += 1;
        matched.push(term);
        // Bonus for exact word match
        if (new RegExp(`\\b${term}\\b`).test(lowerText)) {
          score += 0.5;
        }
      }
    }

    return { score, matched };
  };

  const results = useMemo((): SearchResult[] => {
    if (!query.trim() || query.length < 2) return [];

    const searchTerms = query.toLowerCase().split(/\s+/).filter(t => t.length > 1);
    const results: SearchResult[] = [];

    // Search entities
    for (const entity of entities) {
      const entityEnrichment = getEnrichment(entity);
      const searchText = [
        entity.name,
        entity.docstring || "",
        entity.file_path,
        entityEnrichment?.summary || "",
        entityEnrichment?.description || "",
      ].join(" ");

      const { score, matched } = scoreMatch(searchText, searchTerms);

      if (score > 0) {
        results.push({
          type: "entity",
          score,
          item: entity,
          matchReason: `Matched: ${matched.join(", ")}`,
          enrichment: entityEnrichment,
        });
      }
    }

    // Search features
    for (const feature of features) {
      const searchText = [
        feature.name || "",
        feature.display_name || "",
        feature.reasoning || "",
        feature.files.join(" "),
      ].join(" ");

      const { score, matched } = scoreMatch(searchText, searchTerms);

      if (score > 0) {
        results.push({
          type: "feature",
          score: score + 0.5, // Boost features slightly
          item: feature,
          matchReason: `Matched: ${matched.join(", ")}`,
        });
      }
    }

    // Search packs
    for (const pack of packs) {
      const searchText = [
        pack.name,
        pack.display_name,
        pack.description || "",
      ].join(" ");

      const { score, matched } = scoreMatch(searchText, searchTerms);

      if (score > 0) {
        results.push({
          type: "pack",
          score,
          item: pack,
          matchReason: `Matched: ${matched.join(", ")}`,
        });
      }
    }

    // Sort by score descending
    return results.sort((a, b) => b.score - a.score).slice(0, 20);
  }, [query, entities, features, packs]);

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

  const exampleQueries = [
    "authentication login",
    "API response",
    "security validation",
    "routing endpoint",
    "error handling",
    "middleware",
  ];

  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Search</h1>
        <p className="text-muted-foreground mt-1">
          Search across entities, features, and packs
        </p>
      </div>

      {/* Search Input */}
      <Card>
        <CardContent className="pt-4">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-5 w-5 text-muted-foreground" />
            <Input
              placeholder="Search for functions, classes, features..."
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              className="pl-12 text-lg h-12"
              autoFocus
            />
          </div>

          {/* Example queries */}
          {!query && (
            <div className="mt-4">
              <p className="text-sm text-muted-foreground mb-2">Try searching for:</p>
              <div className="flex flex-wrap gap-2">
                {exampleQueries.map((eq) => (
                  <button
                    key={eq}
                    onClick={() => setQuery(eq)}
                    className="px-3 py-1 text-sm bg-muted rounded-full hover:bg-muted/80 transition-colors"
                  >
                    {eq}
                  </button>
                ))}
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Results */}
      {query.length >= 2 && (
        <div className="space-y-4">
          <p className="text-sm text-muted-foreground">
            {results.length} results for "{query}"
          </p>

          {results.length > 0 ? (
            <div className="space-y-3">
              {results.map((result, i) => {
                if (result.type === "entity") {
                  const entity = result.item as CodeEntity;
                  return (
                    <Card key={`entity-${i}`} className="hover:border-primary/50 transition-colors">
                      <CardContent className="py-4">
                        <div className="flex items-start gap-3">
                          <div className="mt-0.5 text-muted-foreground">
                            {typeIcon(entity.type)}
                          </div>
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center gap-2 flex-wrap">
                              <span className="font-mono font-medium">
                                {entity.parent_class ? `${entity.parent_class}.` : ""}
                                {entity.name}
                              </span>
                              <Badge variant="outline" className="text-xs">
                                {entity.type}
                              </Badge>
                              {result.enrichment && (
                                <Badge variant="secondary" className="text-xs gap-1">
                                  <Brain className="h-3 w-3" />
                                  documented
                                </Badge>
                              )}
                            </div>
                            <div className="flex items-center gap-1 text-sm text-muted-foreground mt-1">
                              <FileCode className="h-3 w-3" />
                              <span className="font-mono text-xs">
                                {entity.file_path}:{entity.line_number}
                              </span>
                            </div>
                            <p className="text-sm text-muted-foreground mt-2">
                              {result.enrichment?.summary ||
                                entity.docstring?.split("\n")[0] ||
                                "No description"}
                            </p>
                          </div>
                        </div>
                      </CardContent>
                    </Card>
                  );
                }

                if (result.type === "feature") {
                  const feature = result.item as DetectedFeature;
                  return (
                    <Card key={`feature-${i}`} className="hover:border-primary/50 transition-colors">
                      <CardContent className="py-4">
                        <div className="flex items-start gap-3">
                          <div className="mt-0.5 text-primary">
                            <Sparkles className="h-5 w-5" />
                          </div>
                          <div className="flex-1">
                            <div className="flex items-center gap-2">
                              <span className="font-medium">
                                {feature.display_name || feature.name || `Feature ${feature.id}`}
                              </span>
                              <Badge variant="outline" className="text-xs">
                                Feature
                              </Badge>
                              <Badge variant="outline" className="text-xs">
                                {feature.file_count} files
                              </Badge>
                            </div>
                            {feature.reasoning && (
                              <p className="text-sm text-muted-foreground mt-2">
                                {feature.reasoning}
                              </p>
                            )}
                          </div>
                        </div>
                      </CardContent>
                    </Card>
                  );
                }

                if (result.type === "pack") {
                  const pack = result.item as ContextPack;
                  return (
                    <Card key={`pack-${i}`} className="hover:border-primary/50 transition-colors">
                      <CardContent className="py-4">
                        <div className="flex items-start gap-3">
                          <div className="mt-0.5 text-muted-foreground">
                            <Package className="h-5 w-5" />
                          </div>
                          <div className="flex-1">
                            <div className="flex items-center gap-2">
                              <span className="font-medium">
                                {pack.display_name || pack.name}
                              </span>
                              <Badge variant="outline" className="text-xs">
                                Context Pack
                              </Badge>
                            </div>
                            {pack.description && (
                              <p className="text-sm text-muted-foreground mt-2">
                                {pack.description}
                              </p>
                            )}
                          </div>
                        </div>
                      </CardContent>
                    </Card>
                  );
                }

                return null;
              })}
            </div>
          ) : (
            <Card>
              <CardContent className="py-8 text-center">
                <Search className="h-10 w-10 mx-auto text-muted-foreground mb-3" />
                <p className="text-muted-foreground">No results found for "{query}"</p>
                <p className="text-sm text-muted-foreground mt-2">
                  Try different keywords or use the CLI for full semantic search:
                </p>
                <code className="text-sm bg-muted px-3 py-1 rounded mt-2 inline-block">
                  autodoc search "{query}"
                </code>
              </CardContent>
            </Card>
          )}
        </div>
      )}

      {/* CLI Info */}
      <Card className="mt-6">
        <CardHeader>
          <CardTitle className="text-base">Full Semantic Search</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3 text-sm">
          <p className="text-muted-foreground">
            For vector-based semantic search with embeddings, use the CLI:
          </p>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            <div className="p-3 bg-muted rounded-lg">
              <p className="font-medium mb-1">Global search</p>
              <code className="text-xs">autodoc search "your query"</code>
            </div>
            <div className="p-3 bg-muted rounded-lg">
              <p className="font-medium mb-1">Pack-specific search</p>
              <code className="text-xs">autodoc pack query security "auth flow"</code>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
