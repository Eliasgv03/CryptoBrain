from django.contrib import admin
from .models import BitcoinPriceHistory, BitcoinNews

@admin.register(BitcoinPriceHistory)
class BitcoinPriceHistoryAdmin(admin.ModelAdmin):
    list_display = ('timestamp', 'price', 'volume_24h')
    list_filter = ('timestamp',)
    search_fields = ('timestamp',)
    ordering = ('-timestamp',)

@admin.register(BitcoinNews)
class BitcoinNewsAdmin(admin.ModelAdmin):
    list_display = ('title', 'published_at', 'source')
    list_filter = ('published_at', 'source')
    search_fields = ('title', 'source')
    ordering = ('-published_at',)
