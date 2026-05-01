# Service Booking System

A multi-role Django web application for managing home and appliance service bookings with role-specific workflows.

## Project Overview

This project is designed around a practical service business model with:

- Multi-role architecture for Admin, Staff, and Customer users
- Responsive mobile-first interface
- Booking lifecycle management and dashboard analytics

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

- Backend: Django (Python)
- Frontend: HTML5, CSS3, JavaScript
- Database: MySQL/MariaDB (phpMyAdmin/XAMPP)
- Auth: Django authentication with custom role model

## Quick Start

Run commands are documented in `quickstart.md`.

## Roadmap

- Payment integration (Stripe/Razorpay)
- Location-based service validation
- Real-time notifications