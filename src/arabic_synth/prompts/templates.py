EXAMS_TEACHER_PROMPT = (
    """
[Role: Experienced Arabic high school teacher]
Write a multiple-choice exam question in Arabic for a high school subject.
Subjects: history, science, mathematics, literature, or geography (rotate for diversity).

Constraints:
- Question length: 15–35 words, must be a complete sentence in academic style
- Use varied and academic vocabulary; include at least one subject-specific term
- Avoid repetitive phrasing and simple factual recall questions
- Options must be concise, plausible, and semantically distinct
- At least one option should represent a common misconception
- At least one option should be a near-miss (close but incorrect)
- The correct answer MUST be letter {target_answer_letter}
- Question style should resemble real exam papers, with some requiring reasoning or comparison, not only recall
Return ONLY a valid JSON object:
{
  "question": "...",
  "options": ["A. ...", "B. ...", "C. ...", "D. ..."],
  "answer": "{target_answer_letter}"
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