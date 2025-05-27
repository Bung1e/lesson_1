import os
import json
import nbformat
from nbformat.v4 import new_notebook, new_code_cell, new_output
from dotenv import load_dotenv

from openai import AzureOpenAI
from datetime import datetime



def create_notebook_with_results(vector_result, semantic_result, query):
    nb = new_notebook()

    vector_cell = new_code_cell(
        source=f"""# Vector Search Result
vector_result = {json.dumps(vector_result, indent=2, ensure_ascii=False)}
print("Vector Search Response:")
print(json.dumps(vector_result, indent=2, ensure_ascii=False))""",
        outputs=[new_output("stream",
                           name="stdout",
                           text=f"Vector Search Response:\n{json.dumps(vector_result, indent=2, ensure_ascii=False)}\n")]
    )

    semantic_cell = new_code_cell(
        source=f"""# Semantic Search Result
semantic_result = {json.dumps(semantic_result, indent=2, ensure_ascii=False)}
print("Semantic Search Response:")
print(json.dumps(semantic_result, indent=2, ensure_ascii=False))""",
        outputs=[new_output("stream",
                           name="stdout",
                           text=f"Semantic Search Response:\n{json.dumps(semantic_result, indent=2, ensure_ascii=False)}\n")]
    )

    comparison_cell = new_code_cell(
        source=f"""# Compare Results
print("=== COMPARISON ===")
print(f"Query: {query}")
print(f"Vector search response length: {{len(vector_result.get('content', ''))}}")
print(f"Semantic search response length: {{len(semantic_result.get('content', ''))}}")
print("\\nVector search content preview:")
print(vector_result.get('content', '')[:200] + "...")
print("\\nSemantic search content preview:")
print(semantic_result.get('content', '')[:200] + "...")""",
        outputs=[new_output("stream",
                           name="stdout",
                           text=f"""=== COMPARISON ===
Query: {query}
Vector search response length: {len(vector_result.get('content', ''))}
Semantic search response length: {len(semantic_result.get('content', ''))}

Vector search content preview:
{vector_result.get('content', '')[:200]}...

Semantic search content preview:
{semantic_result.get('content', '')[:200]}...""")]
    )

    nb.cells = [vector_cell, semantic_cell, comparison_cell]
    return nb

def save_notebook(notebook, filename="queries.ipynb"):
    os.makedirs("notebooks", exist_ok=True)
    filepath = os.path.join("notebooks", filename)

    with open(filepath, 'w', encoding='utf-8') as f:
        nbformat.write(notebook, f)

    print(f"Saved to {filepath}")

def perform_search(chat_client, query, search_type, search_url, search_key, index_name, embedding_model, chat_model, semantic_config="azureml-default"):
    prompt = [
        {"role": "system", "content": "You are a travel assistant. Based on the search results from Margie's Travel brochures, provide helpful information about travel destinations, accommodations, and services."},
        {"role": "user", "content": query}
    ]

    rag_params = {
        "data_sources": [
            {
                "type": "azure_search",
                "parameters": {
                    "endpoint": search_url,
                    "index_name": index_name,
                    "authentication": {
                        "type": "api_key",
                        "key": search_key,
                    },
                    "query_type": search_type,
                }
            }
        ],
    }

    if search_type == "vector":
        rag_params["data_sources"][0]["parameters"]["embedding_dependency"] = {
            "type": "deployment_name",
            "deployment_name": embedding_model,
        }
    elif search_type == "semantic":
        if semantic_config:
            rag_params["data_sources"][0]["parameters"]["semantic_configuration"] = semantic_config

    response = chat_client.chat.completions.create(
        model=chat_model,
        messages=prompt,
        extra_body=rag_params
    )

    result = {
        "search_type": search_type,
        "query": query,
        "content": response.choices[0].message.content,
        "timestamp": datetime.now().isoformat()
    }

    if hasattr(response.choices[0].message, 'context'):
        result["context"] = response.choices[0].message.context

    return result

def process_query(client, query, search_url, search_key, index_name, embed_model, chat_model, semantic_cfg):
    print(f"Processing: {query}")

    vector_res = perform_search(client, query, "vector", search_url, search_key, index_name, embed_model, chat_model)

    semantic_res = perform_search(client, query, "semantic", search_url, search_key, index_name, embed_model, chat_model, semantic_cfg)

    print("\nVector Search:")
    print(vector_res["content"])

    print("\nSemantic Search:")
    print(semantic_res["content"])

    nb = create_notebook_with_results(vector_res, semantic_res, query)
    save_notebook(nb)

    return vector_res, semantic_res

def main():
    load_dotenv()

    ai_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
    ai_key = os.getenv("AZURE_OPENAI_API_KEY")
    chat_model = os.getenv("CHAT_MODEL")
    embed_model = os.getenv("EMBEDDING_MODEL")
    search_url = os.getenv("SEARCH_ENDPOINT")
    search_key = os.getenv("SEARCH_KEY")
    index_name = os.getenv("INDEX_NAME")
    semantic_cfg = os.getenv("SEMANTIC_CONFIG", "azureml-default")

    client = AzureOpenAI(
        api_version="2024-12-01-preview",
        azure_endpoint=ai_endpoint,
        api_key=ai_key
    )

    print("Travel Search Assistant")
    print("Enter your travel questions (type 'quit' to exit):")

    while True:
        query = input("\n> ").strip()
        if query.lower() == "quit":
            break
        if query:
            process_query(client, query, search_url, search_key, index_name, embed_model, chat_model, semantic_cfg)

if __name__ == '__main__':
    main()
