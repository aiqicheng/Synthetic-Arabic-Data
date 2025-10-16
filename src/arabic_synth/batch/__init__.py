"""
Batch generation module for Arabic synthetic data generation.

This module provides enhanced batch generation capabilities with parallel processing
using llm-batch-helper for faster generation.
"""

from .enhanced_generator import EnhancedBatchGenerationProgram

__all__ = ["EnhancedBatchGenerationProgram"]
