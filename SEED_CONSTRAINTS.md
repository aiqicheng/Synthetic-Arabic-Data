# 种子约束系统 (Seed Constraint System)

## 概述

种子约束系统确保在生成合成数据时，只使用少量测试集样本（≤10条）作为风格指导，避免过度依赖测试集导致评估系统欺骗。

## 核心特性

### 🔒 约束机制
- **最大种子数量**: 默认 ≤10 条
- **相似度检查**: 生成内容与种子的最大相似度 ≤0.7
- **多样性要求**: 种子间最小多样性 ≥0.8

### 🌱 风格指导
- 分析种子数据的主题分布
- 提取问题长度、选项格式等风格特征
- 生成风格指导，不包含具体内容

### 📊 审计追踪
- 记录使用的种子信息
- 导出约束设置和种子哈希
- 便于验证和复现

## 使用方法

### 1. 准备种子数据

将你的测试集样本（≤10条）保存为 JSONL 格式：

```jsonl
{"question": "ما هي عاصمة المملكة العربية السعودية؟", "options": ["A. الرياض", "B. جدة", "C. مكة", "D. الدمام"], "answer": "A"}
{"question": "في أي عام تأسست المملكة العربية السعودية الحديثة؟", "options": ["A. 1902", "B. 1932", "C. 1945", "D. 1950"], "answer": "B"}
```

### 2. 使用 CLI 生成

```bash
# 使用种子约束生成
arabic-synth generate exams \
  --num-samples 100 \
  --model openai:gpt-4o \
  --seed-file data/seeds/exams_seeds.jsonl \
  --out-dir outputs
```

### 3. 使用 Python 脚本

```python
from arabic_synth.utils.seed_manager import SeedConstraint
from arabic_synth.generators.run import run_generation

# 配置约束
constraint = SeedConstraint(
    max_seeds=10,
    max_generation_similarity=0.7
)

# 生成数据
results = run_generation(
    task="exams",
    num_samples=1000,
    model="openai:gpt-4o",
    seed_path=Path("data/seeds/exams_seeds.jsonl"),
    seed_constraint=constraint
)
```

## 约束配置

### SeedConstraint 参数

```python
@dataclass
class SeedConstraint:
    max_seeds: int = 10                    # 最大种子数量
    min_seed_diversity: float = 0.8        # 种子间最小多样性
    max_generation_similarity: float = 0.7 # 生成内容与种子的最大相似度
```

### 相似度计算

- **词汇重叠**: 基于问题词汇的 Jaccard 相似度
- **阈值控制**: 可调整相似度阈值
- **自动拒绝**: 超过阈值的生成内容会被拒绝

## 输出文件

### 生成的数据
- `outputs/exams_seeded_1000.jsonl`: 生成的 MCQ 数据

### 审计信息
- `outputs/exams_seeds_audit.json`: 种子使用审计
  ```json
  {
    "seed_count": 5,
    "constraints": {
      "max_seeds": 10,
      "max_generation_similarity": 0.7
    },
    "seeds_used": [
      {
        "question_preview": "ما هي عاصمة المملكة العربية السعودية؟...",
        "subject_hint": "geography",
        "hash": 123456789
      }
    ]
  }
  ```

## 扩展到 10,000 样本

### 分阶段生成
```bash
# 阶段 1: 测试 (100 样本)
arabic-synth generate exams --num-samples 100 --seed-file seeds.jsonl

# 阶段 2: 小规模 (1,000 样本)
arabic-synth generate exams --num-samples 1000 --seed-file seeds.jsonl

# 阶段 3: 大规模 (10,000 样本)
arabic-synth generate exams --num-samples 10000 --seed-file seeds.jsonl
```

### 质量控制
- 每阶段检查生成质量
- 调整相似度阈值
- 验证主题分布平衡

## 最佳实践

### ✅ 推荐做法
- 使用 ≤10 个多样化的种子样本
- 定期检查审计信息
- 调整相似度阈值平衡质量和多样性

### ❌ 避免做法
- 使用过多种子（>10）
- 设置过低的相似度阈值
- 忽略审计信息

## 故障排除

### 常见问题

1. **生成失败率高**
   - 检查相似度阈值是否过低
   - 增加种子多样性

2. **风格不一致**
   - 检查种子数据质量
   - 调整风格指导参数

3. **主题分布不均**
   - 优化种子选择
   - 调整生成提示

## 扩展功能

### 未来改进
- 语义相似度检查
- 动态约束调整
- 多任务种子管理
- 自动种子选择 