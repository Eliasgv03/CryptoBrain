from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.prompts import PromptTemplate
from langchain.output_parsers import PydanticOutputParser
from pydantic import BaseModel, Field
import os
import logging
from dotenv import load_dotenv
from google.api_core.exceptions import ResourceExhausted, GoogleAPICallError
from .processor import preprocess_news_titles

# Configure logger
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# --- LLM Initialization ---
try:
    gemini_api_key = os.getenv("GEMINI_API_KEY")
    if not gemini_api_key:
        logger.critical("GEMINI_API_KEY not found in environment variables. The AI agent cannot function.")
        llm = None
    else:
        llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash", api_key=gemini_api_key, temperature=0.7)
        logger.info("Google Generative AI LLM initialized successfully.")
except Exception as e:
    logger.critical(f"Failed to initialize Google Generative AI LLM: {e}", exc_info=True)
    llm = None

class APIQuotaExceededError(Exception):
    """Custom exception for API quota errors."""
    pass

class ComprehensiveAnalysis(BaseModel):
    """A comprehensive analysis of the Bitcoin market."""
    market_sentiment: str = Field(description="Overall market sentiment (e.g., 'Bullish', 'Bearish', 'Neutral', 'Cautiously Optimistic').")
    trend_prediction: str = Field(description="Predicted trend for the next 24-48 hours (e.g., 'Uptrend', 'Downtrend', 'Sideways').")
    confidence_score: float = Field(description="Confidence in the prediction, from 0.0 (low) to 1.0 (high).")
    analysis_summary: str = Field(description="A concise summary of the key drivers for the sentiment and trend.")
    detailed_reasoning: str = Field(description="A detailed, multi-point reasoning for the analysis, synthesizing news and technical indicators.")

parser = PydanticOutputParser(pydantic_object=ComprehensiveAnalysis)

prompt = PromptTemplate(
    input_variables=["news_titles", "price_trend_description", "moving_average", "current_price", "volume_24h"],
    template="""As an expert financial analyst, provide a comprehensive analysis of the Bitcoin market.

    **Instructions:**
    1.  **Analyze the provided data:** Synthesize the news headlines and technical indicators.
    2.  **Determine Sentiment and Trend:** Assess the overall market sentiment and predict the price trend for the next 24-48 hours.
    3.  **Provide a Confidence Score:** Rate your confidence in this prediction on a scale of 0.0 to 1.0.
    4.  **Deliver a Detailed Report:** Explain your reasoning clearly, referencing specific news and data points.

    **Input Data:**
    -   **Current Price:** ${current_price:,.2f}
    -   **24h Trading Volume:** ${volume_24h:,.2f}
    -   **Price Trend:** {price_trend_description}
    -   **7-Day Moving Average:** ${moving_average:,.2f}
    -   **Recent News Headlines:**
        {news_titles}

    **Output Format:**
    {format_instructions}
    """,
    partial_variables={"format_instructions": parser.get_format_instructions()}
)

class AgentCoordinator:
    def __init__(self, llm):
        self.llm = llm

    async def get_comprehensive_analysis(self, news_titles, price_trend, moving_average, current_price, volume_24h):
        """Performs a comprehensive analysis of the market."""
        if not self.llm:
            logger.error("LLM is not initialized. Cannot perform analysis.")
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
            logger.info(f"Invoking AI chain with payload: {invoke_payload}")

            response = await chain.ainvoke(invoke_payload)
            
            logger.info(f"Received response from AI chain: {response}")
            return response.dict()
        except ResourceExhausted as e:
            logger.error(f"API Quota Exceeded: {e}", exc_info=True)
            raise APIQuotaExceededError("The analysis service is temporarily unavailable due to API quota limits.") from e
        except GoogleAPICallError as e:
            logger.error(f"A Google API call error occurred: {e}", exc_info=True)
            raise RuntimeError(f"An error occurred while communicating with the AI service: {e}") from e
        except Exception as e:
            logger.error(f"An unexpected error occurred in comprehensive analysis: {e}", exc_info=True)
            raise

agent_coordinator = AgentCoordinator(llm)