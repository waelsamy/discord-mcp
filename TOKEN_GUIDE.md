# Getting Your Discord Token

This guide explains how to extract your Discord authentication token for use with the Discord MCP server.

## Why Use Token Authentication?

- **More Secure**: No need to store your password
- **Faster**: No login process needed on startup
- **More Reliable**: Avoids CAPTCHA and rate limiting issues
- **Simpler**: Just one environment variable
- **Automatic**: Server can extract tokens automatically in headless mode (for non-MFA accounts)

## Method 1: Using the Helper Script (Recommended)

We provide a helper script that makes extracting your token easy. If you have `DISCORD_EMAIL` and `DISCORD_PASSWORD` in your `.env` file, it will **automatically log you in**!

### Automated Login (Easiest)

If you already have credentials in your `.env`:

1. Run the token extraction script:
   ```bash
   uv run python get_token.py
   ```

2. The script will:
   - Load your email/password from `.env`
   - Open a browser window
   - **Automatically fill in your credentials and click login**
   - Handle 2FA/MFA if needed (you'll be prompted to enter your code)
   - Extract and display your token

3. Copy the token and add it to your `.env` file:
   ```env
   DISCORD_TOKEN=your_token_here
   ```

4. That's it! The MCP server will now use your token for authentication.

### Manual Login

If you don't have credentials in `.env` or prefer manual login:

1. Run the script without credentials in `.env`
2. A browser window will open
3. Log in to Discord manually
4. The script will extract your token once you're logged in

## Method 2: Manual Extraction via Browser DevTools

If the script doesn't work, you can manually extract your token:

1. Open Discord in your browser (https://discord.com/app)
2. Log in to your account
3. Press `F12` to open Developer Tools
4. Click on the **Application** tab (Chrome) or **Storage** tab (Firefox)
5. Expand **Local Storage** in the left sidebar
6. Click on `https://discord.com`
7. Find the row with key `token`
8. Copy the value (it will be a long string)
9. Remove the quotes if present
10. Add it to your `.env` file:
    ```env
    DISCORD_TOKEN=your_token_here
    ```

## Method 3: Using Browser Console

1. Open Discord in your browser (https://discord.com/app)
2. Log in to your account
3. Press `F12` to open Developer Tools
4. Click on the **Console** tab
5. Paste this code and press Enter:
   ```javascript
   (function() {
     const token = localStorage.getItem('token');
     if (token) {
       const cleaned = token.replace(/^"(.*)"$/, '$1');
       console.log('Your token:', cleaned);
       // Try to copy to clipboard
       navigator.clipboard.writeText(cleaned).then(() => {
         console.log('Token copied to clipboard!');
       }).catch(() => {
         console.log('Could not copy to clipboard, please copy manually');
       });
     } else {
       console.log('Token not found in localStorage');
     }
   })();
   ```
6. Copy the token that appears
7. Add it to your `.env` file

## Security Warning ⚠️

**IMPORTANT**: Your Discord token is like a password - it gives full access to your account!

- **Never share your token** with anyone
- **Never commit your token** to git or public repositories
- **Keep your .env file** in `.gitignore`
- **Regenerate your token** if you accidentally expose it (by changing your Discord password)

## Token Format

A valid Discord token looks like this:
```
YOUR_TOKEN_LOOKS_LIKE_THIS.XXXXXX.XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
```

It has three parts separated by dots:
1. User ID (base64 encoded)
2. Timestamp (base64 encoded)
3. HMAC signature

## Troubleshooting

### Token Not Found
- Make sure you're logged in to Discord in the browser
- Try refreshing the page and running the script again
- Use the manual DevTools method instead

### Token Invalid
- The token may have expired - extract a new one
- Make sure you copied the entire token (no spaces or quotes)
- Try logging out and back in to Discord, then extract again

### Script Won't Start
- Make sure Playwright is installed: `uv sync`
- Try running in non-headless mode to see what's happening
- Check if your firewall is blocking the browser

## Alternative: Keep Using Email/Password

If you prefer, you can still use email/password authentication:

```env
DISCORD_EMAIL=your_email@example.com
DISCORD_PASSWORD=your_password
```

However, this method:
- May trigger CAPTCHA challenges
- Requires storing your password
- May be rate-limited by Discord
- Is slower (needs to login each time)

Token authentication is recommended for production use.

## Automatic Headless Token Extraction (New!)

The Discord MCP server now supports **automatic token extraction** when you start the server without a token.

### How It Works

If you provide `DISCORD_EMAIL` and `DISCORD_PASSWORD` but no `DISCORD_TOKEN`:

1. **Server starts** with `DISCORD_HEADLESS=true`
2. **Headless browser launches** automatically (invisible)
3. **Credentials auto-filled** from your `.env` file
4. **Login submitted** automatically
5. **Token extracted** via network capture
6. **Token saved** to `~/.discord_mcp_token` with secure permissions (0o600)
7. **Future runs** use the cached token (no re-authentication needed!)

### Requirements

- **No MFA/2FA**: Your Discord account must NOT have two-factor authentication enabled
- **Valid credentials**: `DISCORD_EMAIL` and `DISCORD_PASSWORD` in `.env`
- **Headless mode**: `DISCORD_HEADLESS=true` (default)

### Example Workflow

```bash
# First-time setup - add to .env
DISCORD_EMAIL=your@email.com
DISCORD_PASSWORD=your_password
DISCORD_HEADLESS=true

# Start the server
# → Headless browser extracts token automatically
# → Token saved to ~/.discord_mcp_token
# → Server ready to use!

# Future runs
# → Server uses cached token from file
# → No re-authentication needed
```

### If You Have MFA/2FA Enabled

If your account has two-factor authentication:

1. The headless extraction will detect MFA and fail with a helpful error message
2. Run `uv run python get_token.py` interactively to complete MFA in the browser
3. Copy the extracted token to `.env` as `DISCORD_TOKEN=your_token`
4. Server will use the token and save it to the file

### Troubleshooting

**Headless extraction fails:**

- Check that credentials are correct in `.env`
- Ensure MFA/2FA is disabled on your account
- Try running `get_token.py` interactively instead
- Check logs for specific error messages

**Token file permissions:**

- The token file at `~/.discord_mcp_token` has permissions `0o600` (owner read/write only)
- This is for security - only you can read the token

**Token expires:**

- The server automatically detects expired tokens (401 errors)
- It will re-extract a new token using the same method
- No manual intervention needed!
