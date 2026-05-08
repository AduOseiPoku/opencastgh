# OpenCastGH — Pay-to-Vote Platform

Ghana's award ceremony and talent show voting platform built with Django + Paystack.

---

## Quick Start (Local Development)

### 1. Clone & setup environment
```bash
cd opencastgh
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure environment
```bash
cp .env.example .env
# Edit .env with your Paystack test keys (get them from dashboard.paystack.com)
```

### 3. Run migrations & create superuser
```bash
python manage.py migrate
python manage.py createsuperuser
```

### 4. Run the development server
```bash
python manage.py runserver
```

Visit: http://localhost:8000
Admin: http://localhost:8000/admin

---

## Setting Up Your First Event (Admin Panel)

1. Go to **http://localhost:8000/admin**
2. Log in with your superuser credentials
3. Click **Events → Add Event**
   - Fill in event name, slug, description
   - **Set `price_per_vote`** — e.g. `1.00` for GHS 1 per vote
   - Set start and end dates
   - Check `is_active`
4. Click **Categories → Add Category**, link it to your event
5. Click **Nominees → Add Nominee**, link to a category
6. Visit the homepage — your event will appear live!

### Bundle Pricing (Optional)
To sell votes in bundles (e.g. 5 votes for GHS 4):
- Set `bundle_size = 5`
- Set `bundle_price = 4.00`

---

## Paystack Setup

1. Sign up at [paystack.com](https://paystack.com)
2. Go to **Settings → API Keys & Webhooks**
3. Copy your **Test Secret Key** and **Test Public Key** into `.env`
4. Set your **Webhook URL** to: `https://yourdomain.com/paystack/webhook/`
5. When ready for production, switch to **Live Keys**

---

## Project Structure

```
opencastgh/
├── opencastgh/
│   ├── settings.py          # All configuration
│   ├── urls.py              # Root URL routing
│   └── celery.py            # Celery configuration
├── voting/
│   ├── models.py            # Event, Category, Nominee, Transaction, Vote
│   ├── views.py             # All page and payment views
│   ├── urls.py              # App URL patterns
│   ├── admin.py             # Django admin configuration
│   ├── forms.py             # VoteForm
│   ├── paystack.py          # Paystack API service layer
│   ├── tasks.py             # Celery background tasks
│   └── templates/voting/    # All HTML templates
├── requirements.txt
├── .env.example
├── nginx.conf               # Production Nginx config
└── supervisor.conf          # Production process manager config
```

---

## Key URLs

| URL | Description |
|-----|-------------|
| `/` | Homepage — lists all events |
| `/event/<slug>/` | Event detail with all nominees |
| `/event/<slug>/nominee/<id>/` | Nominee detail + vote form |
| `/event/<slug>/results/` | Public results (if enabled) |
| `/paystack/webhook/` | Paystack webhook endpoint |
| `/admin/` | Django admin panel |

---

## Production Deployment (AWS/DigitalOcean)

### 1. Server setup
```bash
sudo apt update && sudo apt install python3-pip nginx supervisor postgresql redis-server -y
```

### 2. Clone project & install
```bash
git clone <your-repo> /home/ubuntu/opencastgh
cd /home/ubuntu/opencastgh
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
```

### 3. Configure production .env
```
DEBUG=False
DATABASE_URL=postgres://user:pass@localhost:5432/opencastgh
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com
SITE_URL=https://yourdomain.com
```

### 4. Collect static files
```bash
python manage.py collectstatic --no-input
python manage.py migrate
```

### 5. Configure Nginx & Supervisor
```bash
sudo cp nginx.conf /etc/nginx/sites-available/opencastgh
sudo ln -s /etc/nginx/sites-available/opencastgh /etc/nginx/sites-enabled/
sudo cp supervisor.conf /etc/supervisor/conf.d/opencastgh.conf
sudo supervisorctl reread && sudo supervisorctl update
```

### 6. SSL with Let's Encrypt
```bash
sudo apt install certbot python3-certbot-nginx -y
sudo certbot --nginx -d yourdomain.com
```

---

## Security Checklist Before Going Live

- [ ] `DEBUG=False` in production
- [ ] Strong `SECRET_KEY` (generate with: `python -c "import secrets; print(secrets.token_urlsafe(50))"`)
- [ ] SSL certificate installed
- [ ] Paystack webhook signature verification enabled (already in code)
- [ ] `.env` not committed to git (check `.gitignore`)
- [ ] PostgreSQL with strong password
- [ ] Daily database backups configured
- [ ] `ALLOWED_HOSTS` set to your domain only

---

## Adding Celery for Background Tasks

The `check_pending_transactions` task runs every 30 minutes to verify any payments that were interrupted.

Start Celery (requires Redis):
```bash
celery -A opencastgh worker --loglevel=info
celery -A opencastgh beat --loglevel=info
```

To add the schedule, paste the contents of `celery_beat_schedule.py` into `settings.py`.
