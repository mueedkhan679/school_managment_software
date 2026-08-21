# Step-by-Step Production Deployment Guide (Render.com & PostgreSQL)

This guide provides simple, step-by-step instructions to deploy your Django **School Management Software** to **Render.com** using a managed **PostgreSQL** database.

---

## 📋 Prerequisites
Before starting, ensure you have:
- A free account on [Render.com](https://render.com/).
- A free account on [GitHub.com](https://github.com/).
- [Git](https://git-scm.com/) installed on your computer.

---

## Step 1: Push Project to GitHub

1. Open your terminal in the project root directory (`school_project`).
2. Initialize Git (if not already done) and create your main branch:
   ```bash
   git init
   git branch -M main
   ```
3. Commit all project files:
   ```bash
   git add .
   git commit -m "Prepare Django project for Render deployment"
   ```
4. Create a new repository on GitHub (e.g. `school-management-system`).
5. Link your local repo to GitHub and push your code:
   ```bash
   git remote add origin https://github.com/YOUR_USERNAME/school-management-system.git
   git push -u origin main
   ```

---

## Step 2: Create a PostgreSQL Database on Render

1. Log into your [Render Dashboard](https://dashboard.render.com/).
2. Click **New +** in the top right corner and select **PostgreSQL**.
3. Fill out the database details:
   - **Name**: `school-db`
   - **Database**: `school_db`
   - **User**: `school_user`
   - **Region**: Choose the region closest to you (e.g. Frankfurt / Oregon / Singapore).
   - **Instance Type**: Select **Free** tier.
4. Click **Create Database**.
5. Once created, wait for the database status to show **Available**.
6. Copy the **Internal Database URL** (or **External Database URL**). You will need this in Step 4.

---

## Step 3: Create a Web Service on Render

1. From the Render Dashboard, click **New +** and select **Web Service**.
2. Select **Build and deploy from a Git repository**, then click **Next**.
3. Connect your GitHub account and select your repository (`school-management-system`).
4. Configure the Web Service settings:
   - **Name**: `school-management-app` (or any custom name)
   - **Language**: `Python 3`
   - **Region**: Select the **same region** as your database.
   - **Branch**: `main`
   - **Build Command**: `./build.sh`
   - **Start Command**: `gunicorn config.wsgi:application`
   - **Instance Type**: Select **Free** tier.

---

## Step 4: Configure Environment Variables

Scroll down to the **Environment Variables** section on Render (or click the **Environment** tab on your Web Service) and add the following keys:

| Key | Value / Instructions |
|---|---|
| `DATABASE_URL` | Paste the **Internal Database URL** copied from Step 2. |
| `SECRET_KEY` | Generate a random 50+ char string or use a secure secret key. |
| `DEBUG` | `False` |
| `ALLOWED_HOSTS` | `*` (or your Render URL like `school-management-app.onrender.com`) |
| `PYTHON_VERSION` | `3.11.9` |

Click **Save Changes**. Render will automatically trigger the initial build and deployment.

---

## Step 5: Create Initial Live Admin Superuser

Once your build completes and the deployment is live:

1. In your Render Web Service dashboard, click the **Shell** tab on the left sidebar.
2. Inside the live interactive web terminal, run:
   ```bash
   python manage.py createsuperuser
   ```
3. Enter your desired production username, email, and password.
4. Open your live application URL (e.g. `https://school-management-app.onrender.com/accounts/login/`).
5. Log in using your newly created superuser credentials.

---

## ⚡ Post-Deployment Checklist & Features Verification

- [x] **Static Assets**: CSS and JS files are compressed and served automatically via WhiteNoise.
- [x] **Database Persistence**: All student, teacher, fee, and attendance data is saved permanently in PostgreSQL.
- [x] **Universal Login**: Dynamic role redirection routes Admins, Teachers, and Students to their respective dashboards.
- [x] **SSL / HTTPS**: Render automatically provides a free SSL certificate (`https://`).
