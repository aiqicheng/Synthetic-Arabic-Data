EXAMS_TEACHER_PROMPT = (
    """
[Role: Experienced Arabic high school teacher]
You are given an original question from a question bank.
Your task: generate a **new multiple-choice exam question in Arabic** that has the following properties:

1. Naturalness (طبيعي):  
   - The question should read smoothly in Arabic, as if written naturally by a human teacher.  
   - Avoid robotic, repetitive, or overly simple phrasing.  

2. Similar Style (أسلوب مشابه):  
   - Match the original question’s style, tone, and length (15–35 words).  
   - Maintain academic style and complexity, consistent with real exam papers.  

3. Subject Consistency (الموضوع):  
   {subject}**Subject Focus**: Generate questions specifically in the subject area: {subject}{/subject}
   - **If no subject is specified**, keep the same subject as the seed question.
   - **If the seed question belongs to a specific subject (e.g., التربية الإسلامية, التاريخ, الجغرافيا, العلوم, الرياضيات, الأدب): keep the new question within that same subject area.**  
   - Do not switch subjects.  
   - Only when the subject is unclear, you may rotate across history, science, mathematics, literature, or geography for diversity.  

4. Correctness (الصحة):  
   - The question and its correct answer MUST be factually accurate, aligned with reliable and widely accepted knowledge in that subject.  
   - Wrong options must remain plausible but clearly incorrect.  
   - Avoid controversial, ambiguous, or disputed information (especially in theology, history, or politics).  

5. Different Content (محتوى مختلف):  
   - The new question must focus on a different topic, scenario, or detail than the original, but remain in the same subject.  
   - Do not reuse the same entities, numbers, or specific facts.  
   - Avoid trivial paraphrases or minor word changes.  

Additional Constraints:  
- Use varied and academic vocabulary; include at least one subject-specific term.  
- Avoid simple factual recall; some questions should require reasoning or comparison.  
- Provide 4 options (A–D), concise, plausible, and semantically distinct.  
- At least one option should reflect a common misconception.  
- At least one option should be a near-miss (close but incorrect).  
- The correct answer MUST be letter {target_answer_letter}.  

Steps:  
- Analyze the original question’s **subject and style**.  
- Keep the subject area consistent.  
- Keep the style consistent.  
- Replace the content with a new scenario, theme, or detail in the same subject.  
- Ensure factual accuracy of the question and answer.  
- Ensure no overlap of entities, facts, or specific details with the original.  

Output Format:  
Return ONLY a valid JSON object in this structure:
{
  "question": "...",
  "options": ["A. ...", "B. ...", "C. ...", "D. ..."],
  "answer": "{target_answer_letter}",
  "notes": "Short explanation of why this new question meets Naturalness, Similar Style, Subject Consistency, Correctness, and Different Content"
}
    """.strip()
)




SENTIMENT_PROMPT = (
    """
[Role: Arabic Twitter user / restaurant customer]
Generate a short text (30–50 words) expressing a clear sentiment (positive, negative, or neutral).
Label the sentiment explicitly.
Return ONLY a valid JSON object:
{
  "text": "...",
  "sentiment": "positive | negative | neutral"
}
    """.strip()
)

GRAMMAR_QA_PROMPT = (
    """
[Role: Arabic learner]
Write a sentence with one or more grammar mistakes.

[Role: Arabic teacher]
Correct the sentence and explain the mistake.
Return ONLY a valid JSON object:
{
  "input": "...(incorrect sentence)",
  "correction": "...(corrected sentence)",
  "explanation": "..."
}
    """.strip()
)

MMLU_TEACHER_PROMPT = (
    """
[Role: Expert Arabic Subject Instructor and Technical Verifier]
You are given an original MMLU (Massive Multitask Language Understanding) question from {subject}.
Your task: generate a **new multiple-choice MMLU-style question in Arabic** that meets the following criteria:

---

### 1. Technical Accuracy (دقة تقنية)
- The question and correct answer MUST be factually and scientifically accurate within the {subject} domain.
- Use **precise Arabic technical terminology**.
- Double-check that **only one option is correct** and that the other three are unambiguously incorrect.
- Before finalizing, **mentally verify** the correctness of the chosen answer based on established scientific or academic consensus.

---

### 2. MMLU Style Consistency (اتساق أسلوب MMLU)
- Match the **complexity, precision, and tone** of real MMLU questions.
- Maintain an **academic, formal Arabic register**.
- Keep question length between **15–40 words**.
- Avoid ambiguity or trick phrasing.

---

### 3. Subject Domain Focus (تركيز مجال الموضوع)
**Subject Focus:** Generate questions specifically within **{subject}**.
- Stay strictly within the key subtopics and principles of this domain.
- Include at least one **domain-specific term or concept** (e.g., algorithm, law, principle, theory, equation, or philosophical stance).
- Questions should test **conceptual understanding**, not mere recall.

---

### 4. Different Technical Content (محتوى تقني مختلف)
- Use a **different concept, scenario, or example** than the original question.
- Keep within the same domain but vary the tested skill or concept.
- Avoid reusing identical facts, examples, or entities.

---

### 5. Quality Distractors (مشتتات عالية الجودة)
- Include **plausible wrong options** representing **common misconceptions** or **near-misses**.
- Ensure **only one correct answer** is fully valid under domain knowledge.
- Wrong options should sound reasonable but contain subtle factual or conceptual errors.

---

### 6. Self-Consistency Verification (التحقق من الصحة الذاتية)
Before output, **perform an internal verification** step:
- Confirm that the correct answer is consistent with accepted {subject} theory or definitions.
- Confirm that no other option could be arguably correct.
- Confirm that technical terminology is used accurately and unambiguously.

---

### 7. Labeling & Answer Key Constraints (قيود ترميز الخيارات والإجابة)
- **Option labels must be EXACTLY these ASCII forms:** `A. `, `B. `, `C. `, `D. ` (capital Latin letter, a period, then a space).
- **Do NOT localize labels** to Arabic letters (أ، ب، ج، د) or use parentheses/numbers.
- The `"answer"` field must be **exactly one of** `"A"`, `"B"`, `"C"`, or `"D"` (single uppercase Latin letter, no punctuation or spaces).

---

### Output Format
Return ONLY a valid JSON object structured exactly as follows:
{
  "question": "...",
  "options": ["A. ...", "B. ...", "C. ...", "D. ..."],
  "answer": "{target_answer_letter}"
}

---
**Important:** Do NOT output explanations, reasoning, or any additional text outside the JSON object.
    """.strip()
)
