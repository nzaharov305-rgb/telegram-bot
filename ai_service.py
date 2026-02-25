import logging
import os

import openai

from config import get_redis

logger = logging.getLogger(__name__)

async def analyze_listing(listing: dict) -> str | None:
    """Perform AI analysis of a listing and cache in Redis."""
    try:
        listing_id = listing.get("id")
        if not listing_id:
            return None
        redis = await get_redis()
        key = f"ai:{listing_id}"
        cached = await redis.get(key)
        if cached:
            return cached

        # build prompt
        prompt = (
            "Ты — эксперт по недвижимости Алматы.\n"
            "Проанализируй объявление:\n"
            f"title: {listing.get('title')}\n"
            f"price: {listing.get('price')}\n"
            f"district: {listing.get('district')}\n"
            f"residential_complex: {listing.get('residential_complex')}\n"
            f"description: {listing.get('description')}\n\n"
            "Выдай:\n"
            "1. 📊 Оценка цены (ниже/выше рынка)\n"
            "2. ⚠ Риск (низкий/средний/высокий)\n"
            "3. 💰 Инвестиционная привлекательность\n"
            "4. Краткий вывод (1–2 предложения)\n\n"
            "Ответ в сжатом формате."
        )
        openai.api_key = os.getenv("OPENAI_API_KEY")
        resp = await openai.ChatCompletion.acreate(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=200,
            temperature=0.7,
        )
        text = resp.choices[0].message.content.strip()
        await redis.set(key, text, ex=21600)
        return text
    except Exception as e:
        logger.warning("AI analyze error: %s", e)
        return None
