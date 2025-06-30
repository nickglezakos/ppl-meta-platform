# Project Initiation

## Git and Github

Start a folder. This will be the root of the project.

1. Initialize Git in Your Project Folder.
Open your terminal and navigate to your project folder:

cd /path/to/your/new/project
git init

2. Create a .gitignore File.
Create a .gitignore file to exclude files/folders you don’t want in version control (like venv, .env, etc.):

echo "venv/
__pycache__/
.env
*.pyc
.DS_Store
" > .gitignore

3. Add and Commit Your Files.

git add .
git commit -m "Initial commit"

4. Create a New Repository on GitHub
Go to GitHub and log in.
Click the "+" icon (top right) → New repository.
Name your repo (e.g., my-new-python-project), set it to public or private, and click Create repository.

5. Connect Your Local Repo to GitHub
GitHub will show you the commands to add a remote.
Replace <your-username> and <repo-name> with your info:

git remote add origin https://github.com/<your-username>/<repo-name>.git
git remote add origin https://github.com/nickglezakos/ppl-meta-media.git

6. Push Your Code to GitHub

git branch -M main
git push -u origin main




## Database


Before running the code for dynamic db reference:
```
export DATABASE_URL=postgresql://user:password@localhost/db_name
```