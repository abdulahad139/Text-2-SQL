from langchain_groq import ChatGroq
import os
class GroqClient:
    def __init__(self):
        self.llm = ChatGroq(
            model="llama3-8b-8192",
            temperature=0.5,
            api_key=os.getenv("GROQ_API_KEY")
        )
    def generate_sql(self,natural_language_query,schema_info):
         prompt = f"""
            Convert this natural language query to MySQL SQL: Query: "{natural_language_query}"
            
            Database schema: {schema_info}
            
            Rules:
            - Identify relevant tables automatically
            - Use JOINs when needed
            - Never suggest non-existent columns
            - Use ONLY standard SQL
            - Never add LIMIT unless specified
            - Return ONLY SQL, no explanations
            - give proper naming to the columns if there is no naming convention
            - Do not wrap in markdown or code blocks
            - Never include the natural language query in response
            
            """
         return self.llm.invoke(prompt).content
