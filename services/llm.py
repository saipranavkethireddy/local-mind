import httpx
import json

OLLAMA_HOST = "http://localhost:11434/api/generate"
DEFAULT_MODEL = "llama3"

class LocalLLMEngine:
    @staticmethod
    async def generate_response(prompt: str, context: str, model: str = DEFAULT_MODEL) -> str:
        system_prompt = (
            "You are LocalMind, a secure, air-gapped enterprise AI assistant. "
            "You must answer the user's question strictly using ONLY the provided local context. "
            "If the answer cannot be found in the context, reply exactly with: "
            "'I cannot verify this claim in the provided local documents.' "
            "Do not invent facts, names, numbers, or dates."
        )
        
        full_prompt = f"{system_prompt}\n\nLocal Context:\n{context}\n\nUser Question:\n{prompt}\n\nAnswer:"

        payload = {
            "model": model,
            "prompt": full_prompt,
            "stream": False,
            "options": {"temperature": 0.1}
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            try:
                response = await client.post(OLLAMA_HOST, json=payload)
                if response.status_code == 200:
                    return response.json().get("response", "Error generating response.")
                else:
                    return f"Local LLM Error: Server returned status {response.status_code}"
            except httpx.ConnectError:
                return "Error: Could not connect to local Ollama instance. Ensure Ollama is running locally."