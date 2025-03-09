# AutoGen-MultiAgent

AutoGen-MultiAgent is a web application that allows users to configure and deploy multiple AI agents using the AutoGen framework. The application facilitates real-time agent conversations based on user requirements and includes features for automated AI-driven email generation and distribution.

## Features

- **Agent Configuration**: Easily create and configure multiple AI agents through a user-friendly interface
- **Real-time Conversations**: Watch agents collaborate and solve problems in real-time
- **Automated Email Generation**: Generate personalized healthcare emails based on patient summaries
- **Bulk Email Sending**: Distribute emails to multiple recipients automatically
- **Gemini AI Integration**: Leverage Google's Gemini 2.0 Flash model for intelligent agent responses

## Installation

### Prerequisites

- Python 3.8+
- pip (Python package manager)
- Gmail account (for SMTP functionality)

### Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/karthikbolla/AutoGen-MultiAgent.git
   cd AutoGen-MultiAgent
   ```

2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   
   # On Windows
   venv\Scripts\activate
   
   # On macOS/Linux
   source venv/bin/activate
   ```

3. Install required packages:
   ```bash
   pip install -r requirements.txt
   ```

4. Configure API keys and credentials:
   
   Edit `config.py` to add your Gemini API key and SMTP credentials:
   ```python
   GEMINI_API_KEY = "add your gemini api key"
   SMTP_USER = "add your email-id"
   SMTP_PASSWORD = "add your email application password"
   ```
   
   Edit `config.json` to update your Gemini API key:
   ```json
   [
     {
       "model": "gemini-2.0-flash",
       "api_key": "add-your-api-key",
       "base_url": "https://generativelanguage.googleapis.com/v1beta",
       "api_type": "google"
     }
   ]
   ```

   > **Note**: For Gmail SMTP, you'll need to generate an App Password. Go to your Google Account > Security > 2-Step Verification > App passwords.

5. Run the application:
   ```bash
   python app.py
   ```

6. Access the web interface in your browser:
   ```
   http://localhost:5000
   ```

## Usage

1. **Configure Agents**: Create and configure multiple agents with different roles and capabilities
2. **Set Initial Requirements**: Provide the initial message describing your requirements
3. **Monitor Conversations**: Watch the agents collaborate in real-time to solve your problem
4. **Review and Send Emails**: Generate AI-crafted emails and send them to recipients

## Example Use Cases

- **Healthcare Communication**: Generate personalized patient notifications based on health summaries
- **Software Development**: Create multi-agent teams to design, code, and test software
- **Content Creation**: Deploy agents to brainstorm, draft, and refine content
- **Business Analysis**: Use agents to analyze data and generate reports

## Troubleshooting

- If you encounter API errors, verify your Gemini API key is correct
- For SMTP issues, ensure you're using an app password if you have 2FA enabled on Gmail
- If agent initialization fails, make sure you've installed `google-generativeai` and `vertexai` packages

## Acknowledgements

- This project uses [AutoGen](https://github.com/microsoft/autogen) by Microsoft
- Powered by Google's Gemini 2.0 Flash model
