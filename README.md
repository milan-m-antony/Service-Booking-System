# Service Booking System

A multi-role Django web application for managing home and appliance service bookings with role-specific workflows.

## Project Overview

This project is designed around a practical service business model with:

- Multi-role architecture for Admin, Staff, and Customer users
- Responsive mobile-first interface
- Booking lifecycle management and dashboard analytics
- Production-ready deployment to Render + TiDB Cloud

## User Roles

- Admin: Full system access, service/user management, analytics visibility
- Staff: Assigned bookings, status updates, daily workflow handling
- Customer: Service browsing, booking creation, booking history tracking

## Core Features

- Service and category management
- Validated booking creation flow
- Staff assignment and conflict prevention
- Role-based dashboards
- Booking status tracking
- Analytics views for bookings and service performance

## Tech Stack

- Backend: Django 4.2.30 (Python)
- Frontend: HTML5, CSS3, JavaScript (Bootstrap 5, Bootstrap Icons)
- Database: TiDB Cloud (MySQL-compatible, serverless)
- Auth: Django authentication with custom role model
- Static Files: WhiteNoise 6.7+ for production serving
- Server: Gunicorn + Render Platform

## Deployment

### Prerequisites
- Render account (free tier supported)
- TiDB Cloud account with database and IP allowlist configured
- Custom domain (optional) or use Render's default domain

### Environment Variables

Create a `.env` file in the project root (see `.env.example`):

```env
DATABASE_URL=mysql://user:password@gateway.region.prod.aws.tidbcloud.com:4000/database_name?ssl=true
SECRET_KEY=your-django-secret-key
DEBUG=false
ALLOWED_HOSTS=your-domain.com,localhost,127.0.0.1
CSRF_TRUSTED_ORIGINS=https://your-domain.com,http://localhost:8000,http://127.0.0.1:8000
```

### Deployment Steps

1. **Push to GitHub**: Ensure latest code is on `main` branch
   ```bash
   git push origin main
   ```

2. **Create Render Web Service**:
   - Go to https://render.com → Dashboard → New → Web Service
   - Connect your GitHub repository
   - Render will auto-detect `render.yaml`

3. **Set Environment Variables** in Render → Settings → Environment:
   - Copy all values from `.env` (except quotes)
   - Update `ALLOWED_HOSTS` and `CSRF_TRUSTED_ORIGINS` to match your domain

4. **Deploy**: Render auto-deploys on git push. Manual deploy available in Render dashboard.

### Build & Deployment Process

The `render.yaml` file defines three commands:
- **buildCommand**: Installs dependencies, runs migrations, collects static files
- **startCommand**: Starts Gunicorn on port $PORT
- No release command (free-tier limitation; migrations run in build phase)

### Database Setup

- TiDB Cloud instance must have:
  - **Public Endpoint enabled**
  - **Network access rule**: Allow connections from `0.0.0.0 - 255.255.255.255` or specific Render IP range
  - **Database created** with name matching `DATABASE_URL`

- SSL/TLS is **required** by TiDB Cloud; `isrgrootx1.pem` (LetsEncrypt CA) is included in repo

### Static Files & Media

- **Static files** (CSS, JS, images): Served by WhiteNoise middleware; collected during build
- **Media files** (avatars, etc.): Stored in `media/` directory on Render's ephemeral filesystem (lost on redeploy)
  - **Recommended**: Configure AWS S3 for persistent media storage (see Optional section)

### Troubleshooting

**500 Error on homepage**:
- Check Render logs: `tail -f` build logs, look for database connection errors
- Verify `DATABASE_URL` format and TiDB credentials
- Ensure IP allowlist includes Render's IPs

**Favicon/Static files 404**:
- Clear browser cache
- Verify `collectstatic` ran in build logs
- Check `STATIC_URL` and `STATIC_ROOT` in settings

**Database migrations not running**:
- Free tier: Migrations run during `buildCommand` (included in `render.yaml`)
- Paid tier: Use `releaseCommand` for better isolation

## Optional: AWS S3 for Media Storage

1. Create S3 bucket and IAM credentials
2. Install `django-storages[boto3]`:
   ```bash
   pip install django-storages[boto3]
   ```
3. Add to `requirements.txt`
4. Set Render env vars:
   - `AWS_STORAGE_BUCKET_NAME`
   - `AWS_S3_REGION_NAME`
   - `AWS_ACCESS_KEY_ID`
   - `AWS_SECRET_ACCESS_KEY`
5. Update settings.py `DEFAULT_FILE_STORAGE` to use S3

## Local Development

See `quickstart.md` for local setup instructions.

## Roadmap

- Payment integration (Stripe/Razorpay)
- Location-based service validation
- Real-time notifications
- Media storage optimization