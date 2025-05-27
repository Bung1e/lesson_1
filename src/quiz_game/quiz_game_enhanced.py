import os
import json
from typing import Dict, List
from openai import AzureOpenAI
from dotenv import load_dotenv
from rich.console import Console
from rich.prompt import Prompt
from rich.panel import Panel
from rich.table import Table
import time


load_dotenv()
console = Console()

client = AzureOpenAI(
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),
    api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-12-01-preview"),
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT")
)

def get_quiz_questions(total_questions = 5):
    prompt = """Generate a quiz with {total_questions} questions in the following JSON format:
{{
    "questions": [
        {{
            "question": "The question text",
            "options": {{
                "A": "Option A text",
                "B": "Option B text",
                "C": "Option C text",
                "D": "Option D text"
            }},
            "correct_answer": "A/B/C/D",
            "explanation": "Brief explanation of why this is the correct answer"
        }}
    ]
}}

Requirements:
1. Each question should be challenging but fair
2. All options should be plausible
3. The explanation should be educational
4. The response must be valid JSON
5. Only one option should be correct
6. Questions should be diverse and cover different topics
7. Each question should have a clear and unambiguous correct answer""".format(total_questions=total_questions)

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are a quiz generator that creates educational questions."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=2000,
            temperature=0.7,
            response_format={"type": "json_object"}
        )
        
        questions_data = json.loads(response.choices[0].message.content)
        return questions_data["questions"]
        
    except Exception as e:
        raise

def display_welcome():
    console.print(Panel.fit(
        "[bold blue]Welcome to the Quiz Game![/bold blue]\n"
        "[yellow]Test your knowledge with our AI-powered questions[/yellow]",
        title="🎮 Quiz Game",
        border_style="blue"
    ))

def display_question(question_number, question):
    console.print(Panel(
        f"[bold green]Question {question_number}[/bold green]\n\n{question['question']}",
        title="📝 Question",
        border_style="green"
    ))
    
    table = Table(show_header=False, box=None)
    table.add_column("Option", style="cyan")
    table.add_column("Answer", style="white")
    
    for option, text in question['options'].items():
        table.add_row(option, text)
    console.print(table)

def display_score(score, total):
    percentage = (score/total)*100
    console.print(Panel(
        f"[bold yellow]Score: {score}/{total}[/bold yellow]\n"
        f"[bold blue]Percentage: {percentage:.1f}%[/bold blue]",
        title="📊 Score",
        border_style="yellow"
    ))

def play_quiz():
    score = 0
    questions = 5
    display_welcome()
    
    try:
        quiz_questions = get_quiz_questions(questions)
        
        for i, question in enumerate(quiz_questions, 1):
            display_question(i, question)
            
            while True:
                user_answer = Prompt.ask(
                    "\nYour answer",
                    choices=["A", "B", "C", "D"]
                ).upper()
                
                if user_answer in ['A', 'B', 'C', 'D']:
                    break
                console.print("[red]Please enter A, B, C, or D[/red]")
            
            console.print("\n[bold]Correct Answer:[/bold]")
            console.print(Panel(
                f"[bold]{question['correct_answer']}[/bold]\n"
                f"[italic]{question['explanation']}[/italic]",
                border_style="blue"
            ))
            
            if user_answer == question['correct_answer']:
                console.print("[green]Correct! 🎉[/green]")
                score += 1
            else:
                console.print("[red]Wrong! 😢[/red]")
            
            display_score(score, i)
            time.sleep(1)
        
        table = Table(title="Final Results")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="magenta")
        table.add_row("Total Questions", str(questions))
        table.add_row("Correct Answers", str(score))
        table.add_row("Percentage", f"{(score/questions)*100:.1f}%")
        
        console.print("\n")
        console.print(table)
        
        if score == questions:
            console.print("[bold green]Perfect Score! You're a genius! 🌟[/bold green]")
        elif score >= questions * 0.8:
            console.print("[bold yellow]Great job! You're really smart! 🎯[/bold yellow]")
        elif score >= questions * 0.6:
            console.print("[bold blue]Good effort! Keep learning! 📚[/bold blue]")
        else:
            console.print("[bold red]Keep practicing! You'll get better! 💪[/bold red]")
            
    except Exception as e:
        console.print("[bold red]An error occurred during the quiz. Please try again later.[/bold red]")

if __name__ == "__main__":
    play_quiz() 