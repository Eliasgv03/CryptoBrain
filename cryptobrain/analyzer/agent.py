from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.prompts import PromptTemplate
from langchain.output_parsers import PydanticOutputParser
from pydantic import BaseModel, Field
import os
from dotenv import load_dotenv
from google.api_core.exceptions import ResourceExhausted

# Import the function from the processor
from .processor import preprocess_news_titles

load_dotenv()
llm = ChatGoogleGenerativeAI(model="gemini-1.5-pro", api_key=os.getenv("GEMINI_API_KEY"), temperature=0.7)

# Custom Exception
class APIQuotaExceededError(Exception):
    """Custom exception for API quota errors."""
    pass

# Pydantic models for structured output
class SentimentAnalysis(BaseModel):
    sentiment: str = Field(description="Sentiment (positive, negative, or neutral)")
    confidence: float = Field(description="Confidence score between 0 and 1")

class TrendPrediction(BaseModel):
    trend: str = Field(description="Trend prediction (bullish, bearish, or neutral)")
    confidence: float = Field(description="Confidence score between 0 and 1")
    reasoning: str = Field(description="Brief reasoning for the prediction")

# Parsers and Prompts
sentiment_parser = PydanticOutputParser(pydantic_object=SentimentAnalysis)
sentiment_prompt = PromptTemplate(
    input_variables=["news_titles"],
    template="""You are a financial analyst specializing in cryptocurrency. 
    Analyze the sentiment of the following Bitcoin-related news headlines and return a structured JSON response. 
    Use the format specified below. 
    Headlines:\n{news_titles}\n{format_instructions}""",
    partial_variables={"format_instructions": sentiment_parser.get_format_instructions()}
)

trend_parser = PydanticOutputParser(pydantic_object=TrendPrediction)
trend_prompt = PromptTemplate(
    input_variables=["news_titles", "price_trend_description", "moving_average"],
    template="""You are a cryptocurrency market predictor. 
    Based on the following Bitcoin news headlines, the current price trend description ('{price_trend_description}'), and the 7-day moving average price ({moving_average}), predict the trend for the next 24-48 hours. 
    Return a structured JSON response with trend, confidence score (0-1), and a brief reasoning. 
    Headlines:\n{news_titles}\n{format_instructions}""",
    partial_variables={"format_instructions": trend_parser.get_format_instructions()}
)

# Agent Coordinator
class AgentCoordinator:
    def __init__(self, llm):
        self.llm = llm

    async def analyze_sentiment(self, news_titles):
        """Analyzes the sentiment of news headlines."""
        try:
            chain = sentiment_prompt | self.llm | sentiment_parser
            processed_titles = preprocess_news_titles(news_titles)
            response = await chain.ainvoke({"news_titles": "\n".join(processed_titles)})
            return response.dict()
        except ResourceExhausted as e:
            print(f"API Quota Exceeded in sentiment analysis: {e}")
            raise APIQuotaExceededError("The sentiment analysis service is temporarily unavailable due to API quota limits.")
        except Exception as e:
            print(f"An unexpected error occurred in sentiment analysis: {e}")
            return {"sentiment": "neutral", "confidence": 0.5, "reasoning": "An unexpected error occurred."}

    async def predict_trend(self, news_titles, price_trend, moving_average):
        """Predicts the market trend based on news, price trend, and moving average."""
        try:
            chain = trend_prompt | self.llm | trend_parser
            processed_titles = preprocess_news_titles(news_titles)
            response = await chain.ainvoke({
                "news_titles": "\n".join(processed_titles),
                "price_trend_description": price_trend.get("description", "Neutral"),
                "moving_average": f"{moving_average:.2f}"
            })
            return response.dict()
        except ResourceExhausted as e:
            print(f"API Quota Exceeded in trend prediction: {e}")
            raise APIQuotaExceededError("The trend prediction service is temporarily unavailable due to API quota limits.")
        except Exception as e:
            print(f"An unexpected error occurred in trend prediction: {e}")
            return {"trend": "neutral", "confidence": 0.5, "reasoning": "An unexpected error occurred during prediction."}

# Singleton instance of the coordinator
agent_coordinator = AgentCoordinator(llm)