# app/llm_generator.py
import os
from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
import requests
import json
from app.settings.models import *
from app.settings.llm_settings import *


# === Конфигурация (можно вынести в .env или config.yaml) ===
# LLM_MODE = os.getenv("LLM_MODE", "local")  # "local" или "api"
LLM_MODE = llm_mode
# LOCAL_MODEL_NAME = os.getenv("LOCAL_MODEL_NAME", "Qwen/Qwen1.5-1.8B-Chat")
LOCAL_MODEL_NAME = llm_model_name
API_URL = os.getenv("LLM_API_URL", "https://api.example.com/generate")
API_HEADERS = {
    "Authorization": f"Bearer {os.getenv('LLM_API_KEY', '')}",
    "Content-Type": "application/json"
}


# === Абстрактный интерфейс ===
class LLMGenerator(ABC):
    @abstractmethod
    def generate(self, prompt: str, max_tokens: int = 100) -> str:
        pass


# === Локальная модель (Hugging Face + transformers) ===
class LocalLLM(LLMGenerator):
    def __init__(self, model_name: str):
        try:
            from transformers import AutoTokenizer, AutoModelForCausalLM
            import torch
            self.device = "cuda" if torch.cuda.is_available() else "cpu"
            self.tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)
            device_map = {"": 0}  # Используем только GPU 0
            max_memory = {0: "4GiB"}  # Ограничение VRAM
            self.model = AutoModelForCausalLM.from_pretrained(
                model_name,
                device_map=device_map,
                max_memory=max_memory,  # ← КЛЮЧЕВОЙ ПАРАМЕТР
                trust_remote_code=True,
                quantization_config=quantization_config,
                torch_dtype=torch.float16
            )
            self.model.eval()
            print(f"✅ Локальная LLM загружена: {model_name} на {self.device}")
        except ImportError as e:
            raise RuntimeError(f"Не установлены зависимости для локальной LLM: {e}")

    def generate(self, prompt: str, max_tokens: int = 100) -> str:
        try:
            inputs = self.tokenizer(prompt, return_tensors="pt").to(self.device)
            outputs = self.model.generate(
                **inputs,
                max_new_tokens=max_tokens,
                do_sample=True,
                temperature=0.7,
                top_p=0.9,
                pad_token_id=self.tokenizer.eos_token_id
            )
            result = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
            # Убираем промпт из ответа
            if result.startswith(prompt):
                result = result[len(prompt):].strip()
            return result
        except Exception as e:
            raise RuntimeError(f"Ошибка генерации локальной LLM: {e}")


# === Внешний API ===
class APILLM(LLMGenerator):
    def __init__(self, api_url: str, headers: Dict[str, str]):
        self.api_url = api_url
        self.headers = headers

    def generate(self, prompt: str, max_tokens: int = 100) -> str:
        # payload = {
        #     "prompt": prompt,
        #     "max_tokens": max_tokens,
        #     "temperature": 0.7
        # }
        prompt = (
            "Ты — эксперт по анализу текстов. На основе приведённых фрагментов определи ОДНУ общую тему.\n"
            "Ответ должен быть:\n"
            "- на русском языке,\n"
            "- кратким (2–4 слова),\n"
            "- без пояснений, только тема.\n\n"
            "Фрагменты:\n" +
            "\n".join(f"- {chunk[:150]}" for chunk in chunks[:3]) +
            "\n\nТема:"
        )
        try:
            response = requests.post(self.api_url, headers=self.headers, json=payload, timeout=30)
            response.raise_for_status()
            data = response.json()
            # Настройте путь к тексту в зависимости от API
            return data.get("text", data.get("result", data.get("generated_text", "")))
        except Exception as e:
            raise RuntimeError(f"Ошибка вызова LLM API: {e}")


# === Фабрика генераторов ===
def create_llm_generator() -> LLMGenerator:
    if LLM_MODE == "local":
        return LocalLLM(LOCAL_MODEL_NAME)
    elif LLM_MODE == "api":
        return APILLM(API_URL, API_HEADERS)
    else:
        raise ValueError(f"Неизвестный LLM_MODE: {LLM_MODE}")


# === Основная функция для генерации описания кластера ===
def generate_cluster_description(chunks: List[str], max_tokens: int = 50) -> str:
    """
    Генерирует краткое описание темы кластера на основе фрагментов.
    
    Args:
        chunks: список текстовых фрагментов (чанков)
        max_tokens: максимальное число токенов в ответе
    
    Returns:
        str: краткое описание (например, "Возврат и гарантия")
    """
    if not chunks:
        return "Без темы"
    
    # Формируем промпт
    examples = "\n".join(f"- {chunk[:200]}" for chunk in chunks[:3])
    prompt = (
        "Кратко опишите общую тему этих фрагментов (2–5 слов):\n"
        f"{examples}\n\n"
        "Описание:"
    )
    
    try:
        generator = create_llm_generator()
        description = generator.generate(prompt, max_tokens=max_tokens)
        # Очищаем лишнее
        description = description.strip().rstrip(".").strip()
        return description if description else "Тема не определена"
    except Exception as e:
        print(f"⚠️  Не удалось сгенерировать описание: {e}")
        return "Без темы"


# # === Пример использования (для теста) ===
# if __name__ == "__main__":
#     test_chunks = [
#         "Как оформить возврат товара? Напишите в поддержку.",
#         "Можно ли вернуть товар без чека? Да, но потребуется паспорт.",
#         "Гарантия на технику — 2 года. Сохраняйте чек!"
#     ]
#     desc = generate_cluster_description(test_chunks)
#     print("Описание:", desc)