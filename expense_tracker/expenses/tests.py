from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.db import IntegrityError
from django.utils import timezone
from decimal import Decimal

from expenses.models import Expense, Budget, MonthlyBudget, CustomCategory, RecurringExpense

User = get_user_model()

class BudgetModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.category = CustomCategory.objects.create(user=self.user, name='Food', icon='🍔')
        self.month = timezone.now().date().replace(day=1)

    def test_budget_unique_together_constraint(self):
        # First budget should be created successfully
        Budget.objects.create(user=self.user, category=self.category, month=self.month, amount=Decimal('1000.00'))
        # Attempt to create a second budget with same user, category, month should raise IntegrityError
        with self.assertRaises(IntegrityError):
            Budget.objects.create(user=self.user, category=self.category, month=self.month, amount=Decimal('2000.00'))

class AddExpenseViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='expensetest', password='secret123')
        self.client.login(username='expensetest', password='secret123')
        self.category = CustomCategory.objects.create(user=self.user, name='Transport', icon='🚕')
        self.add_url = reverse('add_expense')

    def test_add_expense_successful(self):
        today = timezone.localdate()
        data = {
            'amount': '150.75',
            'category': str(self.category.id),
            'date': today.strftime('%Y-%m-%d'),
            'description': 'Uber ride',
            'payment_type': Expense.CASH,
            'is_recurring': '',
        }
        response = self.client.post(self.add_url, data, follow=True)
        self.assertRedirects(response, reverse('dashboard'))
        expense = Expense.objects.filter(user=self.user, description='Uber ride').first()
        self.assertIsNotNone(expense)
        self.assertEqual(expense.amount, Decimal('150.75'))
        self.assertEqual(expense.category, self.category)
        self.assertEqual(expense.date, today)
