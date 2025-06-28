from django.db import models
from django.utils import timezone

class BitcoinPriceHistory(models.Model):
    """Stores historical price data for Bitcoin."""
    timestamp = models.DateTimeField()
    price = models.DecimalField(max_digits=15, decimal_places=2)
    volume_24h = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)

    class Meta:
        indexes = [models.Index(fields=['timestamp'])]

    def __str__(self):
        return f"{self.timestamp} - ${self.price}"

class BitcoinNews(models.Model):
    """Stores news articles related to Bitcoin, fetched from various sources."""
    title = models.CharField(max_length=200)
    source = models.CharField(max_length=100, null=True, blank=True)
    published_at = models.DateTimeField()
    url = models.URLField(unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title
