"use client";

import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Search, Terminal, ExternalLink } from "lucide-react";

export default function SearchPage() {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const handleSearch = async () => {
    if (!query.trim()) return;
    setLoading(true);
    setResults(
      `To search your codebase, run:\n\nautodoc search "${query}"\n\nOr for pack-specific search:\n\nautodoc pack query <pack-name> "${query}"`
    );
    setLoading(false);
  };

  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Search</h1>
        <p className="text-muted-foreground mt-1">
          Search your codebase using natural language
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Semantic Search</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex gap-2">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <Input
                placeholder="How does user authentication work?"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && handleSearch()}
                className="pl-10"
              />
            </div>
            <Button onClick={handleSearch} disabled={loading}>
              {loading ? "Searching..." : "Search"}
            </Button>
          </div>

          <div className="text-sm text-muted-foreground">
            <p>Example queries:</p>
            <ul className="list-disc list-inside mt-1 space-y-1">
              <li>How does the API handle authentication?</li>
              <li>Where is user validation implemented?</li>
              <li>Find database connection code</li>
            </ul>
          </div>
        </CardContent>
      </Card>

      {results && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Terminal className="h-5 w-5" />
              CLI Commands
            </CardTitle>
          </CardHeader>
          <CardContent>
            <pre className="bg-muted p-4 rounded-lg text-sm overflow-auto">
              {results}
            </pre>
          </CardContent>
        </Card>
      )}

      <Card>
        <CardHeader>
          <CardTitle>Search Features</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="p-4 border rounded-lg">
              <h3 className="font-medium mb-2">Global Search</h3>
              <p className="text-sm text-muted-foreground mb-2">
                Search across your entire codebase
              </p>
              <code className="text-xs bg-muted px-2 py-1 rounded">
                autodoc search &quot;query&quot;
              </code>
            </div>
            <div className="p-4 border rounded-lg">
              <h3 className="font-medium mb-2">Pack Search</h3>
              <p className="text-sm text-muted-foreground mb-2">
                Search within a specific context pack
              </p>
              <code className="text-xs bg-muted px-2 py-1 rounded">
                autodoc pack query auth &quot;login flow&quot;
              </code>
            </div>
            <div className="p-4 border rounded-lg">
              <h3 className="font-medium mb-2">Build Embeddings</h3>
              <p className="text-sm text-muted-foreground mb-2">
                Generate vector embeddings for better search
              </p>
              <code className="text-xs bg-muted px-2 py-1 rounded">
                autodoc pack build --all --embeddings
              </code>
            </div>
            <div className="p-4 border rounded-lg">
              <h3 className="font-medium mb-2">MCP Integration</h3>
              <p className="text-sm text-muted-foreground mb-2">
                Use with AI assistants via MCP
              </p>
              <code className="text-xs bg-muted px-2 py-1 rounded">
                autodoc mcp-server
              </code>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
