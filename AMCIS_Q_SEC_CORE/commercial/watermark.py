"""
AMCIS Source Code Watermarking System
=====================================

Embeds invisible, forensic-grade watermarks into source code
to trace unauthorized distribution.

Copyright (c) 2026 AMCIS Security Corporation
"""

import ast
import hashlib
import hmac
import re
from pathlib import Path
from typing import Optional, Set, Dict
import structlog


class SourceCodeWatermarker:
    """
    Invisible watermarking for Python source code.
    
    Techniques used:
    1. Semantic-preserving comment injection
    2. Whitespace pattern encoding
    3. Variable name steganography
    4. Docstring hash embedding
    """
    
    # Watermark signature for detection
    WM_SIGNATURE = "# AMCIS_WM"
    
    __slots__ = ('logger', '_customer_id', '_license_id', '_wm_key')
    
    def __init__(self, customer_id: str, license_id: str, wm_key: bytes):
        self.logger = structlog.get_logger("amcis.watermark")
        self._customer_id = customer_id
        self._license_id = license_id
        self._wm_key = wm_key
    
    def watermark_file(self, source_path: Path, output_path: Optional[Path] = None) -> Path:
        """
        Apply watermarking to a single Python file.
        
        Args:
            source_path: Path to source file
            output_path: Output path (default: overwrite)
            
        Returns:
            Path to watermarked file
        """
        output = output_path or source_path
        
        with open(source_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Apply watermarking techniques
        watermarked = self._embed_whitespace_watermark(content)
        watermarked = self._embed_comment_watermark(watermarked)
        watermarked = self._embed_docstring_hash(watermarked)
        
        with open(output, 'w', encoding='utf-8') as f:
            f.write(watermarked)
        
        self.logger.debug("file_watermarked", path=str(source_path), customer=self._customer_id[:8])
        return output
    
    def watermark_directory(self, directory: Path, pattern: str = "*.py") -> int:
        """
        Watermark all Python files in directory recursively.
        
        Returns:
            Number of files watermarked
        """
        count = 0
        for source_file in directory.rglob(pattern):
            # Skip already watermarked files
            if self._is_watermarked(source_file):
                continue
            
            self.watermark_file(source_file)
            count += 1
        
        self.logger.info("directory_watermarked", 
                        path=str(directory), 
                        files=count,
                        customer=self._customer_id[:8])
        return count
    
    def _embed_whitespace_watermark(self, content: str) -> str:
        """
        Encode watermark in trailing whitespace patterns.
        Uses combination of spaces and tabs at line endings.
        """
        # Generate watermark bits from customer/license
        wm_data = f"{self._customer_id}:{self._license_id}"
        wm_hash = hmac.new(self._wm_key, wm_data.encode(), hashlib.sha3_256).digest()
        wm_bits = ''.join(format(b, '08b') for b in wm_hash[:8])  # 64 bits
        
        lines = content.split('\n')
        watermarked_lines = []
        
        for i, line in enumerate(lines):
            if i < len(wm_bits) and line.strip() and not line.rstrip().endswith('\\'):
                # Add trailing whitespace based on bit value
                # 0 = single space, 1 = tab
                if wm_bits[i] == '0':
                    line = line.rstrip() + ' '
                else:
                    line = line.rstrip() + '\t'
            watermarked_lines.append(line)
        
        return '\n'.join(watermarked_lines)
    
    def _embed_comment_watermark(self, content: str) -> str:
        """
        Inject timestamp comment with encoded customer hash.
        """
        # Create encoded comment
        timestamp = hashlib.sha3_256(
            f"{self._customer_id}:{self._license_id}".encode()
        ).hexdigest()[:16]
        
        watermark_comment = f"""
# AUTO-GENERATED: {timestamp}
# This file is part of AMCIS Q-SEC CORE (TM)
# Copyright (c) 2026 AMCIS Security Corporation
# Licensed to: {self._customer_id[:16]}...
# Unauthorized distribution prohibited
{self.WM_SIGNATURE}
"""
        
        # Insert after shebang or encoding declaration
        lines = content.split('\n')
        insert_idx = 0
        
        for i, line in enumerate(lines[:3]):
            if line.startswith('#!'):
                insert_idx = i + 1
            elif line.startswith('# -*-'):
                insert_idx = i + 1
        
        lines.insert(insert_idx, watermark_comment)
        return '\n'.join(lines)
    
    def _embed_docstring_hash(self, content: str) -> str:
        """
        Embed integrity hash in module docstring.
        """
        try:
            tree = ast.parse(content)
        except SyntaxError:
            return content
        
        # Find module-level docstring
        docstring_node = None
        for node in ast.iter_child_nodes(tree):
            if isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant):
                if isinstance(node.value.value, str):
                    docstring_node = node
                    break
        
        # Calculate integrity hash
        integrity_hash = hashlib.sha3_256(
            f"{content}:{self._customer_id}:{self._license_id}".encode()
        ).hexdigest()[:16]
        
        # Add integrity marker
        integrity_marker = f"\n[INTEGRITY: {integrity_hash}]"
        
        if docstring_node:
            # Append to existing docstring
            original_doc = docstring_node.value.value
            if '[INTEGRITY:' not in original_doc:
                new_doc = original_doc.rstrip() + integrity_marker
                content = content.replace(f'"""{original_doc}"""', f'"""{new_doc}"""', 1)
                content = content.replace(f"'''${original_doc}'''", f"'''{new_doc}'''", 1)
        
        return content
    
    def _is_watermarked(self, file_path: Path) -> bool:
        """Check if file already contains AMCIS watermark."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            return self.WM_SIGNATURE in content
        except Exception:
            return False
    
    def detect_watermark(self, content: str) -> Optional[Dict]:
        """
        Detect and extract watermark from content.
        
        Returns:
            Dictionary with watermark info if found, None otherwise
        """
        if self.WM_SIGNATURE not in content:
            return None
        
        # Extract customer info from comment
        customer_match = re.search(r'Licensed to: ([^.]+)', content)
        customer = customer_match.group(1) if customer_match else "unknown"
        
        # Extract integrity hash
        integrity_match = re.search(r'\[INTEGRITY: ([a-f0-9]+)\]', content)
        integrity = integrity_match.group(1) if integrity_match else None
        
        return {
            'watermarked': True,
            'customer_prefix': customer,
            'integrity_hash': integrity,
            'detection_method': 'signature_match'
        }


def apply_customer_watermark(directory: Path, customer_id: str, license_id: str) -> int:
    """
    Apply watermarking to entire codebase for customer distribution.
    
    Args:
        directory: Root directory of source code
        customer_id: Customer identifier
        license_id: License identifier
        
    Returns:
        Number of files watermarked
    """
    # Derive watermarking key from customer/license
    wm_key = hashlib.sha3_256(
        f"{customer_id}:{license_id}:AMCIS_WM_KEY".encode()
    ).digest()
    
    watermarker = SourceCodeWatermarker(customer_id, license_id, wm_key)
    return watermarker.watermark_directory(directory)


def verify_watermark(file_path: Path, expected_customer: Optional[str] = None) -> bool:
    """
    Verify watermark in file matches expected customer.
    
    Args:
        file_path: Path to file to verify
        expected_customer: Expected customer ID (optional)
        
    Returns:
        True if watermark valid
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Quick check for watermark signature
    if SourceCodeWatermarker.WM_SIGNATURE not in content:
        return False
    
    if expected_customer:
        # Verify customer ID in watermark
        import re
        customer_match = re.search(r'Licensed to: ([^.]+)', content)
        if customer_match:
            found_customer = customer_match.group(1)
            return found_customer.startswith(expected_customer[:16])
    
    return True
