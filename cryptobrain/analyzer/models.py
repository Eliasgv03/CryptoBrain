from django.db import models
from django.utils import timezone

class BitcoinPriceHistory(models.Model):
    timestamp = models.DateTimeField()
    price = models.DecimalField(max_digits=15, decimal_places=2)
    volume_24h = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)

    class Meta:
        indexes = [models.Index(fields=['timestamp'])]

    def __str__(self):
        return f"{self.timestamp} - ${self.price}"

class BitcoinNews(models.Model):
    title = models.CharField(max_length=200)
    source = models.CharField(max_length=100, null=True, blank=True)
    published_at = models.DateTimeField()
    url = models.URLField(unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title

class AnalysisCache(models.Model):
    sentiment_response = models.JSONField()
    trend_response = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Analysis cache from {self.created_at.strftime('%Y-%m-%d %H:%M:%S')}"