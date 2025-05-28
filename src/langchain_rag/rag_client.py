import requests
import json
import sys

AZURE_FUNCTION_ENDPOINT = "http://localhost:7071/api/ask"

def ask_rag_endpoint(question: str):
    """
    Sends a question to the RAG Azure Function endpoint and prints the response.

    Args:
        question: The question string to send.
    """
    try:
        params = {"question": question}
        
        print(f"Sending question: \"{question}\" to {AZURE_FUNCTION_ENDPOINT}")

        response = requests.get(AZURE_FUNCTION_ENDPOINT, params=params)

        response.raise_for_status() 

        response_data = response.json()

        if response_data.get("status") == "error":
             print(f"Error from endpoint: {response_data.get('error')}")
        else:
            print("\n--- Answer ---")
            print(response_data.get("answer", "No answer provided."))
            if "timestamp" in response_data:
                 print(f"\n(Timestamp: {response_data['timestamp']})")

    except requests.exceptions.RequestException as e:
        print(f"Error communicating with the Azure Function endpoint: {e}", file=sys.stderr)
    except json.JSONDecodeError:
        print(f"Error decoding JSON response: {response.text}", file=sys.stderr)
    except Exception as e:
        print(f"An unexpected error occurred: {e}", file=sys.stderr)

if __name__ == "__main__":
    if len(sys.argv) > 1:
        question = " ".join(sys.argv[1:])
        ask_rag_endpoint(question)
    else:
        print("Enter your questions (type 'quit' to exit):")
        while True:
            user_question = input("\nYour question: ").strip()
            if user_question.lower() == "quit":
                break
            if user_question:
                ask_rag_endpoint(user_question)
