# Where I got stuck and how I fixed it

Problems I hit while running and publishing the work on my Mac:
1. **The cold start looked too slow for what the app does.** App initialisation took 124 ms for a tiny stdlib program. With Claude's help I traced this to the official `python` image shipping without precompiled `.pyc` files, so every new container recompiled the standard library on its first imports. Adding `RUN python -m compileall` to the Dockerfile cut init to 19 ms and the cold start from 237 ms to 123 ms (`results/20261103-160654`).
2. **Pushing to GitHub failed twice.** First, `git remote add` failed because I pasted the README's `<your-username>` placeholder literally and zsh read `<` as a redirect, so no remote was created; I reran it with my real username. Then the push was rejected because GitHub no longer accepts account passwords for git; I logged in with the GitHub CLI (`gh auth login`, browser flow) and the push worked.
3. **Commits had the wrong author.** Git had auto-generated my identity from the Mac's hostname (`nc@Navkars-Mac.local`). I set `user.name` / `user.email` and amended the first commit with `git commit --amend --reset-author`.

Problems found while the code was being built (AI-assisted, see AI_USE.md):
- **A ~40 ms stall on every request.** Python's `http.server` sent headers and body as two packets, and Nagle's algorithm plus the client's delayed ACK held the second one back by about 40 ms. That would have made warm calls look ~40 ms slower and shrunk the cold/warm gap. Fixed with `TCP_NODELAY` and one buffered write per response.
- **Order effects.** Running all cold trials and then all warm ones would mix the condition with time (the laptop heats up, caches fill). Fixed by shuffling all trials together with seed 6 and discarding warm-up trials.

# What I would do in week 2

I would run the same design on real AWS Lambda, where a cold start also includes host placement, a Firecracker microVM boot and code download, so the absolute numbers become meaningful. I would compare Python, Node and Java with SnapStart, zip versus container-image packaging, and 128 MB versus 1024 MB memory. I would add an idle-gap sweep (1, 5, 15, 30 and 60 minutes) to find when environments are recycled, and compare provisioned concurrency with scheduled pinging as pre-warming strategies, including their cost. Finally I would make the function realistic (heavy imports such as pandas or a small ML model) to see how much initialisation dominates, and whether precompiled `.pyc` files and lazy imports still cut the cold start as they did here.
