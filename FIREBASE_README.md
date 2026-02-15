# Hangout Split - Firebase Version

A bill-splitting web application hosted on Firebase with Firestore for real-time data persistence.

## Features

- Add/remove participants
- Add/remove expenses with equal or custom splits
- Real-time balance calculation
- Settlement suggestions
- Real-time sync across devices using Firestore

## Setup Instructions

### 1. Create a Firebase Project

1. Go to [Firebase Console](https://console.firebase.google.com/)
2. Click "Add project" and follow the setup wizard
3. Once created, click on "Web" icon (</>) to add a web app
4. Register your app and copy the Firebase config

### 2. Configure Firebase in the App

Edit `public/index.html` and replace the Firebase config with your own:

```javascript
const firebaseConfig = {
  apiKey: "YOUR_API_KEY",
  authDomain: "YOUR_PROJECT_ID.firebaseapp.com",
  projectId: "YOUR_PROJECT_ID",
  storageBucket: "YOUR_PROJECT_ID.appspot.com",
  messagingSenderId: "YOUR_SENDER_ID",
  appId: "YOUR_APP_ID"
};
```

### 3. Enable Firestore

1. In Firebase Console, go to "Firestore Database"
2. Click "Create database"
3. Start in "test mode" (allows read/write for development)
4. Choose a location for your database

### 4. Update .firebaserc

Edit `.firebaserc` and replace `your-firebase-project-id` with your actual Firebase project ID.

### 5. Install Firebase CLI

```bash
npm install -g firebase-tools
```

### 6. Login to Firebase

```bash
firebase login
```

### 7. Deploy

```bash
firebase deploy
```

## Local Development

To test locally before deploying:

```bash
firebase serve
```

This will start a local server at `http://localhost:5000`

## Security Notes

The current Firestore rules allow read/write access to all users. For production, you should:

1. Enable Firebase Authentication
2. Update `firestore.rules` to restrict access to authenticated users

Example secure rules:
```
rules_version = '2';
service cloud.firestore {
  match /databases/{database}/documents {
    match /{document=**} {
      allow read, write: if request.auth != null;
    }
  }
}
```

## Project Structure

```
├── public/
│   ├── index.html      # Main app (HTML + JavaScript)
│   └── styles.css      # Styles
├── firebase.json       # Firebase configuration
├── firestore.rules     # Firestore security rules
├── firestore.indexes.json
└── .firebaserc         # Firebase project settings
```

