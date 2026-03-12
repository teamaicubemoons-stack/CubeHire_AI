# 📧 Gmail Integration Guide — Agentic Hiring Suite

## For: Companies Using This System

This guide helps you connect your **company's hiring Gmail account** (e.g., `hiring@yourcompany.com`) to the Agentic Hiring Suite so the system can automatically fetch candidate resumes from your inbox.

**⏱️ Total Time: ~10 minutes (one-time setup)**

---

## 🔑 Understanding the Two Files

| File                                    | What It Is                                                             | Who Creates It                                | Shared?               |
| :-------------------------------------- | :--------------------------------------------------------------------- | :-------------------------------------------- | :-------------------- |
| `Backend/client_secret.json`            | **App Identity** — Tells Google "this is the Agentic Hiring Suite app" | The system owner (CEO)                        | ✅ Yes, safe to share |
| `Backend/tokens/<company>_token.pickle` | **Your Login** — Stores YOUR Gmail authorization                       | Auto-generated when you click "Connect Gmail" | ❌ Never share        |

> 💡 **If you are just USING the system (not hosting it),** skip to **[Step 5: Connect Your Gmail](#5-connect-your-gmail-1-minute)** — the `client_secret.json` is already included.

---

## 🏗️ For System Owners: Creating Your Own `client_secret.json`

Follow these steps **only if** you want to replace the default `client_secret.json` with your own company's Google Cloud project.

---

### Step 1: Create a Google Cloud Project (2 minutes)

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Click the **project dropdown** at the top → **"New Project"**
3. Enter:
   - **Project Name:** `Hiring-Suite` (or any name)
   - **Organization:** Leave as "No Organization" (or select yours)
4. Click **Create**
5. **Select** the newly created project from the dropdown

---

### Step 2: Enable Gmail API (1 minute)

1. In the left sidebar → **APIs & Services** → **Library**
2. Search for **"Gmail API"**
3. Click on it → Click **"Enable"**

✅ You should see: _"Gmail API has been enabled"_

---

### Step 3: Configure OAuth Consent Screen (3 minutes)

1. Left sidebar → **APIs & Services** → **OAuth consent screen**
2. Select **User Type**:
   - **Internal** → If you have Google Workspace (only your org's people can connect)
   - **External** → If you want anyone with a Gmail to connect
3. Click **Create**
4. Fill in:
   - **App Name:** `Agentic Hiring Suite`
   - **User Support Email:** `your-email@company.com`
   - **Developer Contact Email:** `your-email@company.com`
5. Click **Save and Continue**

#### Scopes Page:

1. Click **"Add or Remove Scopes"**
2. Search for: `gmail.readonly` and `gmail.send`
3. ✅ Check:
   - `https://www.googleapis.com/auth/gmail.readonly`
   - `https://www.googleapis.com/auth/gmail.send`
4. Click **Update** → **Save and Continue**

#### Test Users Page (Only for External type):

1. Click **"Add Users"**
2. Add your hiring email: `hiring@yourcompany.com`
3. Click **Save and Continue**

> ⚠️ **Important:** If you chose "External", your app starts in **Testing Mode** (100 user limit). To remove this limit, click **"PUBLISH APP"** on the OAuth consent screen page.

---

### Step 4: Create OAuth Credentials (2 minutes)

1. Left sidebar → **APIs & Services** → **Credentials**
2. Click **"+ CREATE CREDENTIALS"** → **"OAuth client ID"**
3. Select **Application Type:** **Web application**
4. **Name:** `Hiring Suite Web Client`
5. Under **Authorized redirect URIs**, click **"+ ADD URI"** and add:
   ```
   http://localhost:8000/auth/gmail/callback
   ```
   If deploying to a server (like Hugging Face), also add:
   ```
   https://your-space-name.hf.space/auth/gmail/callback
   ```
6. Click **Create**

#### Download the JSON:

1. A popup appears with Client ID and Secret
2. Click **"DOWNLOAD JSON"** ⬇️
3. The downloaded file will be named something like `client_secret_1055096247934-xxxxx.apps.googleusercontent.com.json`

---

### Step 4.1: Replace the File

1. **Rename** the downloaded file to exactly: `client_secret.json`
2. **Replace** the existing file at:
   ```
   Backend/client_secret.json
   ```
3. Done! The system will now use YOUR Google Cloud project for OAuth.

#### Your `client_secret.json` should look like this:

```json
{
  "web": {
    "client_id": "YOUR_CLIENT_ID.apps.googleusercontent.com",
    "project_id": "your-project-name",
    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
    "token_uri": "https://oauth2.googleapis.com/token",
    "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
    "client_secret": "GOCSPX-your-secret-here",
    "redirect_uris": ["https://your-space-name.hf.space/auth/gmail/callback"]
  }
}
```

> ✅ **Key Check:** The JSON must start with `"web"` (not `"installed"`). Web type supports browser-based OAuth redirect.

---

## 5. Connect Your Gmail (1 minute)

This is the step every user does — whether you're the system owner or a company using the system.

1. **Start the server:**

   ```bash
   # If running locally:
   python -m uvicorn Backend.app.unified_server:app --host 0.0.0.0 --port 8000
   ```

2. **Open browser:** Go to your app URL (e.g., `https://huggingface.co/spaces/user/space-name`)

3. **Click "Connect Gmail"** in the dashboard

4. **Google Login popup appears:**
   - Sign in with your **company hiring email**
   - You may see: _"This app isn't verified"_
     - Click **"Advanced"** → **"Go to Agentic Hiring Suite (unsafe)"**
   - **CRITICAL:** On the permissions screen, ensure you check **ALL** boxes, especially **"Send email on your behalf"**.
   - Click **"Allow"**

5. ✅ **Done!** You'll see a success page.

---

## 6. How It Works (Behind the Scenes)

```
You click "Connect Gmail"
        ↓
Browser redirects to Google Login
        ↓
You sign in with hiring@yourcompany.com
        ↓
Google asks: "Allow Agentic Hiring Suite to read and SEND emails?"
        ↓
You click "Allow" (Ensuring 'Send' is checked)
        ↓
Google sends auth token back to the system
        ↓
System saves token as: Backend/tokens/default_company_token.pickle
        ↓
✅ System can now read inbox AND send assessment links!
```

**Security Notes:**

- The system uses **API-based sending** which bypasses server firewall blocks (like Hugging Face SMTP blocks).
- It only uses `gmail.readonly` (to fetch resumes) and `gmail.send` (to send links).
- Your token is stored **locally** on the server — never uploaded to external databases.
- You can **revoke access** anytime from [Google Account Settings](https://myaccount.google.com/permissions)

---

## 7. Troubleshooting

| Error                                     | Solution                                                                                                                  |
| :---------------------------------------- | :------------------------------------------------------------------------------------------------------------------------ |
| _"MISSING REQUIRED SCOPE: ...gmail.send"_ | You didn't check the "Send email" box during login. **Disconnect** and **Reconnect** Gmail, ensuring you check all boxes. |
| _"Error 403: access_denied"_              | Your email is not added as a **Test User** (Step 3). Add it or **Publish** the app.                                       |
| _"Error: redirect_uri_mismatch"_          | The redirect URI in Google Console doesn't match. Add the EXACT URL shown in the error to Step 4.                         |
| _"client_secret.json not found"_          | Place the file at `Backend/client_secret.json`.                                                                           |
| _"Token expired"_                         | Delete `Backend/tokens/` folder and reconnect Gmail (Step 5).                                                             |
| _"This app is blocked"_                   | The OAuth app is not published. Go to Google Console → OAuth consent screen → Click **"PUBLISH APP"**.                    |
| _"GROQ_API_KEY Not Found"_                | Set `GROQ_API_KEY` in your environment variables or Hugging Face Space Secrets.                                           |

---

## 8. Revoking Access

If you want to disconnect your Gmail:

**Option A: From the Dashboard**

- Click **"Disconnect Gmail"** in the UI

**Option B: From Google**

1. Go to [Google Account Permissions](https://myaccount.google.com/permissions)
2. Find **"Agentic Hiring Suite"**
3. Click **"Remove Access"**

**Option C: Manual**

- Delete the file: `Backend/tokens/default_company_token.pickle`
