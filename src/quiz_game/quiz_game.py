import os
from openai import AzureOpenAI
from dotenv import load_dotenv

load_dotenv()

client = AzureOpenAI(
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),
    api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-12-01-preview"),
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT")
)

def get_quiz_question():
    with open("prompts/best.txt", "r") as f:
        prompt = f.read()
    
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=500,
        temperature=0.7
    )
    
    return response.choices[0].message.content

def play_quiz():
    score = 0
    questions = 5 
    print("You will be asked", questions, "questions.")
    print("For each question, enter A, B, C, or D as your answer.")
    print("Let's begin!\n")
    for i in range(questions):
        print(f"\nQuestion {i+1}:")
        question_text = get_quiz_question()
        print(question_text.split("Correct Answer: ")[0].strip())
        correct_answer = question_text.split("Correct Answer: ")[-1].strip()
        while True:
            user_answer = input("\nYour answer (A/B/C/D): ").upper()
            if user_answer in ['A', 'B', 'C', 'D']:
                break
            print("Please enter A, B, C, or D")
        if user_answer == correct_answer:
            print("Correct! 🎉")
            score += 1
        else:
            print("Wrong!")
        print(f"Correct answer: {correct_answer}")
        print(f"Current score: {score}/{i+1}")
    print(f"\nGame Over! Your final score: {score}/{questions}")
    print(f"Percentage: {(score/questions)*100:.1f}%")

if __name__ == "__main__":
    play_quiz() 