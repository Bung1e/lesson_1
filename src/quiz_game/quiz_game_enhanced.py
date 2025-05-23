import os
from openai import AzureOpenAI
from dotenv import load_dotenv
from rich.console import Console
from rich.prompt import Prompt
from rich.panel import Panel
from rich.table import Table
from rich import print as rprint
import time

load_dotenv()
console = Console()

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

def parse_question(question_text):
    parts = question_text.split("Correct Answer: ")
    question_part = parts[0].strip()
    correct_answer = parts[1].strip() if len(parts) > 1 else ""
    lines = question_part.split('\n')
    question = lines[0].strip()
    options = [line.strip() for line in lines[1:] if line.strip()]
    
    return question, options, correct_answer

def display_welcome():
    console.print(Panel.fit(
        "[bold blue]Welcome to the Quiz Game![/bold blue]\n"
        "[yellow]Test your knowledge with our AI-powered questions[/yellow]",
        title="🎮 Quiz Game",
        border_style="blue"
    ))

def display_question(question_number, question, options):
    console.print(Panel(
        f"[bold green]Question {question_number}[/bold green]\n\n{question}",
        title="📝 Question",
        border_style="green"
    ))
    
    table = Table(show_header=False, box=None)
    table.add_column("Option", style="cyan")
    table.add_column("Answer", style="white")
    
    for option in options:
        table.add_row(option[0], option[2:])
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
    
    for i in range(questions):
        question_text = get_quiz_question()
        question, options, correct_answer = parse_question(question_text)
        display_question(i+1, question, options)
        
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
            f"[bold]{correct_answer}[/bold]",
            border_style="blue"
        ))
        
        if user_answer == correct_answer:
            console.print("[green]Correct! 🎉[/green]")
            score += 1
        else:
            console.print("[red]Wrong! 😢[/red]")
        display_score(score, i+1)
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

if __name__ == "__main__":
    play_quiz() 