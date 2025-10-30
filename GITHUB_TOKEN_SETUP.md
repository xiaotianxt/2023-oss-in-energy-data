# GitHub Token Setup Guide

## Quick Answer: Where to Place Your GitHub Token

### Method 1: Environment Variable (Recommended)

**Windows (PowerShell)**:
```powershell
$env:GITHUB_TOKEN = "ghp_your_token_here"
```

**Windows (Command Prompt)**:
```cmd
set GITHUB_TOKEN=ghp_your_token_here
```

**Linux/Mac (Bash)**:
```bash
export GITHUB_TOKEN=ghp_your_token_here
```

**Make it Permanent (Windows)**:
1. Search for "Environment Variables" in Windows Start menu
2. Click "Edit the system environment variables"
3. Click "Environment Variables..." button
4. Under "User variables", click "New..."
5. Variable name: `GITHUB_TOKEN`
6. Variable value: `ghp_your_token_here`
7. Click OK

**Make it Permanent (Linux/Mac)**:
Add to your `~/.bashrc` or `~/.zshrc`:
```bash
export GITHUB_TOKEN=ghp_your_token_here
```

Then reload: `source ~/.bashrc`

---

### Method 2: Command Line (For Single Use)

```bash
python cli.py scan-python --github-token ghp_your_token_here --limit 10
```

---

### Method 3: Create a `.env` File (Advanced)

Create a file named `.env` in the `dependency_analyzer` directory:

```env
GITHUB_TOKEN=ghp_your_token_here
```

Then load it in your script with python-dotenv (if installed).

---

## How to Get a GitHub Token

### Step 1: Go to GitHub Settings
1. Log into GitHub
2. Click your profile picture → **Settings**
3. Scroll down to **Developer settings** (left sidebar)
4. Click **Personal access tokens** → **Tokens (classic)**

### Step 2: Generate New Token
1. Click **Generate new token** → **Generate new token (classic)**
2. Give it a note: "Dependency Analyzer CVE Scanner"
3. Set expiration (recommended: 90 days)
4. Select scopes:
   - ✅ **`public_repo`** (to access public repositories)
   - ✅ **`read:org`** (if scanning organization repos)

5. Click **Generate token**
6. **COPY THE TOKEN IMMEDIATELY** (you won't see it again!)

Your token will look like: `ghp_1234567890abcdefghijklmnopqrstuvwxyz`

### Step 3: Test It

```bash
# Set the token
export GITHUB_TOKEN=ghp_your_token_here

# Test with a small scan
cd dependency_analyzer
python cli.py scan-python --limit 3
```

You should see: No warnings about rate limits!

---

## Why You Need a GitHub Token

### Without Token:
- ⚠️ **60 API requests per hour** (very limited)
- Scanning 10 projects = rate limit exceeded
- Can't access SBOM files effectively
- Tier 2 (SBOM scraping) will fail frequently

### With Token:
- ✅ **5,000 API requests per hour** (plenty)
- Can scan 50+ projects without issues
- Full access to SBOM files in repositories
- Tier 2 (SBOM scraping) works smoothly

---

## Verification: Check if Token is Working

```bash
cd dependency_analyzer
python -c "
import os
token = os.getenv('GITHUB_TOKEN')
if token:
    print(f'Token found: {token[:10]}...')
    print('Token length:', len(token))
else:
    print('No token found!')
"
```

**Expected output**:
```
Token found: ghp_123456...
Token length: 40
```

---

## Security Best Practices

### ✅ DO:
- Store token in environment variable
- Use token expiration (90 days recommended)
- Revoke tokens you no longer need
- Use minimal required scopes

### ❌ DON'T:
- Commit token to git repositories
- Share token publicly
- Use tokens with unnecessary permissions
- Store token in code files

---

## Troubleshooting

### Issue: "No token found"
**Solution**: Check if environment variable is set:
```bash
echo $GITHUB_TOKEN
```

### Issue: "Rate limit exceeded" even with token
**Causes**:
1. Token not properly loaded
2. Token expired
3. Token lacks required permissions

**Solution**:
```bash
# Test token directly
curl -H "Authorization: Bearer $GITHUB_TOKEN" https://api.github.com/user
```

Should return your GitHub user info (not 401 error).

### Issue: "Token revoked" or "Bad credentials"
**Solution**: Generate a new token and update environment variable.

---

## For Different Scanners

### Multi-Tier Scanner (scan-python, scan-all-languages)
```bash
export GITHUB_TOKEN=ghp_your_token_here
python cli.py scan-python --limit 20
```

### Original SBOM Scanner (scan-sbom)
```bash
export GITHUB_TOKEN=ghp_your_token_here
python cli.py scan-sbom --limit 20
```

### Original Full Analysis (run_full_analysis.py)
```bash
export GITHUB_TOKEN=ghp_your_token_here
python run_full_analysis.py
```

All scripts automatically read from the `GITHUB_TOKEN` environment variable!

---

## Complete Example Session

```bash
# 1. Set token (one time per session)
export GITHUB_TOKEN=ghp_your_actual_token_here

# 2. Verify it's set
echo $GITHUB_TOKEN

# 3. Run a test scan
cd dependency_analyzer
python cli.py scan-python --limit 5

# 4. Run a larger scan
python cli.py scan-python --limit 50

# 5. Or multi-language
python cli.py scan-all-languages --limit 20
```

---

## Token Permissions Reference

| Scope | Needed For | Required? |
|-------|------------|-----------|
| `public_repo` | Access public repositories | ✅ YES |
| `repo` | Access private repositories | Only if scanning private repos |
| `read:org` | Access organization repos | Only for org repos |
| `read:user` | Read user profile | ❌ NO |

**Recommended minimal scopes**: `public_repo` only (for public energy sector repos)

---

## Quick Reference Card

```bash
# Set token (Windows PowerShell)
$env:GITHUB_TOKEN = "ghp_your_token_here"

# Set token (Linux/Mac/Git Bash)
export GITHUB_TOKEN=ghp_your_token_here

# Run scan with token
cd dependency_analyzer
python cli.py scan-python --limit 20

# Or specify token directly
python cli.py scan-python --github-token ghp_your_token_here --limit 20
```

---

**Need help?** Check if token is working:
```bash
python cli.py scan-python --limit 1
```

If you see no rate limit warnings → Token is working! ✅
