### Git Folder Uploader v2.0.0

Upload entire folders to GitHub or GitLab with one click -- no Git knowledge required.

Developed by Techip Developers
What is Git Folder Uploader?

Git Folder Uploader is a standalone Windows desktop application that makes it easy for anyone to push a local folder to a GitHub or GitLab repository, completely overwriting the remote contents. No terminal, no command line, no Git experience needed -- just point, click, and upload.
### Features

GitHub + GitLab Support -- Choose your platform with a single toggle. The app handles both seamlessly.
Automatic Git Detection -- On launch, the app checks if Git is installed on your computer. If it's missing, install it with one click (via Windows Package Manager).
Visual Folder Picker -- Browse and select any folder on your computer using a native file dialog.
Force Push / Overwrite -- Completely replaces the remote repository contents with your local folder. Perfect for deploying static sites, syncing project files, or resetting a repo.
Step-by-Step Guidance -- Every action is explained in plain language. A real-time output log shows exactly what's happening behind the scenes.
Smart Error Detection -- The app detects common errors and tells you exactly how to fix them:
Protected branch? Step-by-step instructions to unprotect it (platform-specific for GitHub vs GitLab)
Authentication failed? Guidance on creating a Personal Access Token
Repository not found? URL and permission checks
Network issues? Connectivity troubleshooting
Retry Without Starting Over -- If the push fails (e.g., protected branch), fix the issue and click "Retry Push" to re-attempt only the push step without redoing everything.
Custom Commit Message -- Set your own commit message or use the default.
Branch Selection -- Push to main, master, or any branch name you choose.
Optional Git Identity -- Set your Git username and email directly in the app if needed.
Standalone .exe -- Single file, no Python or dependencies required on the target machine.
Modern Dark UI -- Clean, branded interface with the Techip color scheme.
How It Works
The app runs the following Git commands automatically in sequence:

git init -- Initializes a fresh local repository in your selected folder
git add . -- Stages all files and subdirectories
git commit -m "your message" -- Creates a commit snapshot
git branch -M main -- Sets the branch name
git remote add origin -- Links to your GitHub/GitLab repository
git push --force origin main -- Force pushes to overwrite the remote contents
Getting Started
Download GitFolderUploader.exe from the assets below
Double-click to run (no installation needed)
Select GitHub or GitLab
Paste your repository URL
Browse to the folder you want to upload
Click UPLOAD and you're done!
System Requirements
OS: Windows 10 / 11
Git: Required (the app will help you install it if missing)
Network: Internet connection to push to remote repository
Auth: A Personal Access Token (PAT) for GitHub, or credentials/token for GitLab
Screenshot
Screenshot 2026-02-12 215245
Important Notes
This tool performs a force push, which overwrites all existing content in the remote repository. Make sure you have backups if needed.
For GitHub HTTPS authentication, you need a Personal Access Token with repo scope (GitHub no longer accepts passwords).
For GitLab, you can use your password or a token with write_repository scope.
If the target branch is protected, you'll need to temporarily unprotect it or allow force pushes in your repository settings.

Developed by Techip Developers
