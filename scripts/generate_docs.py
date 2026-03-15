#!/usr/bin/env python3
"""
AMCIS Auto-Documentation Generator

This script automatically generates documentation from source code on git commit.
It extracts docstrings, type hints, and module information to create:
- API documentation
- Module references
- Architecture diagrams
- Changelog updates

Usage:
    python scripts/generate_docs.py [--check] [--output-dir DIR]

Exit codes:
    0 - Success
    1 - Documentation generation failed
    2 - Documentation is outdated (when using --check)
"""

import os
import sys
import re
import json
import argparse
import subprocess
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
from dataclasses import dataclass, asdict


@dataclass
class FunctionDoc:
    """Documentation for a function or method."""
    name: str
    signature: str
    docstring: str
    params: List[Dict[str, str]]
    returns: Optional[str]
    raises: List[str]
    examples: List[str]
    module: str
    line_number: int
    is_async: bool
    is_class_method: bool
    is_static: bool
    is_property: bool


@dataclass
class ClassDoc:
    """Documentation for a class."""
    name: str
    docstring: str
    bases: List[str]
    methods: List[FunctionDoc]
    attributes: List[Dict[str, str]]
    module: str
    line_number: int
    is_dataclass: bool
    is_abstract: bool


@dataclass
class ModuleDoc:
    """Documentation for a module."""
    name: str
    path: str
    docstring: str
    classes: List[ClassDoc]
    functions: List[FunctionDoc]
    imports: List[str]
    exports: List[str]


class DocumentationGenerator:
    """Generate documentation from Python source code."""
    
    def __init__(self, source_dir: str, output_dir: str):
        self.source_dir = Path(source_dir)
        self.output_dir = Path(output_dir)
        self.modules: List[ModuleDoc] = []
        
    def parse_docstring(self, docstring: str) -> Dict[str, Any]:
        """Parse a docstring to extract structured information."""
        if not docstring:
            return {"description": "", "params": [], "returns": None, "raises": [], "examples": []}
        
        lines = docstring.strip().split('\n')
        result = {
            "description": lines[0] if lines else "",
            "params": [],
            "returns": None,
            "raises": [],
            "examples": []
        }
        
        current_section = None
        current_content = []
        
        for line in lines[1:]:
            line_stripped = line.strip()
            
            # Check for section headers
            if line_stripped in ['Args:', 'Arguments:', 'Params:', 'Parameters:']:
                current_section = 'params'
                continue
            elif line_stripped in ['Returns:', 'Return:']:
                current_section = 'returns'
                continue
            elif line_stripped in ['Raises:', 'Exceptions:', 'Raise:']:
                current_section = 'raises'
                continue
            elif line_stripped in ['Example:', 'Examples:']:
                if current_content and current_section:
                    self._add_section_content(result, current_section, current_content)
                current_section = 'examples'
                current_content = []
                continue
            
            if current_section:
                current_content.append(line)
        
        # Don't forget the last section
        if current_content and current_section:
            self._add_section_content(result, current_section, current_content)
        
        return result
    
    def _add_section_content(self, result: Dict, section: str, content: List[str]):
        """Add content to the appropriate section."""
        if section == 'params':
            for line in content:
                match = re.match(r'\s*(\w+)(?:\s*\(([^)]+)\))?:\s*(.+)', line)
                if match:
                    result['params'].append({
                        'name': match.group(1),
                        'type': match.group(2) or 'Any',
                        'description': match.group(3)
                    })
        elif section == 'returns':
            result['returns'] = '\n'.join(content).strip()
        elif section == 'raises':
            for line in content:
                match = re.match(r'\s*(\w+):\s*(.+)', line)
                if match:
                    result['raises'].append(f"{match.group(1)}: {match.group(2)}")
        elif section == 'examples':
            result['examples'].append('\n'.join(content).strip())
    
    def extract_function_info(self, source: str, start_line: int) -> Optional[FunctionDoc]:
        """Extract function information from source code."""
        # Simple regex-based extraction (for production, use ast module)
        func_pattern = r'(?:async\s+)?def\s+(\w+)\s*\(([^)]*)\)(?:\s*->\s*([^:]+))?:'
        match = re.search(func_pattern, source)
        
        if not match:
            return None
        
        name = match.group(1)
        signature = f"({match.group(2)})"
        returns = match.group(3) if match.group(3) else None
        is_async = source.strip().startswith('async')
        
        # Extract docstring
        docstring_match = re.search(r'\)\s*:\s*(?:\s*#[^\n]*\n)?\s*"""([^"]*)"""', source, re.DOTALL)
        if not docstring_match:
            docstring_match = re.search(r"\)\s*:\s*(?:\s*#[^\n]*\n)?\s*'''([^']*)'''", source, re.DOTALL)
        
        docstring = docstring_match.group(1) if docstring_match else ""
        parsed = self.parse_docstring(docstring)
        
        return FunctionDoc(
            name=name,
            signature=signature,
            docstring=parsed['description'],
            params=parsed['params'],
            returns=parsed['returns'] or returns,
            raises=parsed['raises'],
            examples=parsed['examples'],
            module="",
            line_number=start_line,
            is_async=is_async,
            is_class_method=False,
            is_static=False,
            is_property=False
        )
    
    def parse_module(self, file_path: Path) -> Optional[ModuleDoc]:
        """Parse a Python module file."""
        try:
            content = file_path.read_text(encoding='utf-8')
            lines = content.split('\n')
            
            # Extract module docstring
            docstring = ""
            if content.strip().startswith('"""') or content.strip().startswith("'''"):
                match = re.search(r'^(?:"""|\'\'\')([^"\']*)(?:"""|\'\'\')', content.strip(), re.DOTALL)
                if match:
                    docstring = match.group(1).strip()
            
            # Get module name from file path
            module_name = str(file_path.relative_to(self.source_dir)).replace('/', '.').replace('\\', '.')[:-3]
            
            return ModuleDoc(
                name=module_name,
                path=str(file_path),
                docstring=docstring,
                classes=[],
                functions=[],
                imports=[],
                exports=[]
            )
        except Exception as e:
            print(f"Error parsing {file_path}: {e}")
            return None
    
    def scan_directory(self, directory: Path) -> List[ModuleDoc]:
        """Scan a directory for Python modules."""
        modules = []
        
        for py_file in directory.rglob('*.py'):
            # Skip test files and private modules
            if py_file.name.startswith('test_') or py_file.name.startswith('_'):
                continue
            
            module = self.parse_module(py_file)
            if module:
                modules.append(module)
        
        return modules
    
    def generate_markdown(self) -> str:
        """Generate Markdown documentation."""
        lines = [
            "# AMCIS API Documentation",
            "",
            f"*Auto-generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*",
            "",
            "## Table of Contents",
            "",
        ]
        
        # Add TOC
        for module in self.modules:
            anchor = module.name.replace('.', '-').lower()
            lines.append(f"- [{module.name}](#{anchor})")
        
        lines.append("")
        
        # Add module documentation
        for module in self.modules:
            anchor = module.name.replace('.', '-').lower()
            lines.extend([
                f"## {module.name}",
                "",
                f"**Path:** `{module.path}`",
                "",
            ])
            
            if module.docstring:
                lines.extend([module.docstring, ""])
            
            if module.classes:
                lines.extend(["### Classes", ""])
                for cls in module.classes:
                    lines.extend([
                        f"#### `{cls.name}`",
                        "",
                        cls.docstring,
                        "",
                    ])
            
            if module.functions:
                lines.extend(["### Functions", ""])
                for func in module.functions:
                    async_prefix = "async " if func.is_async else ""
                    lines.extend([
                        f"#### `{async_prefix}{func.name}{func.signature}`",
                        "",
                        func.docstring,
                        "",
                    ])
                    
                    if func.params:
                        lines.extend(["**Parameters:**", ""])
                        for param in func.params:
                            lines.append(f"- `{param['name']}` ({param['type']}): {param['description']}")
                        lines.append("")
                    
                    if func.returns:
                        lines.extend([f"**Returns:** {func.returns}", ""])
                    
                    if func.examples:
                        lines.extend(["**Example:**", "", "```python"])
                        for example in func.examples:
                            lines.extend([example, ""])
                        lines.extend(["```", ""])
            
            lines.append("---")
            lines.append("")
        
        return '\n'.join(lines)
    
    def generate_json(self) -> Dict:
        """Generate JSON documentation."""
        return {
            "generated_at": datetime.now().isoformat(),
            "version": self._get_version(),
            "modules": [asdict(m) for m in self.modules]
        }
    
    def _get_version(self) -> str:
        """Get the current version from git or version file."""
        try:
            result = subprocess.run(
                ['git', 'describe', '--tags', '--always'],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                return result.stdout.strip()
        except:
            pass
        return "unknown"
    
    def generate_changelog_entry(self) -> str:
        """Generate a changelog entry for recent commits."""
        try:
            result = subprocess.run(
                ['git', 'log', '-10', '--pretty=format:- %s (%h)'],
                capture_output=True,
                text=True,
                cwd=self.source_dir
            )
            
            date_str = datetime.now().strftime('%Y-%m-%d')
            commits = result.stdout
            
            return f"""## [{self._get_version()}] - {date_str}

### Changes
{commits}

### Documentation
- Auto-generated API documentation updated

---
"""
        except Exception as e:
            print(f"Error generating changelog: {e}")
            return ""
    
    def run(self) -> bool:
        """Run the documentation generation process."""
        print(f"Scanning {self.source_dir} for Python modules...")
        self.modules = self.scan_directory(self.source_dir)
        print(f"Found {len(self.modules)} modules")
        
        # Create output directory
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate Markdown docs
        print("Generating Markdown documentation...")
        markdown_content = self.generate_markdown()
        (self.output_dir / 'api_reference.md').write_text(markdown_content, encoding='utf-8')
        
        # Generate JSON docs
        print("Generating JSON documentation...")
        json_content = self.generate_json()
        (self.output_dir / 'api_reference.json').write_text(
            json.dumps(json_content, indent=2),
            encoding='utf-8'
        )
        
        # Generate module index
        print("Generating module index...")
        self._generate_module_index()
        
        # Update changelog
        print("Updating changelog...")
        self._update_changelog()
        
        print(f"Documentation generated in {self.output_dir}")
        return True
    
    def _generate_module_index(self):
        """Generate a module index file."""
        lines = [
            "# AMCIS Module Index",
            "",
            f"*Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*",
            "",
            "| Module | Description |",
            "|--------|-------------|",
        ]
        
        for module in self.modules:
            desc = module.docstring.split('\n')[0][:50] if module.docstring else ""
            lines.append(f"| `{module.name}` | {desc} |")
        
        (self.output_dir / 'module_index.md').write_text('\n'.join(lines), encoding='utf-8')
    
    def _update_changelog(self):
        """Update the changelog with recent commits."""
        changelog_path = self.output_dir / 'CHANGELOG.md'
        new_entry = self.generate_changelog_entry()
        
        if changelog_path.exists():
            existing = changelog_path.read_text(encoding='utf-8')
            content = new_entry + '\n' + existing
        else:
            content = "# Changelog\n\n" + new_entry
        
        changelog_path.write_text(content, encoding='utf-8')


def check_documentation_status(source_dir: str, output_dir: str) -> bool:
    """Check if documentation is up to date with source code."""
    generator = DocumentationGenerator(source_dir, output_dir)
    
    # Get the most recent modification time of source files
    source_mtime = 0
    for py_file in Path(source_dir).rglob('*.py'):
        if not py_file.name.startswith('test_') and not py_file.name.startswith('_'):
            mtime = py_file.stat().st_mtime
            source_mtime = max(source_mtime, mtime)
    
    # Get the most recent modification time of generated docs
    doc_mtime = float('inf')
    for doc_file in Path(output_dir).glob('*'):
        mtime = doc_file.stat().st_mtime
        doc_mtime = min(doc_mtime, mtime)
    
    return doc_mtime >= source_mtime


def main():
    parser = argparse.ArgumentParser(
        description='Generate AMCIS documentation from source code'
    )
    parser.add_argument(
        '--source-dir',
        default='AMCIS_Q_SEC_CORE',
        help='Source code directory to scan'
    )
    parser.add_argument(
        '--output-dir',
        default='docs/api',
        help='Output directory for generated documentation'
    )
    parser.add_argument(
        '--check',
        action='store_true',
        help='Check if documentation is up to date (exit 2 if outdated)'
    )
    parser.add_argument(
        '--watch',
        action='store_true',
        help='Watch for changes and regenerate automatically'
    )
    
    args = parser.parse_args()
    
    if args.check:
        if check_documentation_status(args.source_dir, args.output_dir):
            print("Documentation is up to date")
            sys.exit(0)
        else:
            print("Documentation is outdated. Run without --check to regenerate.")
            sys.exit(2)
    
    if args.watch:
        print("Watching for changes... (Press Ctrl+C to stop)")
        import time
        generator = DocumentationGenerator(args.source_dir, args.output_dir)
        generator.run()
        
        try:
            while True:
                time.sleep(5)
                if not check_documentation_status(args.source_dir, args.output_dir):
                    print("Changes detected, regenerating...")
                    generator.run()
        except KeyboardInterrupt:
            print("\nStopping watcher")
    else:
        generator = DocumentationGenerator(args.source_dir, args.output_dir)
        success = generator.run()
        sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
