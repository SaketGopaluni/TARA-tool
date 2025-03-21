# TARA Assistant

TARA Assistant is a web-based tool designed to aid cybersecurity professionals and developers in performing Threat Analysis and Risk Assessment (TARA) for automotive systems, with a focus on Electronic Control Units (ECUs).

## Features

The application consists of three primary modules:

### 1. Coding Module
- **Script Generation:** Create new scripts based on specified requirements
- **Debugging:** Identify and fix errors in existing scripts with explanations
- **Modification:** Request changes to existing scripts and receive updated versions
- **Change Explanation:** Get clear explanations for any modifications made
- **Diffchecker:** Compare different versions of scripts with highlighted differences

### 2. Testing Module
- **Unit Testing:** Write and execute unit tests for scripts
- **Test Improvement:** Enhance test cases based on execution results

### 3. Chat Module
- **ECU Explanations:** Get detailed information about ECUs, their functions, and security implications
- **Damage Scenarios:** Generate potential damage scenarios based on the CIA triad
- **Threat Scenarios:** Create threat scenarios using the STRIDE model
- **Attack Patterns:** Generate possible attack patterns based on dataflow descriptions

## Tech Stack

- **Backend:** Flask (Python)
- **Frontend:** HTML, CSS, JavaScript with Tailwind CSS
- **Database:** NeonDB (PostgreSQL)
- **AI Integration:** OpenAI GPT-4O API

## Setup Instructions

### Prerequisites

- Python 3.9+ installed
- An OpenAI API key with access to GPT-4O
- A NeonDB PostgreSQL database (or you can use the provided connection string)

### Local Development Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/tara-assistant.git
   cd tara-assistant
   ```

2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   
   # On Windows
   venv\Scripts\activate
   
   # On macOS/Linux
   source venv/bin/activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Create a `.env` file in the project root with the following variables:
   ```
   FLASK_APP=app.py
   FLASK_ENV=development
   SECRET_KEY=your-secret-key
   OPENAI_API_KEY=your-openai-api-key
   DATABASE_URL=postgresql://neondb_owner:npg_4ksIGc2hmgye@ep-green-brook-a5k5r5cf-pooler.us-east-2.aws.neon.tech/neondb?sslmode=require
   ```

   Replace `your-secret-key` with a secure random string and `your-openai-api-key` with your valid OpenAI API key.

5. Run the application:
   ```bash
   flask run
   ```

6. Open a web browser and navigate to: http://127.0.0.1:5000

### Deployment to Vercel

1. Make sure you have the Vercel CLI installed:
   ```bash
   npm install -g vercel
   ```

2. Login to Vercel:
   ```bash
   vercel login
   ```

3. Deploy the application:
   ```bash
   vercel
   ```

4. Set the required environment variables in the Vercel dashboard:
   - `SECRET_KEY`
   - `OPENAI_API_KEY`
   - `DATABASE_URL`
   - `FLASK_ENV=production`
   - `FLASK_CONFIG=production`

5. The application will be deployed and a URL will be provided.

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