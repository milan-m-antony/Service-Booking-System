# Quick Start Guide

## Local Development

### 1. Activate virtual environment
```powershell
.\.venv\Scripts\Activate.ps1
```

### 2. Install dependencies
```powershell
python -m pip install -r requirements.txt
```

### 3. Set up environment variables
Copy `.env.example` to `.env` and update with your local or remote database:
```powershell
cp .env.example .env
```

Edit `.env`:
```env
# For local MySQL (XAMPP):
DATABASE_URL=mysql://root@127.0.0.1:3306/Service-Booking-System

# For TiDB Cloud:
DATABASE_URL=mysql://user:password@gateway.region.prod.aws.tidbcloud.com:4000/myapp_db?ssl=true

DEBUG=true
ALLOWED_HOSTS=localhost,127.0.0.1
CSRF_TRUSTED_ORIGINS=http://localhost:8000,http://127.0.0.1:8000
```

### 4. Apply migrations
```powershell
python manage.py migrate
```

### 5. Run development server
```powershell
python manage.py runserver
```

### 6. Open in browser
```
http://127.0.0.1:8000/
```

### 7. Access admin panel
```
http://127.0.0.1:8000/admin
```

---

## Production Deployment (Render + TiDB Cloud)

### Quick Deployment Checklist

- [ ] Code committed and pushed to GitHub `main` branch
- [ ] `.env.example` exists in repo (do NOT commit `.env`)
- [ ] TiDB Cloud instance created with public endpoint enabled
- [ ] IP allowlist configured in TiDB Cloud
- [ ] Render Web Service created and connected to GitHub
- [ ] Environment variables set in Render dashboard

### Environment Variables for Render

Set these in Render → Settings → Environment:

```
DATABASE_URL=mysql://user:password@gateway.region.prod.aws.tidbcloud.com:4000/database?ssl=true
SECRET_KEY=<generated-secret-key>
DEBUG=false
ALLOWED_HOSTS=your-domain.com,localhost,127.0.0.1
CSRF_TRUSTED_ORIGINS=https://your-domain.com,http://localhost:8000,http://127.0.0.1:8000
```

### Viewing Logs

In Render dashboard → Web Service → Logs:
- Build logs: Shows `pip install`, `migrate`, `collectstatic` progress
- Runtime logs: Shows Gunicorn startup and HTTP requests

### Common Issues

| Issue | Solution |
|-------|----------|
| 500 error on `/` | Check database connection; verify `DATABASE_URL` and TiDB credentials |
| Static files 404 | Clear browser cache; check Render build logs for `collectstatic` errors |
| Favicon 404 | Same as above; WhiteNoise should serve `/static/` files |
| Connection timeout | Verify TiDB IP allowlist; Render may use different IP each deploy |

### Database Migrations

- **Free tier**: Migrations run automatically during build phase (defined in `render.yaml`)
- **Paid tier**: Can use `releaseCommand` for isolated migration execution
- **Manual**: SSH into Render and run `python manage.py migrate --no-input`

### Redeploy

Push a new commit to trigger auto-deploy:
```bash
git add .
git commit -m "Fix: <description>"
git push origin main
```

Or manually redeploy in Render → Deploys → Latest → Redeploy

---

## Database Management

### Using SQLTools in VS Code (Optional)

1. Install SQLTools extension
2. `.vscode/settings.json` is pre-configured for TiDB Cloud
3. Connect and browse tables, run queries

### Backup & Restore

TiDB Cloud provides:
- Automatic backups (check TiDB console)
- Manual backup export via Data Import/Export

---

## Additional Commands

### Create superuser (admin account)
```powershell
python manage.py createsuperuser
```

### Collect static files manually
```powershell
python manage.py collectstatic --no-input --clear
```

### Check Django system status
```powershell
python manage.py check
```

### Reset database (WARNING: deletes all data)
```powershell
python manage.py flush
```

---

## Testing

### Run tests (if defined)
```powershell
python manage.py test
```

### Test database connection
```powershell
python manage.py dbshell
```

---

## Next Steps

- [ ] Customize admin panel branding
- [ ] Add payment gateway integration
- [ ] Set up monitoring/alerting on Render
- [ ] Configure AWS S3 for media uploads
- [ ] Enable HTTPS custom domain (Render auto-provides HTTPS)
