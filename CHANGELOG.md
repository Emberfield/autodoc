# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.6.0] - 2025-06-27

### Added
- **Enhanced Search Capabilities**
  - Regex pattern matching with `--regex` flag
  - Filter by entity type with `--type` option (function, class, method, etc.)
  - Filter by file pattern with `--file` option (supports wildcards)
  
- **Dry-run Mode for Enrichment**
  - Preview inline docstring changes without modifying files
  - Preview module enrichment file generation
  - Clear "DRY RUN:" prefixes in output
  
- **Diff Command**
  - Compare analysis caches to see what changed
  - Automatic backup creation for easy comparison
  - Detailed view shows what changed in modified entities
  
- **Export/Import for Team Sharing**
  - Export analysis data to zip archives
  - Include enrichment cache and config optionally
  - Import shared analysis from team members
  
- **Progress Bars**
  - Visual feedback during file analysis
  - Progress tracking for inline enrichment
  - Better user experience for long operations
  
- **Test Coverage Mapping**
  - `test-map` command analyzes which functions are tested
  - Identifies untested functions
  - Multiple output formats: table, JSON, markdown
  - Shows coverage percentage and statistics

### Changed
- `save()` method now creates automatic backups for diff comparisons

### Fixed
- Various bug fixes and improvements

## [0.5.0] - Previous Release
- Inline documentation enrichment
- Module-level enrichment files
- And more...