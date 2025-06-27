#!/usr/bin/env python3
"""
Makefile parser for extracting targets and their descriptions.
"""

import re
from pathlib import Path
from typing import Dict, List


class MakefileParser:
    """Parse Makefile to extract targets and their descriptions."""
    
    def __init__(self, makefile_path: Path):
        self.makefile_path = makefile_path
        self.targets: Dict[str, Dict[str, str]] = {}
        
    def parse(self) -> Dict[str, Dict[str, str]]:
        """Parse the Makefile and return targets with their descriptions."""
        if not self.makefile_path.exists():
            return {}
            
        try:
            with open(self.makefile_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            # Parse targets with descriptions (## comments)
            # Pattern: target: deps ## description
            target_pattern = re.compile(
                r'^([a-zA-Z0-9_-]+):(?:[^#\n]*)(?:##\s*(.*))?$',
                re.MULTILINE
            )
            
            for match in target_pattern.finditer(content):
                target_name = match.group(1)
                description = match.group(2) or ""
                
                # Skip special targets
                if target_name.startswith('.'):
                    continue
                    
                self.targets[target_name] = {
                    'name': target_name,
                    'description': description.strip(),
                    'command': f'make {target_name}'
                }
                
            # Also look for variables that might indicate commands
            # e.g., QUERY in "make search QUERY='...'"
            self._extract_command_details(content)
            
        except Exception as e:
            print(f"Error parsing Makefile: {e}")
            
        return self.targets
        
    def _extract_command_details(self, content: str):
        """Extract additional command details from Makefile content."""
        # Look for commands that require parameters
        # Pattern: target uses $(VARIABLE)
        for target_name, target_info in self.targets.items():
            # Search for the target's recipe
            target_section = re.search(
                rf'^{re.escape(target_name)}:.*?(?=^[a-zA-Z0-9_-]+:|$)',
                content,
                re.MULTILINE | re.DOTALL
            )
            
            if target_section:
                section_text = target_section.group(0)
                
                # Look for variable usage
                var_pattern = re.compile(r'\$\(([A-Z_]+)\)')
                variables = var_pattern.findall(section_text)
                
                if variables:
                    # Update command with parameter hints
                    params = [f'{var}="..."' for var in variables if var not in ['NC', 'GREEN', 'YELLOW', 'RED']]
                    if params:
                        target_info['command'] = f'make {target_name} {" ".join(params)}'
                        
                # Check for common patterns in descriptions
                if 'usage:' in target_info['description'].lower():
                    # Extract usage from description
                    usage_match = re.search(r'usage:\s*(.+)', target_info['description'], re.IGNORECASE)
                    if usage_match:
                        target_info['command'] = usage_match.group(1).strip()
                        
    def get_categorized_targets(self) -> Dict[str, List[Dict[str, str]]]:
        """Get targets organized by category."""
        categories = {
            'setup': [],
            'build': [],
            'test': [],
            'lint': [],
            'format': [],
            'publish': [],
            'clean': [],
            'help': [],
            'other': []
        }
        
        for target_name, target_info in self.targets.items():
            # Categorize based on target name
            added = False
            for category in categories:
                if category in target_name:
                    categories[category].append(target_info)
                    added = True
                    break
                    
            if not added:
                # Check description for category hints
                desc_lower = target_info['description'].lower()
                for category in categories:
                    if category in desc_lower:
                        categories[category].append(target_info)
                        added = True
                        break
                        
            if not added:
                categories['other'].append(target_info)
                
        # Remove empty categories
        return {k: v for k, v in categories.items() if v}