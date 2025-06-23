from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.prompts import PromptTemplate
from langchain.output_parsers import PydanticOutputParser
from pydantic import BaseModel, Field
import os
from dotenv import load_dotenv
import json

load_dotenv()
llm = ChatGoogleGenerativeAI(model="gemini-1.5-pro", api_key=os.getenv("GEMINI_API_KEY"), temperature=0.7)

# Modelos Pydantic para salida estructurada
class SentimentAnalysis(BaseModel):
    sentiment: str = Field(description="Sentiment (positive, negative, or neutral)")
    confidence: float = Field(description="Confidence score between 0 and 1")

class TrendPrediction(BaseModel):
    trend: str = Field(description="Trend prediction (bullish, bearish, or neutral)")
    confidence: float = Field(description="Confidence score between 0 and 1")
    reasoning: str = Field(description="Brief reasoning for the prediction")

# Prompts mejorados
sentiment_parser = PydanticOutputParser(pydantic_object=SentimentAnalysis)
sentiment_prompt = PromptTemplate(
    input_variables=["news_titles"],
    template="You are a financial analyst specializing in cryptocurrency. Analyze the sentiment of the following Bitcoin-related news headlines and return a structured JSON response. Use the format specified below. Headlines:\n{news_titles}\n{format_instructions}",
    partial_variables={"format_instructions": sentiment_parser.get_format_instructions()}
)

trend_parser = PydanticOutputParser(pydantic_object=TrendPrediction)
trend_prompt = PromptTemplate(
    input_variables=["news_titles", "price_trend", "moving_average"],
    template="You are a cryptocurrency market predictor. Based on the following Bitcoin news headlines, the current price trend ({price_trend}), and the 7-day moving average price ({moving_average}), predict the trend for the next 24-48 hours. Return a structured JSON response with trend, confidence score (0-1), and a brief reasoning. Headlines:\n{news_titles}\n{format_instructions}",
    partial_variables={"format_instructions": trend_parser.get_format_instructions()}
)

# Agentes
class AgentCoordinator:
    def __init__(self, llm):
        self.llm = llm

    async def analyze_sentiment(self, news_titles):
        try:
            chain = sentiment_prompt | self.llm | sentiment_parser
            response = await chain.ainvoke({"news_titles": "\n".join(preprocess_news_titles(news_titles))})
            return response.dict()
        except Exception as e:
            print(f"Error en análisis de sentimiento: {e}")
            return {"sentiment": "neutral", "confidence": 0.5}

    async def predict_trend(self, news_titles, price_trend, moving_average):
        try:
            chain = trend_prompt | self.llm | trend_parser
            response = await chain.ainvoke({
                "news_titles": "\n".join(preprocess_news_titles(news_titles)),
                "price_trend": price_trend["trend"],
                "moving_average": moving_average
            })
            return response.dict()
        except Exception as e:
            print(f"Error en predicción de tendencia: {e}")
            return {"trend": "neutral", "confidence": 0.5, "reasoning": "Error en predicción"}

# Instancia del coordinador
agent_coordinator = AgentCoordinator(llm)