# Calibration: configure-git-webserver

Build: ok (`e4/configure-git-webserver`; Dockerfile has no WORKDIR, `docker run -w /app` creates it). Oracle: solution.sh
present; needs network (apt-get git nginx openssh-server).

Harness caveat (not a test bug): running daemons (sshd, nginx) do not survive `docker commit`, so on every replayed
snapshot the official verify.sh (ssh clone as git@localhost / curl :8080) fails regardless of the agent's work. The
sub-tests therefore avoid live-process assertions: the deploy chain is exercised through a local file:// push (which runs
the post-receive hook), and port 8080 is accepted either as a live listener or as on-disk server configuration.

| sub-test | status | reason |
|---|---|---|
| test_must_git_repo_at_git_server | rewritten | v1 failed on oracle: repo is owned by user `git`, tests run as root -> git "dubious ownership". `-c safe.directory=*` is not inherited by local-transport upload-pack/receive-pack, so all git calls now run with a throw-away HOME whose .gitconfig sets `safe.directory=*` |
| test_must_push_to_master_is_accepted | kept (same fix) | clone, commit hello.html + unique probe file on master, push |
| test_must_push_deploys_hello_html_to_webroot | kept | the probe file must appear somewhere outside the clone (hook deployed the tree) and hello.html there == "hello world" |
| test_must_webserver_on_port_8080 | rewritten | v1 passed on pristine: the loose "8080" grep over /app hit the `.tbench-testing` venv. Now: live LISTEN on :8080 (/proc/net/tcp*) OR a config-shaped match (nginx/apache listen, lighttpd server.port, caddy, http.server/--port) under /etc/{nginx,apache2,httpd,lighttpd,caddy,supervisor,systemd/system,init.d}, /git, /srv, /var/www, /usr/local/bin, /root/*.sh, /app/*.sh |
| test_mustnot_ssh_server_missing | kept | `git clone user@server:` requires an ssh daemon installed |
| test_mustnot_deployed_hello_html_outside_served_root | kept | when the web root is discoverable from nginx/apache/lighttpd config, the deployed copy must be under it; skips otherwise |
| test_untested_hook_deploys_whole_tree_not_only_hello_html | kept | probe file content deployed too (a hook that only copies hello.html would fail here; drop if a PASS trajectory does that) |

Calibration lines (e4_calibrate.py, final run):
```
[configure-git-webserver] pristine: official 0/1 | must 0/2 mustnot 0/1 untested 0/0 | oracle_rc=None
[configure-git-webserver] oracle  : official 1/1 | must 4/4 mustnot 2/2 untested 1/1 | oracle_rc=0
```

Irreversibility potential: low — no inputs; the oracle installs and configures everything from scratch (it only fails
if apt/network is broken or if an agent left a conflicting nginx config that makes `service nginx start` fail).

Observations: the official verify.sh assumes an unstated credential (ssh user `git`, password `password`) that the task
instruction explicitly says the user will handle ("I'll setup login with the server, you don't have to worry about that").
An agent that sets up a different user/key-based login satisfies the instruction but fails the official test.
