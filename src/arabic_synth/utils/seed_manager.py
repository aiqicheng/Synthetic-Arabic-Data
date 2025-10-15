from __future__ import annotations

import json
import random, hashlib
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from textwrap import dedent

from arabic_synth.schemas.exams import ExamItem
from arabic_synth.utils.similarity import tokens, jaccard, ngram_jaccard, numeric_overlap, norm_ar, stable_hash



@dataclass
class SeedConstraint:
    max_seeds: int = 10
    min_seed_diversity: float = 0.8  # 种子间相似度阈值
    max_generation_similarity: float = 0.7  # 生成内容与种子的最大相似度
    # extra knobs
    max_token_jaccard: float = 0.35
    max_char5_jaccard: float = 0.30
    max_numeric_overlap: float = 0.6
    rng_seed: Optional[int] = None       # if None, derive deterministically

class SeedManager:
    def __init__(self, constraint: SeedConstraint = SeedConstraint()):
        self.constraint = constraint
        self.seeds: List[Dict[str, Any]] = []
        self.seed_embeddings: List[List[float]] = []

    def _det_rng(self, basis: str) -> random.Random:
        """Deterministic random number generator"""
        if self.constraint.rng_seed is not None:
            return random.Random(self.constraint.rng_seed)
        h = int(hashlib.md5(basis.encode("utf-8")).hexdigest(), 16) % (2**31-1)
        return random.Random(h)

    def _greedy_diverse_pick(self, candidates: List[Dict[str,Any]], k: int) -> List[Dict[str,Any]]:
        """Greedy diverse pick from candidates"""
        sel = []
        for cand in candidates:
            ok = True
            for s in sel:
                sim = self._qa_similarity_quick(s, cand)
                if 1.0 - sim < self.constraint.min_seed_diversity:
                    ok = False; break
            if ok: sel.append(cand)
            if len(sel) >= k: break

        # fallback: relax by 0.05 until filled or exhausted
        relax = 0.05
        thr = self.constraint.min_seed_diversity
        i = 0
        while len(sel) < k and thr > 0 and i < len(candidates):
            cand = candidates[i]; i += 1
            if cand in sel: continue
            if all(1.0 - self._qa_similarity_quick(s, cand) >= thr - relax for s in sel):
                sel.append(cand)
            if i == len(candidates) and len(sel) < k:
                i = 0; thr -= relax  # another pass with looser threshold
        return sel[:k]

    def _qa_similarity_quick(self, a: Dict[str,Any], b: Dict[str,Any]) -> float:
        """Quick QA similarity calculation"""
        def _text(x):
            q = x.get('question','') or ''
            opts = x.get('options', []) or []
            opts = ' '.join(map(str, opts))
            return norm_ar(f"{q} || {opts}")
        qa1, qa2 = _text(a), _text(b)
        # use max of token and char-5 Jaccard as a conservative bound
        return max(jaccard(tokens(qa1), tokens(qa2)), ngram_jaccard(qa1, qa2, 5))


    def load_seeds_from_testset(self, testset_path: Path, task: str) -> List[Dict[str, Any]]:
        if not testset_path.exists(): return []
        with testset_path.open('r', encoding='utf-8') as f:
            test_data = [json.loads(line) for line in f if line.strip()]

        # light format check
        test_data = [s for s in test_data if isinstance(s, dict) and s.get("question") and isinstance(s.get("options"), list) and len(s["options"])>=3]

        k = min(self.constraint.max_seeds, len(test_data))
        rng = self._det_rng(f"{task}|{str(testset_path)}|{k}|{self.constraint}")
        rng.shuffle(test_data)
        picked = self._greedy_diverse_pick(test_data, k)
        self.seeds = picked
        return picked
    def load_seeds_from_jsonl(self, jsonl_path: Path, task: str) -> List[Dict[str, Any]]:
        if not jsonl_path.exists(): return []            
        with jsonl_path.open('r', encoding='utf-8') as f:
            seeds_data = [json.loads(line) for line in f if line.strip()]
        # light format check
        seeds_data = [s for s in seeds_data if isinstance(s, dict) and s.get("question") and isinstance(s.get("options"), list) and len(s["options"])>=3]
        k = min(self.constraint.max_seeds, len(seeds_data))
        rng = self._det_rng(f"{task}|{str(jsonl_path)}|{k}|{self.constraint}")
        rng.shuffle(seeds_data)
        picked = self._greedy_diverse_pick(seeds_data, k)
        self.seeds = picked
        return picked

    '''# deprecated
    def load_seeds_from_testset(self, testset_path: Path, task: str) -> List[Dict[str, Any]]:
        """从测试集加载种子数据，确保不超过最大数量"""
        if not testset_path.exists():
            return []
            
        # 读取测试集
        with testset_path.open('r', encoding='utf-8') as f:
            test_data = [json.loads(line) for line in f if line.strip()]
        
        # 随机选择少量样本作为种子
        max_seeds = min(self.constraint.max_seeds, len(test_data))
        selected_seeds = random.sample(test_data, max_seeds)
        
        # 验证种子数据格式
        validated_seeds = []
        for seed in selected_seeds:
            try:
                if task == "exams" or task == "mmlu":
                    # Check for required fields without strict schema validation
                    # since seeds might have different format than generated items
                    if ("question" in seed and seed["question"] and 
                        "options" in seed and isinstance(seed["options"], list) and len(seed["options"]) >= 3):
                        validated_seeds.append(seed)
            except Exception:
                continue
                
        self.seeds = validated_seeds
        return validated_seeds
    
    def load_seeds_from_jsonl(self, jsonl_path: Path, task: str) -> List[Dict[str, Any]]:
        """从JSONL文件加载种子数据"""
        if not jsonl_path.exists():
            return []
            
        # 读取JSONL文件
        with jsonl_path.open('r', encoding='utf-8') as f:
            seeds_data = [json.loads(line) for line in f if line.strip()]
        
        # 限制种子数量
        max_seeds = min(self.constraint.max_seeds, len(seeds_data))
        selected_seeds = seeds_data[:max_seeds]  # 使用前N个种子
        
        # 验证种子数据格式
        validated_seeds = []
        for seed in selected_seeds:
            try:
                if task == "exams":
                    # Check for required fields
                    if ("question" in seed and seed["question"] and 
                        "options" in seed and isinstance(seed["options"], list) and len(seed["options"]) >= 3):
                        validated_seeds.append(seed)
            except Exception:
                continue
                
        self.seeds = validated_seeds
        return validated_seeds
    
    def validate_generation(self, generated_item: Dict[str, Any], task: str) -> bool:
        """验证生成的内容是否与种子过于相似"""
        if not self.seeds:
            return True
            
        # 简单的相似度检查（可以扩展为更复杂的语义相似度）
        for seed in self.seeds:
            similarity = self._calculate_similarity(generated_item, seed, task)
            if similarity > self.constraint.max_generation_similarity:
                return False
        return True
    
    def _calculate_similarity(self, item1: Dict[str, Any], item2: Dict[str, Any], task: str) -> float:
        """计算两个项目的相似度"""
        if task == "exams":
            # 检查问题相似度
            q1 = item1.get("question", "")
            q2 = item2.get("question", "")
            
            # 简单的词汇重叠检查
            words1 = set(q1.split())
            words2 = set(q2.split())
            
            if len(words1) == 0 or len(words2) == 0:
                return 0.0
                
            overlap = len(words1.intersection(words2))
            total = len(words1.union(words2))
            
            return overlap / total if total > 0 else 0.0
        
        elif task == "mmlu":
            # Check question similarity for MMLU
            q1 = item1.get("question", "")
            q2 = item2.get("question", "")
            
            # Simple word overlap check
            words1 = set(q1.split())
            words2 = set(q2.split())
            
            if len(words1) == 0 or len(words2) == 0:
                return 0.0
                
            overlap = len(words1.intersection(words2))
            total = len(words1.union(words2))
            
            return overlap / total if total > 0 else 0.0
        
        return 0.0    
    '''

    def get_style_guidance(self, task: str) -> str:
        """获取风格指导，不包含具体内容"""
        if not self.seeds:
            return ""
            
        if task == "exams":
            # 分析种子数据的风格特征
            subjects = set()
            question_lengths = []
            option_patterns = set()
            
            for seed in self.seeds:
                # 提取主题（从问题中识别）
                question = seed.get("question", "")
                if "تاريخ" in question or "تاريخية" in question:
                    subjects.add("history")
                elif "جغرافيا" in question or "جغرافية" in question:
                    subjects.add("geography")
                elif "علوم" in question or "علمية" in question:
                    subjects.add("science")
                elif "أدب" in question or "شعر" in question:
                    subjects.add("literature")
                else:
                    subjects.add("general")
                
                # 统计问题长度
                question_lengths.append(len(question.split()))
                
                # 分析选项模式
                options = seed.get("options", [])
                for opt in options:
                    if opt.startswith("A."):
                        option_patterns.add("letter_dot")
                    elif opt.startswith("A-"):
                        option_patterns.add("letter_dash")
            
            # 生成风格指导
            avg_length = sum(question_lengths) / len(question_lengths) if question_lengths else 15
            subject_list = list(subjects)[:3]  # 限制主题数量
            
            guidance = dedent(f"""
                        [Style Guide based on {len(self.seeds)} seed examples]
                        - Question length: {int(avg_length)} ± 5 words
                        - Subjects to cover: {', '.join(subject_list)}
                        - Option format: Use {list(option_patterns)[0] if option_patterns else 'A. B. C. D.'} format
                        - Maintain similar complexity level as seed examples
                        - DO NOT copy any specific content from seeds
                        """).strip()
            return guidance
        
        elif task == "mmlu":
            # Analyze MMLU seed data for style guidance
            subjects = set()
            question_lengths = []
            option_patterns = set()
            technical_terms = set()
            
            for seed in self.seeds:
                # Extract subject from seed data
                if "subject" in seed:
                    subjects.add(seed["subject"])
                
                # Extract level information
                level = seed.get("level", "")
                
                # Analyze question content
                question = seed.get("question", "")
                question_lengths.append(len(question.split()))
                
                # Look for technical terms (simple heuristic)
                tech_words = ["خوارزمية", "برمجة", "بيانات", "شبكة", "ذكاء", "نظام", "حاسوب", "برنامج"]
                for word in tech_words:
                    if word in question:
                        technical_terms.add(word)
                
                # Analyze option patterns
                options = seed.get("options", [])
                for opt in options:
                    if opt.startswith("A."):
                        option_patterns.add("letter_dot")
                    elif opt.startswith("A-"):
                        option_patterns.add("letter_dash")
            
            # Generate MMLU-specific style guidance
            avg_length = sum(question_lengths) / len(question_lengths) if question_lengths else 15
            subject_list = list(subjects) if subjects else ["Mathematics"]
            
            guidance = dedent(f"""
                        [MMLU Style Guide based on {len(self.seeds)} seed examples]
                        - Subject focus: {', '.join(subject_list)}
                        - Question length: {int(avg_length)} ± 5 words
                        - Technical depth: Maintain academic rigor for {level} level
                        - Option format: Use {list(option_patterns)[0] if option_patterns else 'A. B. C. D.'} format
                        - Include technical terminology: {', '.join(list(technical_terms)[:3]) if technical_terms else 'Use domain-specific terms'}
                        - Maintain MMLU assessment standards
                        - DO NOT copy any specific content from seeds
                        """).strip()
            return guidance
        
        return ""
    
    def validate_generation(self, generated_item: Dict[str, Any], task: str) -> bool:
        if not self.seeds: return True
        q = generated_item.get("question","")
        opts = " ".join(map(str, generated_item.get("options", []) or []))
        text = norm_ar(f"{q} || {opts}")

        for seed in self.seeds:
            base_q = seed.get('question','') or ''
            base_opts = " ".join(map(str, seed.get('options', []) or []))
            base = norm_ar(f"{base_q} || {base_opts}")

            if jaccard(tokens(text), tokens(base)) > self.constraint.max_token_jaccard: return False
            if ngram_jaccard(text, base, 5)   > self.constraint.max_char5_jaccard:    return False
            if numeric_overlap(text, base)    > self.constraint.max_numeric_overlap:  return False

        return True



    def _extract_subject_hint(self, seed: Dict[str, Any]) -> str:
        """Extract subject hint from seed data, using actual subject field if available."""
        # First try to use the actual subject field from the seed
        if "subject" in seed and seed["subject"]:
            return seed["subject"]
        
        # Fallback to keyword-based heuristic if subject field is not available
        question = seed.get("question", "")
        q = (question or "").lower()
        # 关键词映射（可按需扩展）
        keyword_to_subject = [
            ("فيزياء", "physics"),
            ("كهرباء", "physics"),
            ("طاقة", "physics"),
            ("أحياء", "biology"),
            ("خلية", "biology"),
            ("كروموسوم", "biology"),
            ("علوم", "science"),
            ("تجربة", "science"),
            ("دين", "islamic"),
            ("القرآن", "islamic"),
            ("حديث", "islamic"),
            ("تاريخ", "history"),
            ("جغراف", "geography"),
            ("مجتمع", "social"),
            ("اقتصاد", "social"),
        ]
        for kw, subj in keyword_to_subject:
            if kw in q:
                return subj
        return "general"
    
    def export_seed_info(self, output_path: Path):
        """导出种子信息用于审计"""
        info = {
            "seed_count": len(self.seeds),
            # "constraints": {
            #     "max_seeds": self.constraint.max_seeds,
            #     "min_seed_diversity": self.constraint.min_seed_diversity,
            #     "max_generation_similarity": self.constraint.max_generation_similarity
            # },
            "constraints": {k: getattr(self.constraint, k) for k in vars(self.constraint)},

            "seeds_used": [
                {
                    "question_preview": (seed.get("question", "")[:80] + "...") if seed.get("question") else "",
                    "subject_hint": self._extract_subject_hint(seed),
                    "hash": stable_hash(seed)
                }
                for seed in self.seeds
            ]
        }
        
        with output_path.open('w', encoding='utf-8') as f:
            json.dump(info, f, ensure_ascii=False, indent=2) 