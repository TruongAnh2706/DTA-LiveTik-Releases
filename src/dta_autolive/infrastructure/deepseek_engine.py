import requests


def query_deepseek_v3(viewer_name, comment_text, api_key, system_prompt):
    """
    Gửi câu hỏi của khán giả Live Stream tới DeepSeek V3 API và nhận phản hồi tức thì.
    """
    if not api_key or not api_key.strip():
        raise ValueError("Chưa cấu hình DeepSeek API Key!")

    url = "https://api.deepseek.com/chat/completions"
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {api_key.strip()}"}

    user_prompt = f"Bình luận từ khán giả '{viewer_name}': \"{comment_text}\". Hãy trả lời ngắn gọn theo System Prompt."

    payload = {
        "model": "deepseek-chat",  # DeepSeek V3 Engine
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "max_tokens": 120,
        "temperature": 0.7,
    }

    response = requests.post(url, headers=headers, json=payload, timeout=8)
    if response.status_code == 200:
        data = response.json()
        choices = data.get("choices", [])
        if choices:
            return choices[0]["message"]["content"].strip()
        return "DTA Shop em cảm ơn sếp! Sếp bấm vào giỏ hàng xem nha! 🔥"
    raise Exception(f"DeepSeek API Error [{response.status_code}]: {response.text}")
