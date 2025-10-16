"""
Diversity utilities for reducing content duplication in generation.

This module implements fast duplicate detection and diversity techniques for the generation pipeline:
- FastScreen: SimHash-based duplicate detection
- NgramBloom: Bloom filter for n-gram overlap detection  
- DiversityManager: Orchestrates all diversity features
- SamplingJitter: Configuration for parameter variation

Dependencies:
- Uses similarity.py for Arabic text normalization and n-gram processing
- Designed for integration with the generation pipeline in generators/run.py
"""
import re
import hashlib
import random
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

# Import Arabic normalization and n-gram functions from similarity module
from arabic_synth.utils.similarity import norm_ar, char_ngrams


def _tokens(s: str) -> List[str]:
    """Extract tokens from text for hashing with proper Arabic normalization."""
    # Use the better Arabic normalization from similarity.py
    normalized = norm_ar(s.lower())
    # Split on whitespace to get tokens
    return [w for w in normalized.split() if w]


def simhash(s: str, bits: int = 64) -> int:
    """Generate SimHash for text content."""
    v = [0] * bits
    for w in _tokens(s):
        h = int(hashlib.md5(w.encode()).hexdigest(), 16)
        for i in range(bits):
            v[i] += 1 if (h >> i) & 1 else -1
    
    x = 0
    for i in range(bits):
        if v[i] > 0:
            x |= (1 << i)
    return x


def hamdist(a: int, b: int) -> int:
    """Calculate Hamming distance between two integers."""
    return (a ^ b).bit_count()


class FastScreen:
    """Fast duplicate detection using SimHash."""
    
    def __init__(self, bits: int = 64, max_hd: int = 2):
        self.bits = bits
        self.max_hd = max_hd
        self.hexes: List[int] = []  # store small list; cheap linear scan
    
    def accept(self, text: str) -> bool:
        """Check if text is sufficiently different from previous texts."""
        h = simhash(text, self.bits)
        for prev in self.hexes:
            if hamdist(h, prev) <= self.max_hd:
                return False
        self.hexes.append(h)
        return True


class NgramBloom:
    """5-gram Bloom filter for even cheaper duplicate detection."""
    
    def __init__(self, m: int = 1 << 20, k: int = 3, n: int = 5):
        self.m = m
        self.k = k
        self.n = n
        self.bits = bytearray(m // 8)
    
    def _hashes(self, g: str):
        """Generate k hash values for n-gram."""
        b = g.encode()
        h1 = int(hashlib.md5(b).hexdigest(), 16)
        h2 = int(hashlib.sha1(b).hexdigest(), 16)
        for i in range(self.k):
            yield (h1 + i * h2) & (self.m - 1)
    
    def seen_or_add(self, text: str) -> bool:
        """Check if text likely overlaps with previous texts."""
        # Use the better n-gram function from similarity.py
        ngram_counter = char_ngrams(text, self.n)
        hit = False
        
        for ngram in ngram_counter.keys():
            for h in self._hashes(ngram):
                byte, bit = divmod(h, 8)
                mask = 1 << bit
                if not (self.bits[byte] & mask):
                    self.bits[byte] |= mask
                else:
                    hit = True
        return hit  # True => likely overlap


@dataclass
class SamplingJitter:
    """Configuration for sampling jitter."""
    base_temp: float = 0.95
    temp_jitter: float = 0.2
    base_top_p: float = 0.92
    presence_penalty: float = 0.4
    frequency_penalty: float = 0.4


class DiversityManager:
    """Manages all diversity techniques for generation."""
    
    def __init__(self, use_simhash: bool = True, use_bloom: bool = False, 
                 jitter_config: Optional[SamplingJitter] = None):
        self.jitter_config = jitter_config or SamplingJitter()
        self.screen = FastScreen(max_hd=3) if use_simhash else None
        self.bloom = NgramBloom() if use_bloom else None
        
        # Prompt variations for micro-variation
        self.prompt_variations = [
            "explain", "describe", "analyze", "evaluate", "discuss"
        ]
        self.option_formats = [
            "A)", "B)", "C)", "D)",
            "A.", "B.", "C.", "D.",
            "(A)", "(B)", "(C)", "(D)"
        ]
        self.context_phrases = [
            "Vary entities, years, and contexts across items in this batch.",
            "Use diverse examples, scenarios, and contexts for each question.",
            "Ensure each question covers different aspects and contexts.",
        ]
    
    def get_jittered_params(self) -> Dict[str, Any]:
        """Generate jittered sampling parameters."""
        temp_jitter = random.uniform(-self.jitter_config.temp_jitter/2, 
                                   self.jitter_config.temp_jitter/2)
        temperature = max(0.1, min(1.0, self.jitter_config.base_temp + temp_jitter))
        
        return {
            "temperature": temperature,
            "top_p": self.jitter_config.base_top_p,
            "presence_penalty": self.jitter_config.presence_penalty,
            "frequency_penalty": self.jitter_config.frequency_penalty
        }
    
    def get_varied_prompt(self, base_prompt: str, item_index: int) -> str:
        """Add micro-variations to prompt."""
        # Rotate through variations
        verb = self.prompt_variations[item_index % len(self.prompt_variations)]
        context_phrase = self.context_phrases[item_index % len(self.context_phrases)]
        
        # Replace common instruction words
        varied_prompt = base_prompt.replace("explain", verb, 1)
        varied_prompt = varied_prompt.replace("describe", verb, 1)
        varied_prompt = varied_prompt.replace("analyze", verb, 1)
        
        # Add context variation instruction
        if "Vary entities" not in varied_prompt:
            varied_prompt += f"\n\n**Important**: {context_phrase}"
        
        return varied_prompt
    
    def check_duplicate(self, item: Dict[str, Any]) -> bool:
        """Check if item is likely a duplicate using fast screening."""
        # Create text representation for screening
        question = item.get("question", "")
        options = item.get("options", [])
        text = f"{question} || {' '.join(map(str, options))}"
        
        # Use SimHash first (more accurate)
        if self.screen and not self.screen.accept(text):
            return True
            
        # Use Bloom filter as backup (cheaper)
        if self.bloom and self.bloom.seen_or_add(text):
            return True
            
        return False
    
    def should_retry_with_boost(self, item: Dict[str, Any]) -> bool:
        """Determine if we should retry generation with temperature boost."""
        return self.check_duplicate(item)


def create_diversity_manager(use_simhash: bool = True, use_bloom: bool = False) -> DiversityManager:
    """Factory function to create a diversity manager."""
    jitter_config = SamplingJitter(
        base_temp=0.95,
        temp_jitter=0.2,
        base_top_p=0.92,
        presence_penalty=0.4,
        frequency_penalty=0.4
    )
    return DiversityManager(use_simhash=use_simhash, use_bloom=use_bloom, jitter_config=jitter_config)
