EXAMS_TEACHER_PROMPT = (
    """
[Role: Arabic high school teacher]
Write a multiple-choice exam question in Arabic for {subject}.
Provide 4 options (A, B, C, D) and specify the correct answer.
Return ONLY a valid JSON object:
{
  "question": "...",
  "options": ["A. ...", "B. ...", "C. ...", "D. ..."],
  "answer": "A|B|C|D"
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