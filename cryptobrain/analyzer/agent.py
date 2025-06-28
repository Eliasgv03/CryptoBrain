from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.prompts import PromptTemplate
from langchain.output_parsers import PydanticOutputParser
from pydantic import BaseModel, Field
import os
from dotenv import load_dotenv
from google.api_core.exceptions import ResourceExhausted, GoogleAPICallError
from .processor import preprocess_news_titles
from .prompts import ANALYSIS_PROMPT_TEMPLATE


load_dotenv()

try:
    gemini_api_key = os.getenv("GEMINI_API_KEY")
    if not gemini_api_key:
        raise ValueError("GEMINI_API_KEY not found in environment variables. The AI agent cannot function.")
    llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash", api_key=gemini_api_key, temperature=0.7)
except (ValueError, Exception) as e:
    llm = None

class APIQuotaExceededError(Exception):
    """Custom exception raised when the Google Generative AI API quota is exceeded."""
    pass

class ComprehensiveAnalysis(BaseModel):
    """
    Defines the data structure for a comprehensive Bitcoin market analysis.
    This Pydantic model ensures that the AI's output is structured and validated.
    """
    market_sentiment: str = Field(description="Overall market sentiment (e.g., 'Bullish', 'Bearish', 'Neutral', 'Cautiously Optimistic').")
    trend_prediction: str = Field(description="Predicted trend for the next 24-48 hours (e.g., 'Uptrend', 'Downtrend', 'Sideways').")
    confidence_score: float = Field(description="Confidence in the prediction, from 0.0 (low) to 1.0 (high).")
    analysis_summary: str = Field(description="A concise summary of the key drivers for the sentiment and trend.")
    detailed_reasoning: str = Field(description="A detailed, multi-point reasoning for the analysis, synthesizing news and technical indicators.")

parser = PydanticOutputParser(pydantic_object=ComprehensiveAnalysis)

prompt = PromptTemplate(
    input_variables=["news_titles", "price_trend_description", "moving_average", "current_price", "volume_24h"],
    template=ANALYSIS_PROMPT_TEMPLATE,
    partial_variables={"format_instructions": parser.get_format_instructions()},
)

class AgentOrchestrator:
    """
    Orchestrates the AI analysis process by integrating the language model,
    data processing, and prompt engineering components.
    """
    def __init__(self, llm):
        """
        Initializes the AgentOrchestrator.

        Args:
            llm: An instance of a LangChain compatible language model.
                 If None, analysis methods will raise an error.
        """
        self.llm = llm

    async def get_comprehensive_analysis(self, news_titles, price_trend, moving_average, current_price, volume_24h):
        """
        Performs a comprehensive market analysis by invoking the AI chain.

        This method preprocesses input data, formats it for the AI model,
        invokes the analysis chain, and returns the structured output.

        Args:
            news_titles (list[str]): A list of recent news headlines.
            price_trend (dict): A dictionary describing the price trend.
            moving_average (float): The 7-day moving average.
            current_price (float): The current Bitcoin price.
            volume_24h (float): The 24-hour trading volume.

        Returns:
            dict: A dictionary containing the structured market analysis,
                  conforming to the ComprehensiveAnalysis model.

        Raises:
            RuntimeError: If the LLM is not initialized or if an unexpected
                          API error occurs.
            APIQuotaExceededError: If the API call fails due to quota limits.
        """
        if not self.llm:
            raise RuntimeError("AI Agent is not configured. Check GEMINI_API_KEY.")

        try:
            chain = prompt | self.llm | parser
            processed_titles = preprocess_news_titles(news_titles)
            
            invoke_payload = {
                "news_titles": "\n".join([f"- {title}" for title in processed_titles]),
                "price_trend_description": price_trend.get("description", "Neutral"),
                "moving_average": moving_average,
                "current_price": current_price,
                "volume_24h": volume_24h
            }

            response = await chain.ainvoke(invoke_payload)
            return response.dict()
        except ResourceExhausted as e:
            raise APIQuotaExceededError("The analysis service is temporarily unavailable due to API quota limits.") from e
        except GoogleAPICallError as e:
            raise RuntimeError(f"An error occurred while communicating with the AI service: {e}") from e
        except Exception as e:
            raise RuntimeError(f"An unexpected error occurred in comprehensive analysis: {e}") from e


agent_orchestrator = AgentOrchestrator(llm)