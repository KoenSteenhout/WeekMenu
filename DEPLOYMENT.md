# 🚀 Deployment Guide - Streamlit Community Cloud

Follow these steps to deploy your Slim Weekmenu app to Streamlit Cloud.

## Step 1: Push Code to GitHub

Open Terminal and run these commands:

```bash
# Navigate to project directory
cd /Users/macbookpro/Documents/devProjects/WeekMenuPython

# Initialize git repository
git init

# Add all files
git add .

# Create first commit
git commit -m "Initial commit: Slim Weekmenu app

- Dutch weekly meal planner with Streamlit UI
- Smart recipe matching with vegetable focus
- PDF export and shopping list generation
- Co-authored-by: Claude Sonnet 4.5 <noreply@anthropic.com>"

# Add remote repository
git remote add origin https://github.com/KoenSteenhout/WeekMenu.git

# Push to GitHub
git push -u origin main
```

**If you get an error about `main` vs `master`:**
```bash
git branch -M main
git push -u origin main
```

**If you get authentication error:**
- GitHub now requires a Personal Access Token instead of password
- Go to: https://github.com/settings/tokens
- Click "Generate new token (classic)"
- Select scopes: `repo` (full control)
- Copy the token and use it as your password when pushing

---

## Step 2: Deploy to Streamlit Cloud

### 2.1 Sign Up / Log In

1. Go to: https://share.streamlit.io/
2. Click "Sign up" or "Continue with GitHub"
3. Authorize Streamlit to access your GitHub

### 2.2 Create New App

1. Click **"New app"** button
2. Fill in the deployment form:
   - **Repository**: `KoenSteenhout/WeekMenu`
   - **Branch**: `main`
   - **Main file path**: `scripts/app.py`
   - **App URL** (optional): Choose a custom subdomain like `weekmenu-koen`

### 2.3 Advanced Settings (Optional)

Click "Advanced settings" if you need to:
- Set Python version: `3.11` (recommended)
- Set environment variables (not needed for basic usage)

### 2.4 Deploy!

1. Click **"Deploy!"**
2. Wait 2-3 minutes while Streamlit Cloud:
   - Clones your repository
   - Installs dependencies from `requirements.txt`
   - Starts your app
3. Your app will be live at: `https://[your-subdomain].streamlit.app`

---

## Step 3: Share with Friends

Once deployed, share the URL with your friends:
- Example: `https://weekmenu-koen.streamlit.app`
- No installation required - works in any browser
- Mobile-friendly interface

**Note:** Streamlit Cloud apps sleep after inactivity. First visit after sleep takes ~30 seconds to wake up.

---

## Troubleshooting

### App won't start / shows error

1. Check the logs in Streamlit Cloud dashboard
2. Common issues:
   - **Import errors**: Make sure `requirements.txt` is complete
   - **Database missing**: Ensure `recipes.db` is committed to git
   - **Path issues**: All paths in code are relative to `scripts/` directory

### Missing recipes in deployed app

The database (`data/recipes.db`) must be committed to git:
```bash
# Check if database is tracked
git ls-files data/recipes.db

# If not listed, add it:
git add data/recipes.db
git commit -m "Add recipe database"
git push
```

Then redeploy from Streamlit Cloud dashboard (click "Reboot app").

### Want to update the app

Just push changes to GitHub:
```bash
git add .
git commit -m "Your changes description"
git push
```

Streamlit Cloud auto-detects changes and redeploys within 1-2 minutes.

---

## Advanced: Environment Variables

If you later add features requiring API keys (already set up for Gemini, but not needed for just running the app):

1. In Streamlit Cloud dashboard, click your app
2. Click "⋮" menu → "Settings"
3. Go to "Secrets" tab
4. Add secrets in TOML format:
   ```toml
   GEMINI_API_KEY = "your_api_key_here"
   ```
5. Click "Save"
6. App will automatically reboot with new secrets

**Note:** The current app doesn't need API keys - they're only for importing new recipes locally.

---

## Need Help?

- Streamlit Cloud docs: https://docs.streamlit.io/streamlit-community-cloud
- Streamlit forum: https://discuss.streamlit.io/
- GitHub Issues: https://github.com/KoenSteenhout/WeekMenu/issues

---

Happy cooking! 🍳👨‍🍳
