import os
from openai import AzureOpenAI
from dotenv import load_dotenv

load_dotenv()

client = AzureOpenAI(
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),
    api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-12-01-preview"),
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT")
)

def run_prompt(prompt, model = "gpt-4o"):
    response = client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ],
        max_tokens=1000,
        temperature=0.7
    )
    
    return {
        "response": response.choices[0].message.content,
        "input_tokens": response.usage.prompt_tokens,
        "output_tokens": response.usage.completion_tokens
    }

def main():
    prompts = [
        "What is 2+2?",
        "Tell me about cats",
        "What is Python?"
    ]
    
    model = "gpt-4o"
    os.makedirs("logs", exist_ok=True)

    with open("logs/usage.md", "w", encoding="utf-8") as f:
        for prompt in prompts:
            print(f"\nPrompt: {prompt}")
            result = run_prompt(prompt, model)
            
            f.write(f"Prompt: {prompt}\n")
            f.write(f"Response: {result['response']}\n")
            f.write(f"Input tokens: {result['input_tokens']}\n")
            f.write(f"Output tokens: {result['output_tokens']}\n")

            print(f"Response: {result['response']}")
            print(f"Input tokens: {result['input_tokens']}")
            print(f"Output tokens: {result['output_tokens']}")

if __name__ == "__main__":
    main() 