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
   - Rotate subjects for diversity: history, science, mathematics, literature, or geography.  

3. Different Content (محتوى مختلف):  
   - The new question must focus on a different topic, scenario, or detail than the original.  
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
- Analyze the original question’s **style** (tone, length, format).  
- Keep the style consistent.  
- Replace the content with a new scenario, theme, or subject.  
- Ensure no overlap of entities, facts, or specific details with the original.  

Output Format:  
Return ONLY a valid JSON object in this structure:
{
  "question": "...",
  "options": ["A. ...", "B. ...", "C. ...", "D. ..."],
  "answer": "{target_answer_letter}",
  "notes": "Short explanation of why this new question meets Naturalness, Similar Style, Different Content"
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
