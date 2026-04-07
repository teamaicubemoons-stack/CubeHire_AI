
# Unified Server for RecruitAI
import sys
import os

# Fix for Google OAuth "Scope has changed" error
os.environ['OAUTHLIB_RELAX_TOKEN_SCOPE'] = '1'

import importlib.util
import traceback
from fastapi import FastAPI, Request, Response, Query, HTTPException
from fastapi.responses import JSONResponse, FileResponse, HTMLResponse, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

# 1. Setup Paths to import sibling modules
current_dir = os.path.dirname(os.path.abspath(__file__)) # Backend/app
project_root = os.path.dirname(os.path.dirname(current_dir)) # Resume-Screening-Agent

# Add project root to sys.path so we can find 'JD_Generator'
sys.path.append(project_root)

# 2. Import Both Apps
# 2. Import Apps with Module Isolation

# --- Load Resume App ---
from .main import app as resume_app

# --- Load JD Generator App ---
jd_backend_path = os.path.join(project_root, "JD_Generator", "backend")
sys.path.insert(0, jd_backend_path) # Priority Path

try:
    # Prevent 'agent' module collision
    if 'agent' in sys.modules:
        del sys.modules['agent']
    
    # Dynamic Import
    spec = importlib.util.spec_from_file_location("jd_main_pkg", os.path.join(jd_backend_path, "main.py"))
    jd_module = importlib.util.module_from_spec(spec)
    sys.modules["jd_main_pkg"] = jd_module
    spec.loader.exec_module(jd_module)
    jd_app = jd_module.app
    print("✅ JD App Loaded Successfully")
except Exception as e:
    print(f"❌ Failed to load JD App: {e}")
    jd_app = FastAPI()
finally:
    # Cleanup path to avoid leaking into Aptitude
    if jd_backend_path in sys.path:
        sys.path.remove(jd_backend_path)

# --- Load Aptitude Generator App ---
aptitude_backend_path = os.path.join(project_root, "Aptitude_Generator", "backend")
sys.path.insert(0, aptitude_backend_path)

try:
    # Prevent collision again (Force reload of 'agent' for Aptitude context)
    if 'agent' in sys.modules:
        del sys.modules['agent']
        
    spec = importlib.util.spec_from_file_location("aptitude_main_pkg", os.path.join(aptitude_backend_path, "main.py"))
    aptitude_module = importlib.util.module_from_spec(spec)
    sys.modules["aptitude_main_pkg"] = aptitude_module
    spec.loader.exec_module(aptitude_module)
    aptitude_app = aptitude_module.app
    print("✅ Aptitude App Loaded Successfully")
except Exception as e:
    print(f"❌ Failed to load Aptitude App: {e}")
    traceback.print_exc()
    aptitude_app = FastAPI()
finally:
    sys.path.remove(aptitude_backend_path)

# 3. Create Unified App
app = FastAPI(title="Unified RecruitAI Server")

# CORS (Global)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from fastapi import HTTPException, Query, Request
from fastapi.responses import RedirectResponse, HTMLResponse
from .services.gmail_oauth import gmail_oauth_service

@app.get("/auth/gmail/debug")
async def debug_gmail_url(request: Request):
    """Deep debug for OAuth issues"""
    import os
    from .services.gmail_oauth import gmail_oauth_service
    
    base_url_env = os.getenv("BASE_URL") or os.getenv("BASE_URI")
    space_id = os.getenv("SPACE_ID")
    
    # Detect from headers
    proto = request.headers.get("x-forwarded-proto", "https")
    host = request.headers.get("x-forwarded-host") or request.headers.get("host")
    
    # Construction logic
    auto_url = f"{proto}://{host}".rstrip('/')
    env_url = base_url_env.replace("http://", "https://").rstrip('/') if base_url_env else None
    
    # Hugging Face Space fallback
    hf_url = f"https://{os.getenv('SPACE_ID').replace('/', '-')}.hf.space" if os.getenv('SPACE_ID') else None
    
    redirect_uri = f"{(env_url or hf_url or auto_url)}/auth/gmail/callback"
    
    return {
        "detection": {
            "proto_header": request.headers.get("x-forwarded-proto"),
            "host_header": request.headers.get("host"),
            "forwarded_host": request.headers.get("x-forwarded-host"),
            "space_id_env": space_id
        },
        "secrets": {
            "BASE_URL_set": bool(base_url_env),
            "OPENAI_KEY_set": bool(os.getenv("OPENAI_API_KEY")),
            "CLIENT_SECRET_exists": gmail_oauth_service.client_secret_path.exists(),
            "CLIENT_SECRET_path": str(gmail_oauth_service.client_secret_path)
        },
        "constructed": {
            "final_redirect_uri": redirect_uri
        },
        "google_console_requirement": "This EXACT URL must be in Google Cloud Console Authorised Redirect URIs"
    }

@app.get("/auth/gmail/start")
async def start_gmail_oauth(request: Request, company_id: str = Query(default="default_company")):
    try:
        # Robust URL Detection
        base_url_env = os.getenv("BASE_URL") or os.getenv("BASE_URI")
        space_id = os.getenv("SPACE_ID")
        
        if base_url_env:
            base_url = base_url_env.rstrip('/')
        elif space_id:
            # Automatic HF Space URL
            base_url = f"https://{space_id.replace('/', '-')}.hf.space"
        else:
            proto = request.headers.get("x-forwarded-proto", "https")
            host = request.headers.get("x-forwarded-host") or request.headers.get("host")
            base_url = f"{proto}://{host}".rstrip('/')
            
        redirect_uri = f"{base_url}/auth/gmail/callback"
        
        print(f"OAUTH_LOG: Initiating flow with redirect_uri: {redirect_uri}")
        
        # Generate authorization URL
        auth_url, state = gmail_oauth_service.get_authorization_url(company_id, redirect_uri)
        
        # Redirect user to Google
        return RedirectResponse(url=auth_url)
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start OAuth: {str(e)}")


@app.get("/auth/gmail/callback")
async def gmail_oauth_callback(
    code: str = Query(...),
    state: str = Query(...),
    company_id: str = Query(default="default_company")
):
    """
    Handle OAuth callback from Google
    
    Args:
        code: Authorization code from Google
        state: State token for CSRF protection
        company_id: Company identifier
    
    Returns:
        Success page with connection status
    """
    try:
        # Exchange code for tokens
        result = gmail_oauth_service.handle_callback(company_id, code, state)
        user_email = result.get('email', '')
        success_msg = result.get('message', 'Successfully connected!')
        
        # Return success page
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Gmail Connected</title>
            <style>
                body {{
                    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    height: 100vh;
                    margin: 0;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                }}
                .container {{
                    background: white;
                    padding: 40px;
                    border-radius: 15px;
                    box-shadow: 0 15px 35px rgba(0,0,0,0.2);
                    text-align: center;
                    max-width: 400px;
                    width: 90%;
                }}
                .success-icon {{
                    font-size: 80px;
                    margin-bottom: 20px;
                }}
                h1 {{
                    color: #333;
                    margin: 0 0 10px;
                }}
                p {{
                    color: #666;
                    margin: 10px 0;
                    line-height: 1.5;
                }}
                .email {{
                    background: #f0f2f5;
                    padding: 12px;
                    border-radius: 8px;
                    margin: 20px 0;
                    color: #444;
                    font-weight: 600;
                    word-break: break-all;
                }}
                .btn {{
                    display: inline-block;
                    margin-top: 15px;
                    padding: 12px 30px;
                    background: #4f46e5;
                    color: white;
                    border: none;
                    border-radius: 8px;
                    font-weight: bold;
                    cursor: pointer;
                    transition: background 0.2s;
                    font-size: 16px;
                }}
                .btn:hover {{
                    background: #4338ca;
                }}
            </style>
        </head>
        <body>
            <div class="card">
                <div class="success-icon">✅</div>
                <h1>Connection Established</h1>
                <p>Gmail has been successfully synced with RecruitAI.</p>
                <div class="email">{user_email}</div>
                <p style="font-size: 0.9em; opacity: 0.8;">You can now return to the dashboard. This window will close automatically.</p>
                <button onclick="closeAndReturn()" class="btn">Return to Dashboard</button>
            </div>

            <script>
                function closeAndReturn() {{
                    const connectionData = {{
                        type: 'gmail_connected',
                        email: '{user_email}',
                        timestamp: Date.now()
                    }};
                    
                    // Signal through all channels
                    try {{
                        if (window.opener) window.opener.postMessage(connectionData, '*');
                        const bc = new BroadcastChannel('gmail_auth');
                        bc.postMessage(connectionData);
                        localStorage.setItem('gmail_connected_signal', JSON.stringify(connectionData));
                    }} catch (e) {{}}
                    
                    // Close popup
                    setTimeout(() => {{ window.close(); }}, 500);
                    
                    // Redirect fallback
                    setTimeout(() => {{ window.location.href = "/"; }}, 2000);
                }}

                // Auto-trigger signaling but wait a bit before auto-closing
                setTimeout(closeAndReturn, 2500);
            </script>
        </body>
        </html>
        """
        
        return HTMLResponse(content=html_content)
    
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"OAuth callback failed: {str(e)}")


@app.get("/auth/gmail/status")
async def gmail_connection_status(response: Response, company_id: str = Query(default="default_company")):
    """
    Check if Gmail is connected for a company with no-cache headers
    """
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    
    try:
        # This will now return False if the token lacks 'gmail.send' scope
        is_connected = gmail_oauth_service.is_connected(company_id)
        
        email = None
        if is_connected:
            try:
                # Verify credentials and get fresh email
                credentials = gmail_oauth_service.get_credentials(company_id)
                from googleapiclient.discovery import build
                service = build('gmail', 'v1', credentials=credentials)
                profile = service.users().getProfile(userId='me').execute()
                email = profile.get('emailAddress')
            except Exception as e:
                # If we have a token but can't get profile, it might be revoked or expired
                print(f"OAUTH_DEBUG: Token file exists but fetch failed: {str(e)}")
                # We don't automatically delete the token file here, 
                # but we report it as disconnected to force re-auth
                is_connected = False
        
        return {
            "connected": is_connected,
            "email": email
        }
    
    except Exception as e:
        return {
            "connected": False,
            "email": None,
            "error": str(e)
        }


@app.post("/auth/gmail/disconnect")
async def disconnect_gmail(company_id: str = Query(default="default_company")):
    """
    Disconnect Gmail and revoke access
    
    Returns:
        {"status": "success"}
    """
    try:
        gmail_oauth_service.revoke_access(company_id)
        return {"status": "success", "message": "Gmail disconnected successfully"}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to disconnect: {str(e)}")


# 5. Mount Sub-Applications
app.mount("/resume", resume_app) # Optional specific mount
# But since resume_app handles /analyze at root, checking if we can merge routes or mount.
# Best practice: Mount resume app at root for backward compatibility, 
# BUT FastAPI mounts match prefixes. If we mount at root, it catches everything.
# So we mount JD first at specific path.

app.mount("/jd-api", jd_app)

# Mount JD Generator Frontend
jd_frontend_path = os.path.join(project_root, "JD_Generator", "frontend")
if os.path.exists(jd_frontend_path):
    app.mount("/jd-tools", StaticFiles(directory=jd_frontend_path, html=True), name="jd_frontend")
    print(f"✅ JD Frontend mounted at /jd-tools (Path: {jd_frontend_path})")
else:
    print(f"⚠️ Warning: JD Frontend path not found: {jd_frontend_path}")

# Mount Aptitude App
app.mount("/aptitude-api", aptitude_app)

# Mount Aptitude Frontend
aptitude_frontend_path = os.path.join(project_root, "Aptitude_Generator", "frontend")
if os.path.exists(aptitude_frontend_path):
    app.mount("/aptitude", StaticFiles(directory=aptitude_frontend_path, html=True), name="aptitude_frontend")
    print(f"✅ Aptitude Frontend mounted at /aptitude (Path: {aptitude_frontend_path})")
else:
    print(f"⚠️ Warning: Aptitude Frontend path not found: {aptitude_frontend_path}")

# Explicitly Mount Reports Directory (Fix for PDF Links)
reports_dir = os.path.join(current_dir, "Reports") # Backend/app/../Reports -> Backend/Reports actually?
# wait, current_dir is Backend/app. We want Backend/Reports usually?
# Let's check main.py line 47: os.makedirs("Reports"). This creates ./Reports relative to CWD.
# If running form Backend root, it is Backend/Reports.
reports_path = os.path.abspath("Reports") 
if not os.path.exists(reports_path): os.makedirs(reports_path)
app.mount("/reports", StaticFiles(directory=reports_path), name="reports")
print(f"✅ Reports mounted at /reports (Path: {reports_path})")

# Mount Resume Frontend
resume_frontend_path = os.path.join(project_root, "Frontend")
if os.path.exists(resume_frontend_path):
    app.mount("/resume", StaticFiles(directory=resume_frontend_path, html=True), name="resume_frontend")
    print(f"✅ Resume Frontend mounted at /resume (Path: {resume_frontend_path})")
else:
    print(f"⚠️ Warning: Resume Frontend path not found: {resume_frontend_path}")

# Mount Resume App Routes at /api to avoid root conflict
app.mount("/api", resume_app)

# Mount Frontend at Root (Catch-All) - This MUST be last
if os.path.exists(resume_frontend_path):
    app.mount("/", StaticFiles(directory=resume_frontend_path, html=True), name="resume_frontend_root")

print("✅ Unified Server Started: Resume API at /api + JD at /jd-api + Aptitude at /aptitude-api")
