set -e

pip install -r requirements.txt
cd expense_tracker
python manage.py collectstatic --noinput
python manage.py migrate