# The .gitignore file prevents future untracked files from being added to the git index. 
# In other words, any files that are currently tracked will still be tracked by git.
# To remove tracked files from the git index after adding them to .gitignore, we run the following:

git rm -r --cached .
git add .
git commit -m "Removes all .gitignore files and folders"
git push origin main
