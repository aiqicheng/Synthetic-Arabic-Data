from __future__ import annotations

import os
import json
import re
from typing import Optional

import httpx


def _extract_json_from_markdown(text: str) -> str:
    """Extract JSON from markdown code blocks like ```json\n{...}\n```"""
    json_match = re.search(r'```(?:json)?\s*\n?(.*?)\n?```', text, re.DOTALL)
    if json_match:
        return json_match.group(1).strip()
    json_match = re.search(r'\{.*\}', text, re.DOTALL)
    if json_match:
        return json_match.group(0)
    return text


def call_llm(model: str, prompt: str, temperature: float = 0.7, top_p: float = 0.95) -> str:
    if model.startswith("openai:"):
        openai_model = model.split(":", 1)[1]
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY is not set in environment")
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": openai_model,
            "messages": [
                {"role": "system", "content": "You are a helpful Arabic data generator. Return ONLY valid JSON without any markdown formatting or explanations."},
                {"role": "user", "content": prompt},
            ],
            "temperature": temperature,
            "top_p": top_p,
        }
        try:
            with httpx.Client(timeout=60) as client:
                resp = client.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload)
                resp.raise_for_status()
                data = resp.json()
                content = data["choices"][0]["message"]["content"]
                json_content = _extract_json_from_markdown(content)
                return json_content
        except Exception as e:
            raise RuntimeError(f"OpenAI API call failed: {e}")
    
    # Fallback mock with some variety
    if "options" in prompt and "answer" in prompt:
        import random
        import hashlib
        
        # Use prompt hash to generate consistent but varied responses
        prompt_hash = int(hashlib.md5(prompt.encode()).hexdigest()[:8], 16)
        random.seed(prompt_hash)
        
        # Mock question templates with variety
        questions = [
            {
                "question": "ما عاصمة دولة عربية تطل على الخليج وتتميز بمعمار حديث؟",
                "options": ["A. الدوحة", "B. الرياض", "C. جدة", "D. المنامة"],
                "answer": "A"
            },
            {
                "question": "أي من الكواكب التالية الأقرب إلى الشمس؟",
                "options": ["A. الأرض", "B. المريخ", "C. عطارد", "D. الزهرة"],
                "answer": "C"
            },
            {
                "question": "من هو مؤلف رواية 'مدن الملح'؟",
                "options": ["A. عبد الرحمن منيف", "B. نجيب محفوظ", "C. غسان كنفاني", "D. إميل حبيبي"],
                "answer": "A"
            },
            {
                "question": "ما هي أكبر قارة في العالم من حيث المساحة؟",
                "options": ["A. أفريقيا", "B. آسيا", "C. أوروبا", "D. أمريكا الشمالية"],
                "answer": "B"
            },
            {
                "question": "في أي عام تأسست جامعة الأزهر؟",
                "options": ["A. 970م", "B. 988م", "C. 1010م", "D. 1050م"],
                "answer": "A"
            },
            {
                "question": "ما هو العنصر الكيميائي الأكثر وفرة في الكون؟",
                "options": ["A. الأكسجين", "B. الكربون", "C. الهيدروجين", "D. الهيليوم"],
                "answer": "C"
            }
        ]
        
        # Select a question based on hash
        selected = questions[prompt_hash % len(questions)]
        return json.dumps(selected, ensure_ascii=False)
    if "sentiment" in prompt and "text" in prompt:
        return json.dumps({
            "text": "تجربة رائعة في المطعم اليوم؛ خدمة سريعة وطعام لذيذ وأسعار مناسبة.",
            "sentiment": "positive"
        }, ensure_ascii=False)
    return json.dumps({
        "input": "الولد ذهبت إلى المدرسة مبكرًا.",
        "correction": "الولد ذهب إلى المدرسة مبكرًا.",
        "explanation": "الفعل يجب أن يطابق الفاعل في التذكير والإفراد."
    }, ensure_ascii=False) 