from __future__ import annotations

import os
import json
import re
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta

import httpx

# Global chat history storage
_chat_histories: Dict[str, List[Dict[str, Any]]] = {}


def _extract_json_from_markdown(text: str) -> str:
    """Extract JSON from markdown code blocks like ```json\n{...}\n```"""
    json_match = re.search(r'```(?:json)?\s*\n?(.*?)\n?```', text, re.DOTALL)
    if json_match:
        return json_match.group(1).strip()
    json_match = re.search(r'\{.*\}', text, re.DOTALL)
    if json_match:
        return json_match.group(0)
    return text


def clear_chat_history(session_id: Optional[str] = None, older_than_hours: Optional[int] = None) -> int:
    """
    Clear chat histories for performance improvement.
    
    Args:
        session_id: If provided, clear only this specific session. If None, clear all sessions.
        older_than_hours: If provided, only clear histories older than this many hours.
    
    Returns:
        Number of messages cleared.
    """
    cleared_count = 0
    
    if session_id:
        # Clear specific session
        if session_id in _chat_histories:
            if older_than_hours:
                cutoff_time = datetime.now() - timedelta(hours=older_than_hours)
                original_count = len(_chat_histories[session_id])
                _chat_histories[session_id] = [
                    msg for msg in _chat_histories[session_id]
                    if msg.get('timestamp', datetime.now()) > cutoff_time
                ]
                cleared_count = original_count - len(_chat_histories[session_id])
            else:
                cleared_count = len(_chat_histories[session_id])
                _chat_histories[session_id] = []
    else:
        # Clear all sessions
        if older_than_hours:
            cutoff_time = datetime.now() - timedelta(hours=older_than_hours)
            for sid in list(_chat_histories.keys()):
                original_count = len(_chat_histories[sid])
                _chat_histories[sid] = [
                    msg for msg in _chat_histories[sid]
                    if msg.get('timestamp', datetime.now()) > cutoff_time
                ]
                cleared_count += original_count - len(_chat_histories[sid])
                # Remove empty sessions
                if not _chat_histories[sid]:
                    del _chat_histories[sid]
        else:
            # Clear all histories
            for session_messages in _chat_histories.values():
                cleared_count += len(session_messages)
            _chat_histories.clear()
    
    return cleared_count


def get_chat_history_stats() -> Dict[str, Any]:
    """Get statistics about current chat histories."""
    total_sessions = len(_chat_histories)
    total_messages = sum(len(msgs) for msgs in _chat_histories.values())
    
    return {
        "total_sessions": total_sessions,
        "total_messages": total_messages,
        "sessions": {
            sid: len(msgs) for sid, msgs in _chat_histories.items()
        }
    }


def call_llm(model: str, prompt: str, temperature: float = 0.7, top_p: float = 0.95, session_id: Optional[str] = None, use_chat_history: bool = False) -> str:
    if model.startswith("openai:"):
        openai_model = model.split(":", 1)[1]
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY is not set in environment")
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        
        # Build messages array
        messages = [
            {"role": "system", "content": "You are a helpful Arabic data generator. Return ONLY valid JSON without any markdown formatting or explanations."}
        ]
        
        # Add chat history if enabled and session_id provided
        if use_chat_history and session_id:
            if session_id in _chat_histories:
                messages.extend(_chat_histories[session_id])
        
        # Add current user message
        messages.append({"role": "user", "content": prompt})
        
        payload = {
            "model": openai_model,
            "messages": messages,
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
                
                # Store chat history if enabled and session_id provided
                if use_chat_history and session_id:
                    if session_id not in _chat_histories:
                        _chat_histories[session_id] = []
                    
                    # Add user message and assistant response to history
                    _chat_histories[session_id].append({
                        "role": "user", 
                        "content": prompt,
                        "timestamp": datetime.now()
                    })
                    _chat_histories[session_id].append({
                        "role": "assistant", 
                        "content": content,
                        "timestamp": datetime.now()
                    })
                
                return json_content
        except Exception as e:
            raise RuntimeError(f"OpenAI API call failed: {e}")
    
    # Fallback mock remains deterministic
    if "options" in prompt and "answer" in prompt:
        return json.dumps({
            "question": "ما عاصمة دولة عربية تطل على الخليج وتتميز بمعمار حديث؟",
            "options": ["A. الدوحة", "B. الرياض", "C. جدة", "D. المنامة"],
            "answer": "A"
        }, ensure_ascii=False)
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