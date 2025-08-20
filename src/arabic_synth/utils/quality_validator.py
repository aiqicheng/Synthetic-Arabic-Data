from typing import List, Dict, Tuple
from sklearn.metrics import accuracy_score
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
import numpy as np

class QualityValidator:
    def _extract_text(self, item: Dict) -> str:
        return str(item.get('text') or item.get('question') or '')

    def _tokenize(self, text: str) -> List[str]:
        return [t for t in str(text).strip().split() if t]

    def _answer_label(self, item: Dict) -> str:
        ans = str(item.get('answer') or '').strip()
        return ans if ans in {'A', 'B', 'C', 'D'} else ''

    def _length_stats(self, items: List[Dict]) -> Tuple[float, float]:
        lengths = [len(self._tokenize(self._extract_text(it))) for it in items]
        if not lengths:
            return 0.0, 0.0
        return float(np.mean(lengths)), float(np.std(lengths))

    def _answer_distribution(self, items: List[Dict]) -> Dict[str, float]:
        labels = [self._answer_label(it) for it in items if self._answer_label(it)]
        total = max(1, len(labels))
        counts = {k: 0 for k in ['A', 'B', 'C', 'D']}
        for l in labels:
            counts[l] += 1
        return {k: v / total for k, v in counts.items()}

    def _l1_dist(self, p: Dict[str, float], q: Dict[str, float]) -> float:
        keys = set(p.keys()) | set(q.keys())
        return float(sum(abs(p.get(k, 0.0) - q.get(k, 0.0)) for k in keys))

    def _vocab_set(self, items: List[Dict]) -> set:
        vocab = set()
        for it in items:
            vocab.update(self._tokenize(self._extract_text(it)))
        return vocab

    def _ttr(self, items: List[Dict]) -> float:
        tokens = []
        for it in items:
            tokens.extend(self._tokenize(self._extract_text(it)))
        if not tokens:
            return 0.0
        return float(len(set(tokens)) / len(tokens))

    def fidelity_check(self, synthetic: List[Dict], real: List[Dict]) -> Dict:
        """Compare length stats, answer balance, vocabulary diversity and overlap."""
        # Length stats
        syn_mean, syn_std = self._length_stats(synthetic)
        real_mean, real_std = self._length_stats(real)
        length_stats = {
            'synthetic_mean_len': round(syn_mean, 2),
            'synthetic_std_len': round(syn_std, 2),
            'real_mean_len': round(real_mean, 2),
            'real_std_len': round(real_std, 2),
            'mean_len_abs_diff': round(abs(syn_mean - real_mean), 2),
        }

        # Answer balance (EXAMS)
        syn_ans = self._answer_distribution(synthetic)
        real_ans = self._answer_distribution(real)
        answer_balance = {
            'synthetic': syn_ans,
            'real': real_ans,
            'l1_distance': round(self._l1_dist(syn_ans, real_ans), 3),
        }

        # Vocabulary diversity and overlap
        syn_ttr = self._ttr(synthetic)
        real_ttr = self._ttr(real)
        syn_vocab = self._vocab_set(synthetic)
        real_vocab = self._vocab_set(real)
        inter = len(syn_vocab & real_vocab)
        union = max(1, len(syn_vocab | real_vocab))
        vocab = {
            'synthetic_ttr': round(syn_ttr, 3),
            'real_ttr': round(real_ttr, 3),
            'vocab_jaccard': round(inter / union, 3),
            'synthetic_vocab_size': len(syn_vocab),
            'real_vocab_size': len(real_vocab),
        }

        return {
            'length': length_stats,
            'answer_balance': answer_balance,
            'vocabulary': vocab,
        }

    def utility_check(self, synthetic: List[Dict], real: List[Dict]) -> Dict:
        """TSTR: train simple text->answer classifier on synthetic, test on real."""
        # Build train data
        X_train = [self._extract_text(it) for it in synthetic if self._answer_label(it)]
        y_train = [self._answer_label(it) for it in synthetic if self._answer_label(it)]
        X_test = [self._extract_text(it) for it in real if self._answer_label(it)]
        y_test = [self._answer_label(it) for it in real if self._answer_label(it)]

        # Guardrails
        if len(set(y_train)) < 2 or len(X_train) < 10 or len(set(y_test)) < 2 or len(X_test) < 5:
            return {
                'synthetic_to_real_accuracy': None,
                'note': 'Insufficient label variety or sample size for reliable TSTR (need >=2 classes and enough samples).',
            }

        clf = Pipeline([
            ('vec', CountVectorizer(max_features=5000, ngram_range=(1, 2))),
            ('lr', LogisticRegression(max_iter=1000, n_jobs=None)),
        ])
        clf.fit(X_train, y_train)
        y_pred = clf.predict(X_test)
        acc = accuracy_score(y_test, y_pred)
        return {
            'synthetic_to_real_accuracy': round(float(acc), 4)
        }

    def privacy_check(self, synthetic: List[Dict], real: List[Dict]) -> Dict:
        """Approximate re-identification via token-overlap similarity to nearest real item."""
        real_sets = [set(self._tokenize(self._extract_text(it))) for it in real]
        if not real_sets:
            return {
                'max_overlap': None,
                'share_over_threshold': None,
                'threshold': 0.8,
                'note': 'No real data provided.'
            }

        def max_overlap_ratio(tokens: set) -> float:
            if not tokens:
                return 0.0
            best = 0.0
            for r in real_sets:
                u = len(tokens | r)
                if u == 0:
                    continue
                j = len(tokens & r) / u
                if j > best:
                    best = j
            return float(best)

        syn_sets = [set(self._tokenize(self._extract_text(it))) for it in synthetic]
        overlaps = [max_overlap_ratio(s) for s in syn_sets]
        threshold = 0.8
        share = float(sum(1 for v in overlaps if v >= threshold) / max(1, len(overlaps)))

        return {
            'max_overlap': round(max(overlaps) if overlaps else 0.0, 3),
            'mean_overlap': round(float(np.mean(overlaps)) if overlaps else 0.0, 3),
            'share_over_threshold': round(share, 3),
            'threshold': threshold,
        } 