
## Project Structure

```
.
├── src/                   
│   ├── task_1/            
│   ├── task_2/            
│   ├── invest_task/       
│   └── quiz_game/        
├── backlog/               
├── logs/                 
├── prompts/                    
```

## Requirements

- Python 3.12 or higher
- Poetry for dependency management

## Installation

1. Clone the repository:
```bash
git clone [repository-url]
cd accenture-learning
```

2. Install dependencies using Poetry:
```bash
poetry install
```

3. Create a `.env` file in the root directory:
```env
AZURE_OPENAI_API_KEY=your_key
AZURE_OPENAI_API_VERSION=2024-12-01-preview
AZURE_OPENAI_ENDPOINT=your_endpoint
```


## Dependencies

Main dependencies:
- openai - for GPT API integration
- python-dotenv - for environment variables management
- isort - for import sorting
- black - for code formatting
- pytest - for testing
- pytest-cov - for code coverage

## Assignment Structure

### Week 1
- Basic Python assignments
- File and module operations
- GPT API integration
- User stories creation
- Scrum methodology
### Week 2
