from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator
from django.db.models import Q

User = settings.AUTH_USER_MODEL


class CustomCategory(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="categories")
    name = models.CharField(max_length=50)
    icon = models.CharField(max_length=10, default='📦')

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['user', 'name'], name='unique_user_category')
        ]

    def __str__(self):
        return f"{self.icon} {self.name}"


class Budget(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="budgets")
    category = models.ForeignKey(CustomCategory, on_delete=models.CASCADE, related_name="budgets")
    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)]
    )
    month = models.DateField()   # ✅ better than CharField

    def __str__(self):
        return f"{self.user} - {self.category.name} - ₹{self.amount}"


class MonthlyBudget(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="monthly_budgets")
    month = models.DateField()
    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)]
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['user', 'month'], name='unique_user_monthly_budget')
        ]

    def __str__(self):
        return f"{self.user} - {self.month.strftime('%b %Y')} - ₹{self.amount}"


class Expense(models.Model):
    CASH = 'cash'
    ONLINE = 'online'
    PAYMENT_TYPE_CHOICES = [
        (CASH, 'Cash'),
        (ONLINE, 'Online'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="expenses")
    category = models.ForeignKey(CustomCategory, on_delete=models.CASCADE, related_name="expenses")
    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)]
    )
    date = models.DateField()
    description = models.TextField(blank=True)
    payment_type = models.CharField(max_length=10, choices=PAYMENT_TYPE_CHOICES, default=CASH)
    note = models.TextField(blank=True)
    source_recurring = models.ForeignKey(
        'RecurringExpense',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='generated_expenses'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['source_recurring', 'date'],
                condition=Q(source_recurring__isnull=False),
                name='unique_generated_recurring_expense_per_day',
            )
        ]

    def __str__(self):
        return f"{self.category.name} - ₹{self.amount}"


class RecurringExpense(models.Model):
    DAILY = 'daily'
    WEEKLY = 'weekly'
    MONTHLY = 'monthly'
    FREQUENCY_CHOICES = [
        (DAILY, 'Daily'),
        (WEEKLY, 'Weekly'),
        (MONTHLY, 'Monthly'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='recurring_expenses')
    category = models.ForeignKey(CustomCategory, on_delete=models.CASCADE, related_name='recurring_rules')
    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)]
    )
    note = models.TextField(blank=True)
    payment_type = models.CharField(max_length=10, choices=Expense.PAYMENT_TYPE_CHOICES, default=Expense.CASH)
    frequency = models.CharField(max_length=10, choices=FREQUENCY_CHOICES)
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    next_run_date = models.DateField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.category.name} - ₹{self.amount} ({self.frequency})"