from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth.models import User
from django.db.models import Sum, Q
from django.utils import timezone
from datetime import datetime
from django.http import HttpResponse
from django.db.models.functions import TruncMonth
from decimal import Decimal, InvalidOperation
import calendar

import json
import csv

from .models import Expense, Budget, CustomCategory, MonthlyBudget


# ---------------- AUTH ---------------- #

def _expense_date_bounds():
    today = timezone.localdate()
    min_date = today.replace(day=1)
    last_day = calendar.monthrange(today.year, today.month)[1]
    max_date = today.replace(day=min(30, last_day))
    return min_date, max_date


def _validate_expense_date(date_input):
    min_date, max_date = _expense_date_bounds()
    try:
        selected_date = datetime.strptime(date_input, '%Y-%m-%d').date()
    except (TypeError, ValueError):
        return None, 'Please select a valid date.'

    if selected_date < min_date or selected_date > max_date:
        return None, f'Date must be between {min_date} and {max_date}.'

    return selected_date, None


def _parse_month_input(month_input):
    try:
        return datetime.strptime(month_input, '%Y-%m').date().replace(day=1), None
    except ValueError:
        return None, 'Please select a valid month.'

def signup(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Account created!')
            return redirect('login')
    else:
        form = UserCreationForm()
    return render(request, 'expenses/signup.html', {'form': form})


def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        identifier = (request.POST.get('username') or '').strip()
        password = request.POST.get('password') or ''

        if not identifier or not password:
            messages.error(request, 'Username/Email aur password dono required hain.')
            return render(request, 'expenses/login.html')

        username = identifier
        if '@' in identifier:
            user_by_email = User.objects.filter(email__iexact=identifier).only('username').first()
            if user_by_email:
                username = user_by_email.username

        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('dashboard')

        messages.error(request, 'Invalid credentials. Username/Email ya password galat hai.')

    return render(request, 'expenses/login.html')


def logout_view(request):
    logout(request)
    return redirect('login')


# ---------------- DASHBOARD ---------------- #

@login_required
def dashboard(request):
    all_user_expenses = Expense.objects.filter(user=request.user)
    expenses = all_user_expenses.select_related('category').order_by('-date')[:10]
    total_expense = all_user_expenses.aggregate(Sum('amount'))['amount__sum'] or Decimal('0.00')

    current_month_start = timezone.localdate().replace(day=1)
    monthly_expenses_qs = all_user_expenses.filter(
        date__year=current_month_start.year,
        date__month=current_month_start.month,
    )
    monthly_actual = monthly_expenses_qs.aggregate(Sum('amount'))['amount__sum'] or Decimal('0.00')

    monthly_budgets_qs = Budget.objects.filter(user=request.user, month=current_month_start).select_related('category')
    monthly_budget = monthly_budgets_qs.aggregate(Sum('amount'))['amount__sum'] or Decimal('0.00')

    spent_by_category = {
        row['category_id']: row['spent'] or Decimal('0.00')
        for row in monthly_expenses_qs.values('category_id').annotate(spent=Sum('amount'))
    }

    budget_vs_actual = []
    for budget_row in monthly_budgets_qs:
        spent = spent_by_category.get(budget_row.category_id, Decimal('0.00'))
        remaining = budget_row.amount - spent
        budget_vs_actual.append({
            'category': budget_row.category,
            'budget': budget_row.amount,
            'spent': spent,
            'remaining': remaining,
            'is_overspent': spent > budget_row.amount,
        })

    is_overspent = monthly_budget > Decimal('0.00') and monthly_actual > monthly_budget
    monthly_remaining = monthly_budget - monthly_actual
    ai_insights = analyze_expense(all_user_expenses)

    monthly_budget_obj = MonthlyBudget.objects.filter(user=request.user, month=current_month_start).first()
    pocket_monthly_budget = monthly_budget_obj.amount if monthly_budget_obj else Decimal('0.00')
    has_monthly_budget = monthly_budget_obj is not None
    daily_limit = (pocket_monthly_budget / Decimal('30')) if pocket_monthly_budget > Decimal('0.00') else Decimal('0.00')

    today = timezone.localdate()
    today_expense = all_user_expenses.filter(date=today).aggregate(Sum('amount'))['amount__sum'] or Decimal('0.00')
    pocket_remaining = pocket_monthly_budget - monthly_actual
    daily_over_amount = today_expense - daily_limit
    is_daily_over = daily_limit > Decimal('0.00') and today_expense > daily_limit
    if daily_limit > Decimal('0.00'):
        daily_usage_percent = (today_expense / daily_limit) * Decimal('100')
    else:
        daily_usage_percent = Decimal('0.00')
    daily_usage_percent_capped = min(daily_usage_percent, Decimal('100.00'))

    if daily_limit == Decimal('0.00'):
        daily_status_message = 'Aaj ka daily limit dekhne ke liye monthly budget set karo.'
    elif is_daily_over:
        daily_status_message = f'❌ Aaj ₹{daily_over_amount:.2f} zyada kharch hua.'
    else:
        daily_status_message = '✅ Aap limit ke andar ho. Good job!'

    if daily_limit > Decimal('0.00') and is_daily_over:
        pocket_ai_message = 'Kal thoda kam kharch karo.'
    elif daily_limit > Decimal('0.00'):
        pocket_ai_message = 'Great! Aap save kar rahe ho.'
    else:
        pocket_ai_message = 'Pocket AI suggestion ke liye monthly budget set karo.'

    return render(request, 'expenses/dashboard.html', {
        'expenses': expenses,
        'total_expense': total_expense,
        'current_month_label': current_month_start.strftime('%B %Y'),
        'monthly_budget': monthly_budget,
        'monthly_actual': monthly_actual,
        'monthly_remaining': monthly_remaining,
        'is_overspent': is_overspent,
        'budget_vs_actual': budget_vs_actual,
        'ai_insights': ai_insights,
        'pocket_monthly_budget': pocket_monthly_budget,
        'has_monthly_budget': has_monthly_budget,
        'daily_limit': daily_limit,
        'today_expense': today_expense,
        'pocket_remaining': pocket_remaining,
        'is_daily_over': is_daily_over,
        'daily_status_message': daily_status_message,
        'pocket_ai_message': pocket_ai_message,
        'daily_usage_percent': daily_usage_percent,
        'daily_usage_percent_capped': daily_usage_percent_capped,
    })


# ---------------- ADD EXPENSE ---------------- #

@login_required
def add_expense(request):
    categories = CustomCategory.objects.filter(user=request.user)
    min_date, max_date = _expense_date_bounds()

    if request.method == 'POST':
        amount = request.POST.get('amount')
        category_id = request.POST.get('category')
        date_input = request.POST.get('date')
        note = request.POST.get('note', '')
        selected_date, date_error = _validate_expense_date(date_input)

        if date_error:
            messages.error(request, date_error)
            return render(request, 'expenses/add_expense.html', {
                'categories': categories,
                'min_date': min_date,
                'max_date': max_date,
                'form_data': request.POST,
            })

        category = get_object_or_404(CustomCategory, id=category_id, user=request.user)

        Expense.objects.create(
            user=request.user,
            amount=amount,
            category=category,
            date=selected_date,
            note=note
        )

        current_month_start = selected_date.replace(day=1)
        monthly_budget_obj = MonthlyBudget.objects.filter(user=request.user, month=current_month_start).first()
        if monthly_budget_obj:
            daily_limit = monthly_budget_obj.amount / Decimal('30')
            today_expense = Expense.objects.filter(user=request.user, date=selected_date).aggregate(Sum('amount'))['amount__sum'] or Decimal('0.00')
            if today_expense > daily_limit:
                over_amount = today_expense - daily_limit
                messages.warning(request, f'❌ Aaj ₹{over_amount:.2f} zyada kharch hua.')
            else:
                messages.success(request, '✅ Aap daily limit ke andar ho. Good job!')

        messages.success(request, 'Expense added successfully!')
        return redirect('dashboard')

    return render(request, 'expenses/add_expense.html', {
        'categories': categories,
        'min_date': min_date,
        'max_date': max_date,
    })


# ---------------- REPORT ---------------- #

@login_required
def report(request):
    expenses = Expense.objects.filter(user=request.user)
    total_expense = expenses.aggregate(Sum('amount'))['amount__sum'] or Decimal('0.00')

    category_data = expenses.values('category__name').annotate(total=Sum('amount'))
    pie_data = [
        {
            'category': item['category__name'],
            'total': float(item['total'] or 0),
        }
        for item in category_data
    ]

    monthly_data = expenses.annotate(
        month=TruncMonth('date')
    ).values('month').annotate(total=Sum('amount')).order_by('month')
    monthly_chart_data = [
        {
            'month': item['month'].strftime('%b %Y') if item['month'] else '',
            'total': float(item['total'] or 0),
        }
        for item in monthly_data
    ]

    ai_insights = analyze_expense(expenses)
    total_categories_used = category_data.count()
    latest_month_total = monthly_chart_data[-1]['total'] if monthly_chart_data else 0

    return render(request, 'expenses/report.html', {
        'pie_data': json.dumps(pie_data),
        'monthly_data': json.dumps(monthly_chart_data),
        'ai_insights': ai_insights,
        'total_expense': total_expense,
        'total_categories_used': total_categories_used,
        'latest_month_total': latest_month_total,
        'months_tracked': len(monthly_chart_data),
    })


# ---------------- EDIT ---------------- #

@login_required
def edit_expense(request, id):
    expense = get_object_or_404(Expense, id=id, user=request.user)
    categories = CustomCategory.objects.filter(user=request.user)
    min_date, max_date = _expense_date_bounds()

    if request.method == 'POST':
        expense.amount = request.POST.get('amount')
        date_input = request.POST.get('date')
        selected_date, date_error = _validate_expense_date(date_input)
        if date_error:
            messages.error(request, date_error)
            return render(request, 'expenses/edit_expense.html', {
                'expense': expense,
                'categories': categories,
                'min_date': min_date,
                'max_date': max_date,
            })

        expense.date = selected_date
        expense.note = request.POST.get('note', '')

        category_id = request.POST.get('category')
        expense.category = get_object_or_404(CustomCategory, id=category_id, user=request.user)

        expense.save()
        messages.success(request, 'Expense updated!')
        return redirect('dashboard')

    return render(request, 'expenses/edit_expense.html', {
        'expense': expense,
        'categories': categories,
        'min_date': min_date,
        'max_date': max_date,
    })


# ---------------- DELETE ---------------- #

@login_required
def delete_expense(request, id):
    expense = get_object_or_404(Expense, id=id, user=request.user)
    expense.delete()
    messages.success(request, 'Expense deleted!')
    return redirect('dashboard')


# ---------------- SEARCH ---------------- #

@login_required
def search_expenses(request):
    query = request.GET.get('q', '').strip()
    category_id = request.GET.get('category', '').strip()
    start_date = request.GET.get('start_date', '').strip()
    end_date = request.GET.get('end_date', '').strip()

    categories = CustomCategory.objects.filter(user=request.user).order_by('name')

    expenses = Expense.objects.filter(user=request.user).select_related('category').order_by('-date', '-created_at')

    if query:
        search_filter = (
            Q(note__icontains=query) |
            Q(category__name__icontains=query)
        )
        try:
            search_filter |= Q(amount=Decimal(query))
        except (InvalidOperation, ValueError):
            pass
        if len(query) == 10 and query.count('-') == 2:
            search_filter |= Q(date=query)

        expenses = expenses.filter(search_filter)

    if category_id.isdigit():
        expenses = expenses.filter(category_id=int(category_id))

    if start_date:
        try:
            expenses = expenses.filter(date__gte=datetime.strptime(start_date, '%Y-%m-%d').date())
        except ValueError:
            messages.error(request, 'Invalid start date format.')

    if end_date:
        try:
            expenses = expenses.filter(date__lte=datetime.strptime(end_date, '%Y-%m-%d').date())
        except ValueError:
            messages.error(request, 'Invalid end date format.')

    return render(request, 'expenses/search.html', {
        'expenses': expenses,
        'query': query,
        'categories': categories,
        'selected_category': category_id,
        'start_date': start_date,
        'end_date': end_date,
    })


# ---------------- EXPORT CSV ---------------- #

@login_required
def export_csv(request):
    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = 'attachment; filename="expenses.csv"'
    response.write('\ufeff')

    writer = csv.writer(response)
    writer.writerow(['S.No', 'Date', 'Category', 'Amount (INR)', 'Note'])

    expenses = Expense.objects.filter(user=request.user).select_related('category').order_by('-date', '-created_at')

    for index, expense in enumerate(expenses, start=1):
        writer.writerow([
            index,
            expense.date.strftime('%d-%m-%Y'),
            f"{expense.category.icon} {expense.category.name}",
            format(expense.amount, '.2f'),
            expense.note,
        ])

    return response


# ---------------- CATEGORY ---------------- #

@login_required
def manage_categories(request):
    categories = CustomCategory.objects.filter(user=request.user)

    if request.method == 'POST':
        name = request.POST.get('name')

        CustomCategory.objects.create(
            user=request.user,
            name=name
        )
        messages.success(request, f'{name} category created!')
        return redirect('manage_categories')

    return render(request, 'expenses/manage_categories.html', {'categories': categories})


@login_required
def delete_category(request, id):
    cat = get_object_or_404(CustomCategory, id=id, user=request.user)
    cat.delete()
    messages.success(request, 'Category deleted!')
    return redirect('manage_categories')


# ---------------- BUDGET ---------------- #

@login_required
def set_budget(request):
    categories = CustomCategory.objects.filter(user=request.user)
    budgets = Budget.objects.filter(user=request.user).select_related('category').order_by('-month')
    monthly_budgets = MonthlyBudget.objects.filter(user=request.user).order_by('-month')
    monthly_budget_rows = [
        {
            'id': row.id,
            'month': row.month,
            'amount': row.amount,
            'daily_limit': row.amount / Decimal('30'),
        }
        for row in monthly_budgets
    ]
    default_month = timezone.localdate().strftime('%Y-%m')
    current_month_start = timezone.localdate().replace(day=1)
    current_month_budget = monthly_budgets.filter(month=current_month_start).first()
    current_month_daily_limit = (current_month_budget.amount / Decimal('30')) if current_month_budget else Decimal('0.00')
    current_month_category_total = budgets.filter(month=current_month_start).aggregate(Sum('amount'))['amount__sum'] or Decimal('0.00')
    monthly_unallocated = (current_month_budget.amount - current_month_category_total) if current_month_budget else Decimal('0.00')

    monthly_form_month = request.GET.get('monthly_month', default_month)
    monthly_form_amount = request.GET.get('monthly_amount', '')
    category_form_id = request.GET.get('category_id', '')
    category_form_month = request.GET.get('category_month', default_month)
    category_form_amount = request.GET.get('category_amount', '')

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'set_monthly_budget':
            amount = request.POST.get('monthly_amount')
            month_input = request.POST.get('monthly_month', '')
            month, month_error = _parse_month_input(month_input)
            if month_error:
                messages.error(request, month_error)
            else:
                MonthlyBudget.objects.update_or_create(
                    user=request.user,
                    month=month,
                    defaults={'amount': amount}
                )
                messages.success(request, 'Monthly budget set successfully!')

        elif action == 'delete_monthly_budget':
            monthly_budget_id = request.POST.get('monthly_budget_id')
            monthly_budget = get_object_or_404(MonthlyBudget, id=monthly_budget_id, user=request.user)
            monthly_budget.delete()
            messages.success(request, 'Monthly budget deleted successfully!')

        elif action == 'delete_category_budget':
            category_budget_id = request.POST.get('category_budget_id')
            category_budget = get_object_or_404(Budget, id=category_budget_id, user=request.user)
            category_budget.delete()
            messages.success(request, 'Category budget deleted successfully!')

        else:
            category_id = request.POST.get('category')
            amount = request.POST.get('amount')
            month_input = request.POST.get('month', '')

            category = get_object_or_404(CustomCategory, id=category_id, user=request.user)
            month, month_error = _parse_month_input(month_input)

            if month_error:
                messages.error(request, month_error)
                return render(request, 'expenses/set_budget.html', {
                    'categories': categories,
                    'budgets': budgets,
                    'monthly_budgets': monthly_budgets,
                    'monthly_budget_rows': monthly_budget_rows,
                    'default_month': default_month,
                    'current_month_budget': current_month_budget,
                    'current_month_daily_limit': current_month_daily_limit,
                    'monthly_form_month': monthly_form_month,
                    'monthly_form_amount': monthly_form_amount,
                    'category_form_id': category_form_id,
                    'category_form_month': category_form_month,
                    'category_form_amount': category_form_amount,
                    'current_month_category_total': current_month_category_total,
                    'monthly_unallocated': monthly_unallocated,
                })

            Budget.objects.update_or_create(
                user=request.user,
                category=category,
                month=month,
                defaults={'amount': amount}
            )

            messages.success(request, 'Category budget set successfully!')

        return redirect('set_budget')

    return render(request, 'expenses/set_budget.html', {
        'categories': categories,
        'budgets': budgets,
        'monthly_budgets': monthly_budgets,
        'monthly_budget_rows': monthly_budget_rows,
        'default_month': default_month,
        'current_month_budget': current_month_budget,
        'current_month_daily_limit': current_month_daily_limit,
        'monthly_form_month': monthly_form_month,
        'monthly_form_amount': monthly_form_amount,
        'category_form_id': category_form_id,
        'category_form_month': category_form_month,
        'category_form_amount': category_form_amount,
        'current_month_category_total': current_month_category_total,
        'monthly_unallocated': monthly_unallocated,
    })


# ---------------- AI ---------------- #

def analyze_expense(expenses):
    if not expenses.exists():
        return ["ℹ️ Abhi tak expense data nahi hai. Expense add karoge to AI advice dikhega."]

    max_category = expenses.values('category__name').annotate(total=Sum('amount')).order_by('-total').first()

    return [
        f"⚠️ Tumhara sabse zyada kharcha {max_category['category__name']} me ho raha hai.",
        "💡 Suggestion: Is category ka monthly budget 10% increase karo ya spending limit set karo.",
    ]