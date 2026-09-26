from langchain_google_genai import ChatGoogleGenerativeAI

ChatGoogleGenerativeAI(
                model='gemini-3.5-flash-lite',
                google_api_key=api_key,
                temperature=1.0,
                retries=2,
            )