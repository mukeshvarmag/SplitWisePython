# Security: Firebase API Key

## Important Note

Firebase API keys for **web applications** are meant to be public - they are used client-side and cannot be hidden. However, you MUST add restrictions to prevent abuse.

## Steps to Secure Your API Key

### 1. Regenerate the API Key (Recommended)
Since the old key was exposed, regenerate it:

1. Go to [Google Cloud Console - Credentials](https://console.cloud.google.com/apis/credentials?project=splitwise-f6602)
2. Find the "Browser key" or your API key
3. Click on it → Click "REGENERATE KEY"
4. Copy the new key and update `public/index.html`

### 2. Add HTTP Referrer Restrictions
This ensures the key only works from your domain:

1. Go to [Google Cloud Console - Credentials](https://console.cloud.google.com/apis/credentials?project=splitwise-f6602)
2. Click on your API key
3. Under "Application restrictions", select **"HTTP referrers (websites)"**
4. Add these referrers:
   ```
   https://splitwise-f6602.web.app/*
   https://splitwise-f6602.firebaseapp.com/*
   http://localhost/*
   http://127.0.0.1/*
   ```
5. Click **SAVE**

### 3. Add API Restrictions
Limit which APIs the key can access:

1. In the same API key settings page
2. Under "API restrictions", select **"Restrict key"**
3. Select only the APIs you need:
   - Identity Toolkit API
   - Token Service API
   - Firebase Installations API
4. Click **SAVE**

### 4. Enable Firebase App Check (Optional but Recommended)
This adds an extra layer of security:

1. Go to [Firebase Console - App Check](https://console.firebase.google.com/project/splitwise-f6602/appcheck)
2. Register your web app with reCAPTCHA Enterprise
3. Enforce App Check for Firestore and Authentication

## After Regenerating the Key

Update the API key in `public/index.html`:

```javascript
const firebaseConfig = {
  apiKey: "YOUR_NEW_API_KEY_HERE",
  // ... rest of config
};
```

Then redeploy:
```bash
firebase deploy --only hosting
```

## Why Firebase API Keys Can Be Public

Unlike server-side API keys, Firebase web API keys are designed to be public because:
- They identify your Firebase project to Google servers
- Security is enforced through Firebase Security Rules (Firestore, Storage)
- Authentication is handled securely by Firebase Auth
- The key alone cannot access your data without proper authentication

Your **Firestore Security Rules** are already set up to only allow authenticated users to access their own data, which is the proper security mechanism.

