"""
script to generate user stories
"""
import os
from openai import AzureOpenAI
from dotenv import load_dotenv

load_dotenv()

client = AzureOpenAI(
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),
    api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-12-01-preview"),
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT")
)

USER_STORY_PROMPT = """
create three INVEST user stories for a Social Media Sentiment Analysis project. 
The project aims to analyze customer feedback and social media posts to understand public sentiment about products and services.

for each story, follow these guidelines:
1. Make it Independent - each story should be self-contained
2. Make it Negotiable - leave room for discussion and refinement
3. Make it Valuable - clearly show the benefit
4. Make it Estimable - possible to estimate effort
5. Make it Small - completable in one sprint
6. Make it Testable - with clear acceptance criteria

format each story as:
"As a [role], I want [goal] so that [benefit]"

acceptance criteria should be specific and measurable.
focus on these areas:
- data collection and preprocessing
- model training and evaluation
- visualization and reporting
- api integration
- user interface
"""

def get_gpt_response(prompt):
    """
    get response from GPT model.

    args:
        prompt (str): The prompt to send to GPT
        model (str): The model to use
        
    returns:
        dict: Response containing the content and token usage
    """
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ],
        max_tokens=2000,
        temperature=0.7
    )
    
    return {
        "response": response.choices[0].message.content,
        "input_tokens": response.usage.prompt_tokens,
        "output_tokens": response.usage.completion_tokens
    }

def save_response_to_file(response, filename):
    """
    save GPT response to a markdown file.
    
    args:
        response (dict): The response from GPT
        filename (str): The filename to save to
    """
    os.makedirs("backlogs", exist_ok=True)
    with open(f"backlogs/{filename}", "w", encoding="utf-8") as f:
        f.write(response["response"])

def main():
    """generate user stories and save them to a file."""
    response = get_gpt_response(USER_STORY_PROMPT)
    save_response_to_file(response, "sprint1.md")

if __name__ == "__main__":
    main() 