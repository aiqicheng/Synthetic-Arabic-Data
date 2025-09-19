from __future__ import annotations

import json
import random
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from arabic_synth.schemas.exams import ExamItem


@dataclass
class SeedConstraint:
    max_seeds: int = 10
    min_seed_diversity: float = 0.8  # 种子间相似度阈值
    max_generation_similarity: float = 0.7  # 生成内容与种子的最大相似度


class SeedManager:
    def __init__(self, constraint: SeedConstraint = SeedConstraint()):
        self.constraint = constraint
        self.seeds: List[Dict[str, Any]] = []
        self.seed_embeddings: List[List[float]] = []
        
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
                if task == "exams":
                    # Check for required fields without strict schema validation
                    # since seeds might have different format than generated items
                    if ("question" in seed and seed["question"] and 
                        "options" in seed and isinstance(seed["options"], list) and len(seed["options"]) >= 3):
                        validated_seeds.append(seed)
            except Exception:
                continue
                
        self.seeds = validated_seeds
        return validated_seeds
    
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
            
            guidance = f"""
[Style Guide based on {len(self.seeds)} seed examples]
- Question length: {int(avg_length)} ± 5 words
- Subjects to cover: {', '.join(subject_list)}
- Option format: Use {list(option_patterns)[0] if option_patterns else 'A. B. C. D.'} format
- Maintain similar complexity level as seed examples
- DO NOT copy any specific content from seeds
"""
            return guidance
        
        return ""
    
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
        
        return 0.0

    def _extract_subject_hint(self, question: str) -> str:
        """基于问题文本的简单启发式主题识别，仅用于审计展示。"""
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
            "constraints": {
                "max_seeds": self.constraint.max_seeds,
                "min_seed_diversity": self.constraint.min_seed_diversity,
                "max_generation_similarity": self.constraint.max_generation_similarity
            },
            "seeds_used": [
                {
                    "question_preview": seed.get("question", "")[:50] + "...",
                    "subject_hint": self._extract_subject_hint(seed.get("question", "")),
                    "hash": hash(json.dumps(seed, sort_keys=True))
                }
                for seed in self.seeds
            ]
        }
        
        with output_path.open('w', encoding='utf-8') as f:
            json.dump(info, f, ensure_ascii=False, indent=2) 