from decimal import Decimal

from django.db.models import Sum
from django.utils import timezone

from .models import Budget, Expense


def budget_alerts(request):
    if not request.user.is_authenticated:
        return {
            'overspent_categories_count': 0,
            'has_overspend_alert': False,
        }

    current_month_start = timezone.localdate().replace(day=1)

    monthly_expenses = Expense.objects.filter(
        user=request.user,
        date__year=current_month_start.year,
        date__month=current_month_start.month,
    )
    spent_by_category = {
        row['category_id']: row['spent'] or Decimal('0.00')
        for row in monthly_expenses.values('category_id').annotate(spent=Sum('amount'))
    }

    monthly_budgets = Budget.objects.filter(user=request.user, month=current_month_start)
    overspent_categories_count = sum(
        1
        for budget in monthly_budgets
        if spent_by_category.get(budget.category_id, Decimal('0.00')) > budget.amount
    )

    return {
        'overspent_categories_count': overspent_categories_count,
        'has_overspend_alert': overspent_categories_count > 0,
    }
