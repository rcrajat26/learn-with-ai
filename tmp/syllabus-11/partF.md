## §1.33 Remote access and file transfer: SSH, key mechanics, tunnels and SSM

1.33.1 Why this section exists in an operating-systems bible at all: SSH is the only interface most
       engineers ever have to a production kernel, and every diagnostic in §1.30 is run *through*
       it. The mechanism is also the cleanest available example of a `[SYSCALL]`-level story the
       reader already has intuition for — `fork`/`exec` of a login shell, a pty allocated by the
       kernel (§1.26.3), and a session created with `setsid` (§1.26.2).
1.33.2 The public-key mechanism, stated as an exchange rather than a recipe:
       `ssh-keygen -t ed25519 -C "…"` produces a keypair; the **public** half is appended to
       `~/.ssh/authorized_keys` on the server, the **private** half never leaves the client. On
       connect the server sends a challenge, the client signs it, the server verifies against the
       stored public key. **Nothing secret crosses the wire** — which is the whole reason keys beat
       passwords, and the one-line answer to "why not just use a password". `[PROVE]`
1.33.3 Ed25519 vs RSA as a current-practice choice: `ed25519` is the default recommendation (small
       fixed-size keys, fast verification, no key-size parameter to get wrong); `rsa` requires
       `-b 4096` to be defensible; `ssh-rsa` **as a signature algorithm** (SHA-1) has been disabled
       by default in OpenSSH since 8.8, which is why an old key can suddenly stop working after a
       server upgrade with a bare `Permission denied (publickey)`. `[VERSION-TRAP]` `[TRAP]`
1.33.4 **Permissions are enforced, not advised.** `~/.ssh` must be `700`, `authorized_keys` and any
       private key `600`, and the home directory must not be group-writable.
       `Permissions 0644 for 'id_rsa' are too open` is a **refusal to use the key**, not a warning —
       the connection then falls through to the next auth method and fails as though the key were
       wrong. Ties directly to the permission bits in §1.25. `[DIAG]` `[TRAP]` `[X-REF 11]`
1.33.5 `~/.ssh/config` as the unit of repeatability, with the fields that matter:
       `Host`, `HostName`, `User`, `IdentityFile`, `IdentitiesOnly yes` (without it the agent offers
       every key it holds and can trip a server's `MaxAuthTries`), `ProxyJump`,
       `ServerAliveInterval 30`/`ServerAliveCountMax` (the fix for a session dropped by a NAT or
       load-balancer idle timeout — the same mechanism as TCP keepalive, `[X-REF 10]`), and
       `ControlMaster`/`ControlPersist` for connection reuse. `[API]` `[TABLE]`
1.33.6 The bastion pattern: `ssh -J bastion user@private-host` (equivalently `ProxyJump`), and why
       it is not `ssh bastion` followed by `ssh private-host` — with `ProxyJump` the private key
       stays on the workstation and authentication to the inner host is end-to-end, whereas hopping
       manually requires a key **on the bastion**, which is the thing you were avoiding.
       `[PROVE]` `[TRAP]`
1.33.7 Port forwarding, all three directions, stated precisely because interviews ask for the
       distinction: `-L 5432:db.internal:5432` binds a **local** port and tunnels outward (reach the
       `FundsLedger` Postgres instance through a bastion without exposing it); `-R` binds a port on
       the **remote** host back to the client; `-D` is a local SOCKS proxy. `-N` (no remote command)
       and `-f` (background) are what make a tunnel a tunnel rather than a shell. `GatewayPorts` and
       `AllowTcpForwarding` are the server-side controls. `[TABLE]` `[NUM]`
1.33.8 `ssh-agent` and the trust boundary: `ssh-add` holds decrypted keys in memory so a passphrase
       is typed once; `-A`/`ForwardAgent` exposes that agent socket on the remote host, where
       **anyone with root can use your keys against every host you can reach**. Prefer `ProxyJump`
       over agent forwarding; where forwarding is unavoidable, `ssh-add -c` forces per-use
       confirmation. `[TRAP]`
1.33.9 `known_hosts` as host-key pinning: the first connection records the server's key
       (`StrictHostKeyChecking ask`), and a later mismatch produces
       `WARNING: REMOTE HOST IDENTIFICATION HAS CHANGED!` and a refusal. That warning has exactly
       two causes — the host was rebuilt, or you are being MITM'd — and **blindly running
       `ssh-keygen -R host` discards the only evidence that distinguishes them.** Verify the
       fingerprint out of band first. `[DIAG]` `[TRAP]` `[X-REF 13]`
1.33.10 File transfer and what to use when: `scp file user@host:/tmp/` and `scp -r` for one-shot
        small copies (and note `scp` now runs over the SFTP protocol by default as of OpenSSH 9.0);
        `rsync -avz --progress src/ user@host:/dest/` for anything large or repeated because it is
        **incremental and resumable** — `--partial`, `--delete`, `-e ssh`, and the trailing-slash
        rule (`src/` copies the contents, `src` copies the directory) that silently produces a
        nested directory when you get it wrong. `[VERSION-TRAP]` `[TRAP]`
1.33.11 The reason a heap dump is the motivating example: pulling a 12 GB `FundsLedger` heap dump
        (§2.3) off a node is an `rsync` job, not an `scp` job, and copying it into the container's
        writable overlay first can fill the node's disk — write it to a mounted volume and stream it
        out. `[CALC]` `[X-REF 19]`
1.33.12 **AWS SSM Session Manager as the current answer**, and why naming it signals current
        practice: no inbound port 22, no key distribution or rotation problem, IAM-scoped access,
        every session logged to CloudTrail/S3, and port forwarding via
        `aws ssm start-session --document-name AWS-StartPortForwardingSession`. The trade-off is a
        dependency on the SSM agent and on the instance's IAM role. In an EKS context the equivalent
        for a *container* is `kubectl exec`, which is not SSH at all — it is an API call to the
        kubelet that `exec`s into the container's namespaces (§2.13). `[VERSION-TRAP]` `[X-REF 18]`
        `[X-REF 19]`
1.33.13 `[INCIDENT]` An engineer investigating the `ClientRestrictions` 30 ms budget breach could
        reach the bastion but every `ssh -J` into the private subnet hung for ~2 minutes and then
        returned `Permission denied (publickey)`. **Diagnosis:** `ssh -vvv` showed the client
        offering **six** keys from a forwarded agent before the server closed the connection, and
        the server's `/var/log/secure` logged `error: maximum authentication attempts exceeded`
        against the default `MaxAuthTries 6`. **Root cause:** an agent holding many keys, with no
        `IdentitiesOnly yes` and no `IdentityFile` pinned for that host, so the correct key was
        offered seventh. **Fix:** pin `IdentityFile` + `IdentitiesOnly yes` per `Host` block in
        `~/.ssh/config`; the hang itself was the six failed round trips, not the network.
        `[INCIDENT]` `[DIAG]` `[NUM]`

*(13 leaves)*
