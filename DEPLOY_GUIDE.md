# 📦 Deployment Guide: Agentic AI Hiring Suite

This folder contains a standalone version of the **Agentic AI Hiring Suite**, prepared for production deployment using Docker.

## 🚀 Deployment Steps (Hugging Face Spaces)

1. **Create a New Space**: Go to [huggingface.co/new-space](https://huggingface.co/new-space).
2. **Name your space** and select **Docker** as the SDK.
3. **Choose "Blank"** or "None" for the template.
4. **Upload these files**: Upload everything inside this `Deployment_Package` folder to your Space (you can connect your GitHub repo or use the web upload).
5. **Add Secrets**: Go to **Settings > Variables and Secrets** in your Space and add:
   - `OPENAI_API_KEY`: Your OpenAI key.
   - `SMTP_USER`: Your Gmail address for sending invites.
   - `SMTP_PASSWORD`: Your Gmail App Password.
   - `RENDER_EXTERNAL_URL`: (Optional) The URL of your space if using custom domains.

## 🛠️ How to use for different Companies

This setup is designed to be **portable**. Anyone you share this with just needs to:

1. Provide their own `.env` variables (as Secrets in the Cloud or a `.env` file locally).
2. Place their own `client_secret.json` in the root (if they want Gmail integration).
3. The Docker container will automatically pick up these credentials.

## 🐳 Local Deployment (with Docker)

If someone wants to run this locally using Docker:

1. Install Docker.
2. Open terminal in this folder.
3. Build the image:
   ```bash
   docker build -t hiring-suite .
   ```
4. Run the container:
   ```bash
   docker run -p 7860:7860 --env-file .env hiring-suite
   ```

## ⚠️ Important Note

- The `venv` and `.git` folders have been excluded to keep the deployment light.
- **Gmail Auth**: Remember to update the "Authorized Redirect URIs" in Google Cloud Console to your Space's URL: `https://[your-space-name].hf.space/auth/gmail/callback`.
