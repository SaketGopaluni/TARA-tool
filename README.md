# TARA Assistant

TARA Assistant is a web-based tool designed to aid cybersecurity professionals and developers in performing Threat Analysis and Risk Assessment (TARA) for connected automotive systems

## Features

The application consists of three primary modules:

### 1. Coding Module
- **Script Generation:** Generate scripts (Python, C++, etc.) based on natural language requirements.
- **Debugging:** Debug existing scripts with AI-powered analysis and explanations.
- **Modification:** Modify scripts based on instructions.
- **Change Explanation:** Get clear explanations for any modifications made
- **Diffchecker:** Compare different versions of scripts with highlighted differences

### 2. Testing Module
- **Unit Testing:** Generate test cases for scripts.
- **Test Improvement:** Enhance test cases based on execution results

### 3. Chat Module
- **ECU Explanations:** Interact with an AI assistant knowledgeable about ECUs, TARA, and cybersecurity.
- **Damage Scenarios:** Generate potential damage scenarios based on the CIA triad
- **Threat Scenarios:** Create threat scenarios using the STRIDE model
- **Attack Patterns:** Generate possible attack patterns based on dataflow descriptions

## Tech Stack

- **Backend:** Flask (Python)
- **Frontend:** HTML, CSS, JavaScript with Tailwind CSS
- **Database:** NeonDB (PostgreSQL)
- **AI Integration:** OpenRouter (meta-llama/llama-4-maverick model)

## Usage Guide

### Coding Module
1. Navigate to the "Coding" tab from the main navigation menu
2. To generate a new script, provide a detailed description of the requirements
3. For debugging, select or paste a script with potential issues
4. For modifications, select a script and describe the changes needed
5. Use the compare feature to view differences between script versions

### Testing Module
1. Navigate to the "Testing" tab from the main navigation menu
2. Select a script for which you want to generate tests
3. Specify the testing requirements
4. Execute tests to view results
5. Improve tests based on execution feedback

### Chat Module
1. Navigate to the "Chat" tab from the main navigation menu
2. Use the specialized buttons for generating specific content:
   - ECU Explanation
   - Damage Scenario (CIA)
   - Threat Scenario (STRIDE)
   - Attack Pattern
3. Or simply type your questions about automotive cybersecurity

## Contact

For questions or support, please open an issue on the project's GitHub repository.
