from django.contrib import admin
from .models import Expense, CustomCategory, Budget, MonthlyBudget


@admin.register(CustomCategory)
class CustomCategoryAdmin(admin.ModelAdmin):
    list_display = ['user', 'name']
    search_fields = ['user__username', 'name']


@admin.register(Budget)
class BudgetAdmin(admin.ModelAdmin):
    list_display = ['user', 'category', 'amount', 'month']
    list_filter = ['month', 'category']
    search_fields = ['user__username', 'category__name']


@admin.register(MonthlyBudget)
class MonthlyBudgetAdmin(admin.ModelAdmin):
    list_display = ['user', 'month', 'amount']
    list_filter = ['month']
    search_fields = ['user__username']

@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    list_display = ['user', 'amount', 'category', 'payment_type', 'date', 'description']
    list_filter = ['category', 'payment_type', 'date']
    search_fields = ['user__username', 'description', 'note']