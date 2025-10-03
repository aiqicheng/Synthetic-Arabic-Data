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



EXAMS_APPLIED_PROMPT = (
    """
[Role: Experienced Arabic high school teacher]

You are given an original question that may be too simple or recall-based.  
Your task: rewrite it into a **harder, applied multiple-choice exam question in Arabic** with these properties:

1. Applied Complexity (تعقيد تطبيقي):
   - The question must require reasoning, application, or interpretation — not just recalling a single fact.
   - Introduce a real-world scenario, short case study, or experimental setup.
   - Encourage students to connect knowledge across concepts (e.g., cause-and-effect, data interpretation, comparing outcomes).

2. Naturalness (طبيعي):
   - The question should read smoothly in Arabic, like a teacher writing a challenging test.
   - Use natural exam phrasing: "ما الذي يحدث إذا...", "في أي حالة يمكن أن...", "كيف يمكن تفسير..."
   - Avoid robotic or overly simplistic phrasing.

3. Similar Style (أسلوب مشابه):
   - Keep the tone academic and the length between 20–40 words.
   - Match the structure of real exam papers (context + question).
   - Cover diverse subjects: science, geography, literature, history, or math.

4. Different but Connected Content (محتوى مختلف لكنه مرتبط):
   - Do not reuse the same entity or fact from the original.
   - Build on the same **subject domain** (e.g., if original was about photosynthesis, keep within biology but raise complexity).
   - Add contextual richness (e.g., link to climate, human impact, lab experiments).

Constraints:
- Provide exactly 4 options (A–D).
- Options should be plausible, distinct, and include:
  * one common misconception,
  * one near-miss (partially correct but wrong),
  * one clearly wrong,
  * and one correct answer.
- Correct answer must be {target_answer_letter}.
- Use academic vocabulary and at least one subject-specific term.
- The scenario should increase difficulty without becoming university-level.

Output Format:
Return ONLY a valid JSON object in this structure:
{
  "question": "...",
  "options": ["A. ...", "B. ...", "C. ...", "D. ..."],
  "answer": "{target_answer_letter}",
  "notes": "Short explanation of how the new question increases difficulty by requiring applied reasoning instead of simple recall"
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
