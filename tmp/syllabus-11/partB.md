## §1.17 Files, inodes, the VFS, links and the dentry cache

1.17.1 An **inode** holds everything about a file *except its name*: mode bits and file type,
       `uid`/`gid`, size in bytes, block/extent map, link count (`i_nlink`), and the three
       timestamps `atime`/`mtime`/`ctime`. The name lives in a **directory entry**, which is
       nothing but a `(name → inode number)` pair. `ls -i` and `stat` prove it. `[PROVE]` `[DIAG]`
1.17.2 A directory is therefore a *file whose contents are a name-to-inode table*. This single fact
       explains hard links, rename atomicity, and why `mv` within a filesystem is O(1) while `mv`
       across filesystems is a copy plus a delete. `[PROVE]`
1.17.3 **Hard link vs symlink**, as a table: a hard link is another directory entry pointing at the
       same inode (same `st_ino`, `i_nlink` incremented, cannot cross filesystems, cannot target a
       directory); a symlink is a *distinct inode whose data is a path string* (crosses
       filesystems, can dangle, `lstat` vs `stat` see different things). `[TABLE]` `[NUM]`
1.17.4 **`unlink(2)` removes a name, not a file.** `int unlink(const char *pathname)` decrements
       `i_nlink`; the inode and its blocks are freed only when `i_nlink == 0` **and** no process
       holds an open descriptor. This is the mechanism behind the `df`/`du` divergence in §1.19.
       `[SYSCALL]` `[PROVE]` `[X-REF 11]`
1.17.5 The four VFS objects the kernel actually manipulates: `struct super_block` (a mounted
       filesystem), `struct inode` (a file), `struct dentry` (a name→inode binding), `struct file`
       (an *open* file — offset, flags, and a pointer to `file_operations`). An fd indexes into the
       process's fd table, which points at a `struct file`; two fds can share one `struct file`
       (after `dup`) and therefore share the file offset. `[SOURCE]` `[PROVE]`
1.17.6 The **dentry cache** and inode cache live in the slab allocator and are reclaimable, which
       is why they appear under `Slab`/`SReclaimable` in `/proc/meminfo` and can be tens of GB on a
       box that walks many paths. `vm.vfs_cache_pressure` default **100**; lowering it makes the
       kernel prefer keeping dentries over page cache. Observe with `slabtop -o` and
       `/proc/sys/fs/dentry-state`. `[SYSCTL]` `[PROC]` `[RESEARCH: Documentation/admin-guide/sysctl/vm.rst]`
1.17.7 **Path resolution** walks one component at a time, checking `x` (search) permission on each
       directory, following mount points and symlinks (max 40 links, `ELOOP` beyond).
       `openat(2)`'s `dirfd` + `AT_FDCWD`, and `O_PATH` for "a handle to a path without opening
       it", are how you avoid TOCTOU races in that walk. `[SYSCALL]` `[TRAP]`
1.17.8 **`atime` is a write on every read.** Modern distributions mount with `relatime`, which
       updates `atime` only if the old value is older than `mtime`/`ctime` or more than 24 hours
       stale; `noatime` disables it entirely. On the `DocumentVerification` document store — 24k
       uploads/day, cold after 90 days — `noatime` removes a metadata write per read. `[NUM]`
       `[SYSCTL]`
1.17.9 `statx(2)` is the modern `stat`:
       `int statx(int dirfd, const char *path, int flags, unsigned mask, struct statx *buf)`. It is
       the only interface that returns **`btime`** (creation time, `STATX_BTIME`) and, since 6.1,
       `STATX_DIOALIGN` for `O_DIRECT` alignment (§1.18). `stat(2)` has no birth time at all.
       `[SYSCALL]` `[VERSION-TRAP]`
1.17.10 **File locking is advisory, and there are two incompatible families.** `flock(2)` locks the
        *open file* (shared across `dup`, not across `fork`-independent opens, whole-file only);
        `fcntl(F_SETLK)` POSIX record locks are per-process, byte-range, and released by closing
        *any* fd on the file. Java's `FileChannel.lock()` maps to the `fcntl` family, which is why
        two `FileLock`s inside one JVM throw `OverlappingFileLockException` rather than blocking.
        `[SYSCALL]` `[API]` `[TRAP]`
1.17.11 `inotify` as the fd-based file-watch mechanism (`inotify_init1`, `inotify_add_watch`) and its
        per-user ceiling `fs.inotify.max_user_watches` — a **memory-derived default** on 6.x, not
        the historical fixed 8192, which is why "too many open files" from a file-watching library
        surprises people. Each watch is charged against the limit and each instance is an fd.
        `[SYSCTL]` `[VERSION-TRAP]` `[RESEARCH: man 7 inotify, "/proc interfaces"]`
1.17.12 Java's file surface, stated exactly: `java.nio.file.Files` +
        `Path`, `Files.createLink` / `createSymbolicLink`,
        `Files.readAttributes(p, BasicFileAttributes.class, LinkOption.NOFOLLOW_LINKS)`,
        `Files.move(src, dst, ATOMIC_MOVE)` (which only works within one filesystem, for exactly
        the reason in 1.17.2), and `Files.newDirectoryStream` — a **closeable** resource whose leak
        is a classic fd leak. `[API]` `[TRAP]`
1.17.13 `[INCIDENT]` `DocumentVerification` stopped accepting uploads with
        `java.nio.file.FileSystemException: /tmp/…: No space left on device` while `df -h /tmp`
        showed 38% used. **Diagnosis:** `df -i /tmp` showed 100% inodes. **Root cause:**
        `Files.createTempFile` per uploaded image, 24k/day, with deletion only on the happy path —
        two years of 2–6 MB stubs the rotation script had truncated but never unlinked, so the
        directory entries (and inodes) survived. **Fix:** `DELETE_ON_CLOSE` in a
        try-with-resources, plus a `tmpfiles.d` age policy. `[INCIDENT]` `[DIAG]`

*(13 leaves)*

## §1.18 File I/O: the syscalls, the three layers of buffering, `fsync` and `O_DIRECT`

1.18.1 The core signatures, stated exactly: `int open(const char *path, int flags, mode_t mode)`,
       `ssize_t read(int fd, void *buf, size_t n)`, `ssize_t write(int fd, const void *buf, size_t n)`,
       `off_t lseek(int fd, off_t off, int whence)`, and the offset-explicit
       `pread`/`pwrite` which do **not** touch the shared file offset and are therefore the only
       safe form when descriptors are shared across threads. `[SYSCALL]` `[API]`
1.18.2 **`write()` may write less than you asked.** A short write is not an error; the contract is
       "0 ≤ returned ≤ n". Every correct writer loops. Likewise `read()` returning 4 KB from a
       requested 64 KB says nothing about EOF — only `0` does. `[TRAP]` `[PROVE]`
1.18.3 **The three layers of buffering, named separately, because "flush" means a different thing
       at each.** (1) *Userspace*: `BufferedOutputStream` / stdio, drained by `flush()`. (2) *Kernel
       page cache*: dirty pages, drained by writeback or `fsync`. (3) *Device write cache*: drained
       by a `FUA`/flush command the kernel issues as part of `fsync`. `flush()` moves bytes from (1)
       to (2) and gives you **no durability at all**. `[FLOW]` `[TRAP]`
1.18.4 `int fsync(int fd)` forces data **and** metadata for one file to stable storage;
       `int fdatasync(int fd)` skips metadata not needed to retrieve the data (it still writes a
       size change, it skips an `mtime` change). Java: `FileChannel.force(boolean metaData)` — the
       boolean *is* the `fsync`/`fdatasync` choice — and `FileDescriptor.sync()`. `[SYSCALL]` `[API]`
1.18.5 **`fsync` reports an I/O error once, to one descriptor, and then forgets.** Since the
       `errseq_t` rework (4.13) the error is reported to every fd open *at the time of the failure*
       exactly once; a process that opens the file afterwards sees success on a file whose data was
       never written. Treat `EIO` from `force()` as data loss, not as a retryable error. `[PROVE]`
       `[VERSION-TRAP]` `[RESEARCH: LWN "PostgreSQL's fsync() surprise"]`
1.18.6 The writeback tunables and their defaults, because they set how much unwritten data a power
       loss destroys: `vm.dirty_background_ratio` **10** (% of available memory at which background
       writeback starts), `vm.dirty_ratio` **20** (at which the *writer* is throttled synchronously),
       `vm.dirty_expire_centisecs` **3000** (30 s), `vm.dirty_writeback_centisecs` **500** (5 s
       flusher wakeup). The `_bytes` variants override the ratios and are what you use on a
       large-memory box. `[SYSCTL]` `[NUM]` `[CALC]`
1.18.7 **`O_DIRECT` bypasses the page cache** and imposes alignment on the buffer address, the file
       offset and the length — historically 512 bytes or the logical block size, now discoverable
       properly via `statx(STATX_DIOALIGN)`'s `stx_dio_mem_align` / `stx_dio_offset_align` (6.1+).
       Misaligned `O_DIRECT` I/O fails with `EINVAL`, silently falls back, or corrupts, depending on
       the filesystem. `[SYSCALL]` `[VERSION-TRAP]` `[TRAP]`
1.18.8 `O_SYNC` (every write implies `fsync`) vs `O_DSYNC` (implies `fdatasync`) vs `O_APPEND`
       (offset positioning and write are atomic with respect to other writers on the same file —
       the property that makes concurrent appends to one log file safe on a local filesystem and
       unsafe on NFS). `[SYSCALL]` `[TABLE]`
1.18.9 In Java, direct I/O is **not** in `StandardOpenOption`: it is
       `com.sun.nio.file.ExtendedOpenOption.DIRECT` (Java 10+), and it requires you to align the
       `ByteBuffer` yourself — `ByteBuffer.allocateDirect(n)` gives you 8-byte alignment, not
       block alignment. This is why almost no JVM service uses `O_DIRECT` and why the ledger relies
       on `fsync` + group commit instead. `[API]` `[VERSION-TRAP]`
1.18.10 `mmap(2)` as the fourth way to do file I/O: `MAP_SHARED` vs `MAP_PRIVATE`, page-fault-driven
        population, `msync` for durability, and the JVM's `MappedByteBuffer`. Its two standing
        problems: an unmapped region cannot be reliably freed before GC (mitigated in Java 21+ by
        `Arena` + `FileChannel.map(mode, off, size, arena)` in the FFM API), and an I/O error
        surfaces as `SIGBUS`, not an exception. `[API]` `[TRAP]`
1.18.11 Zero-copy: `sendfile(2)`, `splice(2)`, `copy_file_range(2)`, and `FileChannel.transferTo` —
        the payload never enters user space, which removes two copies and the userspace buffer.
        Relevant to serving the 2–6 MB `DocumentVerification` images and to `BankWithdrawal`'s 1.8k
        record payout files. `[SYSCALL]` `[API]`
1.18.12 Cache-management hints: `posix_fadvise(fd, off, len, POSIX_FADV_SEQUENTIAL |
        POSIX_FADV_DONTNEED | POSIX_FADV_RANDOM)` and `readahead(2)`. `POSIX_FADV_DONTNEED` after
        streaming a 68 GB/day document batch is the standard way to stop a bulk job evicting the
        ledger's hot page cache. `[SYSCALL]` `[NUM]`
1.18.13 `io_uring` in three syscalls — `io_uring_setup`, `io_uring_enter`, `io_uring_register` — with
        a shared submission and completion ring, so a batch of I/O costs one syscall or none
        (`SQPOLL`). It is the first Linux interface that is asynchronous for **regular files**, not
        only sockets. No JDK API exposes it as of Java 21/25. `[SYSCALL]` `[VERSION-TRAP]`
1.18.14 `[INCIDENT]` `[CALC]` `ApplicationHistory` lost 4 minutes of transition records after a host
        failure, despite "flushing after every write". **Diagnosis:** the writer called
        `BufferedWriter.flush()` and never `FileChannel.force()`; the records sat in dirty page cache
        under `vm.dirty_expire_centisecs=3000`. **Root cause:** confusing layer (1) with layer (2)
        of 1.18.3. **Fix:** `fdatasync` per batch, not per record — at 2.6M records/day and ~400
        bytes each that is 30/sec sustained; one `fsync` per record at ~1 ms each would cap the
        writer at 1,000/sec, so the correct answer is **group commit**: batch 100 records, one
        `force(false)`, 30 syncs/minute. `[INCIDENT]` `[CALC]`

*(14 leaves)*

## §1.19 File systems in practice: ext4 and XFS, journalling, block size, alignment, `df` vs `du`

1.19.1 **ext4 vs XFS**, as a decision table: ext4 (fixed inode count set at `mkfs`, extents,
       delayed allocation, shrinkable, `data=ordered` default journal mode, better on small
       filesystems and small files) vs XFS (dynamic inode allocation, allocation groups, extremely
       good parallel-write and large-file behaviour, **cannot be shrunk**, the default root
       filesystem on Amazon Linux 2023 and RHEL 8+). `[TABLE]`
1.19.2 The **three ext4 journal modes** and exactly what each guarantees: `data=journal` (data and
       metadata both journalled — slowest, safest), `data=ordered` (**default** — metadata
       journalled, data forced to disk *before* the metadata commit, so you never see metadata
       pointing at stale blocks), `data=writeback` (metadata only, no ordering — a crash can expose
       another file's old contents in your file). Read it with `tune2fs -l /dev/nvme0n1p1 |
       grep -i 'default mount'`. `[TABLE]` `[PROVE]` `[DIAG]`
1.19.3 A journal makes *metadata* consistent after a crash; it does **not** make your application
       data durable and it does not replace `fsync`. `fsck` after an unclean shutdown replays the
       journal rather than walking the whole tree — that is the entire point, and it is why a 1 TB
       volume mounts in seconds. `[PROVE]` `[TRAP]`
1.19.4 **Block size 4096 bytes** is the default and is fixed at `mkfs` time (`tune2fs -l | grep
       'Block size'`). A 180-byte ledger row is not the unit of storage; a 400-byte
       `ApplicationHistory` record occupies a full 4 KiB block unless the filesystem inlines it.
       `[NUM]` `[CALC]`
1.19.5 **Inode count is fixed at `mkfs` for ext4** and derives from the `inode_ratio` in
       `/etc/mke2fs.conf` — **16384 bytes per inode** for the `default` type, so a 100 GiB
       filesystem gets roughly 6.5M inodes. You can exhaust them with millions of tiny files while
       `df -h` reports free space, and `No space left on device` with 40% free is *always* a
       `df -i` question. XFS allocates inodes dynamically and does not have this failure mode.
       `[NUM]` `[CALC]` `[TRAP]` `[RESEARCH: man 5 mke2fs.conf]`
1.19.6 The **5% reserved-block default**: `mke2fs` reserves 5% of blocks for uid 0
       (`tune2fs -m <pct>`, visible as `Reserved block count` in `tune2fs -l`). Consequences worth
       stating: `df` counts them as used-capacity headroom so a "100% full" filesystem still lets
       root write; and on a 1 TB data volume 5% is **50 GB** of storage you are paying for and
       cannot use — the standard `-m 0` or `-m 1` change on a non-root data volume. `[NUM]`
       `[SYSCTL]`
1.19.7 **`df` and `du` disagree for exactly two reasons**, and you must distinguish them. (a)
       Reserved blocks and metadata: `df` asks the filesystem's own accounting, `du` walks the tree
       and sums file sizes. (b) **A deleted-but-still-open file**: the directory entry is gone so
       `du` cannot see it, but `i_nlink == 0` with an open fd means the blocks are not freed, so
       `df` still counts them (§1.17.4). `[PROVE]` `[TABLE]`
1.19.8 `lsof +L1` lists open files with a link count below 1 — the one command that finds case (b).
       The `NLINK` column reads `0` and the `NAME` column shows the path with `(deleted)`. The fix
       is to make the holder reopen (`SIGHUP` on a well-behaved daemon, `copytruncate` in
       `logrotate`, or a restart); `rm` cannot help you because there is nothing left to remove.
       `[DIAG]` `[TRAP]`
1.19.9 `df -h` / `df -i` / `df -hT` (with type) / `findmnt` / `lsblk -f`, and `du -sh dir`,
       `du -xh --max-depth=2 /var | sort -h | tail -20` — where `-x` is the flag that stops you
       walking into a mounted volume and misattributing its contents. `[DIAG]`
1.19.10 **Alignment**, because a misaligned write becomes a read-modify-write. Partitions start at
        1 MiB (2048 sectors) by default in modern `parted`/`sfdisk` precisely so that every 4 KiB
        filesystem block lands on a device boundary. On RAID/striped storage, `mkfs.xfs -d
        su=,sw=` and `mkfs.ext4 -E stride=,stripe_width=` must match the array geometry. On EBS,
        I/O is metered in **16 KiB units for gp2/gp3** (larger sequential I/Os are merged up to
        256 KiB), so 4 KiB random writes cost you the same IOPS as 16 KiB ones — batch them.
        `[NUM]` `[CALC]` `[RESEARCH: AWS EBS volume-types documentation, "I/O size"]`
1.19.11 Mount options that matter in production: `noatime` (§1.17.8), `errors=remount-ro` (the ext4
        default — a filesystem error silently makes your data volume read-only, and your service
        starts throwing `IOException` on every write with the disk looking healthy), `discard` vs a
        periodic `fstrim.timer` (prefer the timer; inline discard adds latency to every delete),
        and `nobarrier`, which you should never set on anything holding money. `[SYSCTL]` `[TRAP]`
1.19.12 **Container filesystems are a different animal.** The writable layer is `overlayfs`:
        modifying a file in a lower layer triggers a **copy-up** of the whole file, so a 2–6 MB
        document image edited in place costs a full copy, and `df` inside the container reports the
        overlay, not the host volume. Anything with real write volume belongs on a mounted volume,
        not the container layer. `[X-REF 19]` `[TRAP]`
1.19.13 `[INCIDENT]` `BankDeposits` failed its 06:00 statement-feed ingestion with
        `java.io.IOException: No space left on device` on a volume `df -h` reported at 61%.
        **Diagnosis:** `df -i` was fine; `du -xh --max-depth=1 /var` summed to 40 GB against `df`'s
        historical 210 GB used. `lsof +L1` showed the previous day's 500k-record month-end file
        held open by the ingestion JVM with `NLINK 0`. **Root cause:** the cleanup step `rm`'d the
        file while a `Files.lines` stream from a failed parse was still open, so 170 GB of deleted
        files accumulated across three weeks of failures. **Fix:** try-with-resources on the stream
        (which also fixed a matching fd leak, §1.16), plus a `+L1` check in the box health script.
        `[INCIDENT]` `[DIAG]`

*(13 leaves)*

## §1.20 Disks and the block layer: I/O schedulers, queue depth, readahead, EBS

1.20.1 The request path, top to bottom, as an ordered trace: syscall → page cache → filesystem
       (extent lookup) → `struct bio` → **blk-mq** software queue → I/O scheduler → hardware
       dispatch queue → driver → device → interrupt/completion → `bio_endio` → page marked clean.
       Every latency number in `iostat` is measured on a *segment* of this path, which is why they
       do not add up naively. `[FLOW]`
1.20.2 **blk-mq is the only block layer that exists now** — the legacy single-queue request path was
       removed in 5.0. It gives one software queue per CPU and *n* hardware queues, which removes
       the single per-device lock and is the reason `%util` stopped meaning what it used to mean
       (1.20.6). `[VERSION-TRAP]` `[PROVE]`
1.20.3 The schedulers, and when each is right: **`none`** (pure FIFO, no reordering — the default
       and correct choice for NVMe, where the device reorders better than you can),
       **`mq-deadline`** (deadline-based, read-preferring, the usual default for SATA/virtio),
       **`kyber`** (latency-target-based, for fast multi-queue devices), **`bfq`** (proportional
       fairness, good for desktops and interactive workloads, meaningful CPU overhead). Read and
       set via `cat /sys/block/nvme0n1/queue/scheduler` — the current one is in brackets.
       `[PROC]` `[TABLE]` `[RESEARCH: Documentation/block/ and Documentation/admin-guide/]`
1.20.4 The queue knobs under `/sys/block/<dev>/queue/`: `nr_requests` (per-queue request depth),
       `read_ahead_kb` (**128** by default — the kernel reads 128 KiB ahead on a detected
       sequential pattern), `rotational` (0 for SSD/NVMe; drives scheduler and merge heuristics),
       `nomerges` (**0**, merges enabled), `max_sectors_kb`, `rq_affinity`. Raising
       `read_ahead_kb` helps a sequential scan and *hurts* a random-read workload by evicting
       useful page cache. `[PROC]` `[SYSCTL]` `[NUM]` `[RESEARCH: Documentation/block/queue-sysfs.rst]`
1.20.5 **`iostat -x 1`, field by field** — the single most misread output in Linux
       diagnostics: `r/s`,`w/s` (IOPS), `rkB/s`,`wkB/s` (throughput), `rrqm/s`,`%rrqm` (merges —
       high merge rates mean your application is issuing I/O too small), `r_await`,`w_await` (mean
       ms per request **including queue time** — the latency your code actually experiences),
       `rareq-sz`,`wareq-sz` (mean request size in KiB), `aqu-sz` (mean queue length), `%util`.
       `[DIAG]` `[TABLE]`
1.20.6 **`%util` is not saturation on a multi-queue device.** It measures the fraction of wall time
       with *at least one* request in flight. An NVMe device that services 64 concurrent requests
       can report `%util 100.00` at 5% of its capability. On a single-queue spinning disk it did
       mean saturation; on NVMe or EBS it means "busy", full stop. Use `await` against your latency
       budget and `aqu-sz` against the device's queue depth instead. `[TRAP]` `[PROVE]`
1.20.7 `[CALC]` **`await` and `aqu-sz` are linked by Little's law**: `aqu-sz ≈ (r/s + w/s) × await
       (seconds)`. So 2,000 IOPS at 4 ms `await` gives `aqu-sz ≈ 8`. That identity is your
       cross-check: an `aqu-sz` of 30 with `await` of 2 ms and 500 IOPS is inconsistent and means
       you are reading a bursty average. It also tells you which lever you have — `await` rising
       with `aqu-sz` flat is the *device* slowing down; both rising together is *you* issuing more.
       `[CALC]` `[PROVE]`
1.20.8 Queue depth is the throughput-versus-latency dial: deeper queues let the device coalesce and
       parallelise (higher IOPS) at the cost of per-request latency. This is exactly the trade you
       make when sizing a JDBC pool in front of `FundsLedger` — a pool larger than the device can
       serve concurrently converts device queueing into application-visible p99. `[PROVE]`
       `[X-REF 09]`
1.20.9 **EBS is a network device wearing a block device's clothes**, and its numbers are contractual
       rather than physical: `gp3` gives a baseline **3,000 IOPS and 125 MiB/s** at any size, with
       provisioning up to **16,000 IOPS and 1,000 MiB/s**; `gp2` gives **3 IOPS per GiB** with a
       burst bucket that empties; `io2 Block Express` goes to 256,000 IOPS. Single-digit-millisecond
       `await` is *normal* for EBS and would be pathological for local NVMe. `[NUM]`
       `[RESEARCH: AWS EBS volume-types documentation]`
1.20.10 The ceiling you forget: the **instance's** EBS bandwidth cap, which is per instance type and
        is independent of the volume's provisioning. Attaching three 16,000-IOPS volumes to an
        instance capped at 20,000 does not give you 48,000, and `iostat` on the volume will look
        innocent while the instance-level limit does the throttling. Watch it in CloudWatch, not on
        the box. `[TRAP]` `[X-REF 18]`
1.20.11 `[PROC]` Where the truth is: `/sys/block/<dev>/queue/*` for configuration,
        `/proc/diskstats` for the raw counters `iostat` derives everything from,
        `/sys/block/<dev>/stat`, and `lsblk -o NAME,ROTA,SCHED,RQ-SIZE,MOUNTPOINT` as the one-line
        summary. `nvme list` and `nvme smart-log` for device health. `[PROC]` `[DIAG]`
1.20.12 Per-process attribution, since `iostat` is per-device: `pidstat -d 1` (kB_rd/s, kB_wr/s per
        process), `iotop -o`, `/proc/<pid>/io` (`read_bytes`/`write_bytes` count actual block
        layer traffic; `rchar`/`wchar` count syscall bytes, which include page-cache hits — the
        difference between the two pairs *is* your cache hit rate). `biolatency` and `biosnoop`
        from bcc when you need a histogram rather than a mean. `[DIAG]` `[PROC]`
1.20.13 **`D`-state is the block layer's signature.** Processes in uninterruptible sleep
        (`ps -eo pid,stat,wchan,cmd | awk '$2 ~ /^D/'`) are blocked inside the kernel on I/O and
        cannot be killed even with `SIGKILL`; they also count toward load average, so a load of 40
        on an idle-CPU box is a storage incident, not a compute one. `[X-REF 11]` `[TRAP]`
1.20.14 `[INCIDENT]` `FundsLedger` p99 on stake reservation went from 40 ms to 900 ms at 19:00 on a
        match night, holding for 40 minutes then recovering by itself. **Diagnosis:** `top` showed
        68% `wa` with CPUs idle; `iostat -x 1` showed `w_await` at 220 ms with only 3,100 write
        IOPS and `%util` pinned at 100; `aqu-sz` of 680 confirmed by Little's law. The volume was
        `gp2`, 900 GiB, so baseline was 2,700 IOPS. **Root cause:** the 3,400/sec settlement burst
        (13,600 ledger writes/sec peak) drained the gp2 burst-credit bucket; `BurstBalance` in
        CloudWatch hit 0 exactly when latency broke. **Fix:** migrate to `gp3` with provisioned
        16,000 IOPS and group-commit the settlement batch (§1.18.14) so the same work costs fewer,
        larger I/Os. This was a billing decision presenting as a latency incident. `[INCIDENT]`
        `[DIAG]` `[CALC]`

*(14 leaves)*

## §1.21 The four I/O models: blocking, non-blocking, multiplexed, asynchronous

1.21.1 The four models defined precisely, in one table: **blocking** (thread sleeps in the syscall
       until data moves), **non-blocking** (syscall returns `EAGAIN`/`EWOULDBLOCK` immediately, you
       retry), **multiplexed** (one thread asks the kernel *which of these fds are ready*, then does
       a non-blocking transfer), **asynchronous** (you hand the kernel a buffer and an operation and
       are told later that it is *finished*). `[TABLE]`
1.21.2 **The axis that actually matters is readiness versus completion.** `select`/`poll`/`epoll`
       and `kqueue` report *readiness* — you still perform the copy on your own thread. `io_uring`
       and Windows IOCP report *completion* — the kernel did the copy. Everything else about these
       APIs is detail; this distinction determines whether your event thread can ever block.
       `[PROVE]`
1.21.3 `[CALC]` **The blocking model's cost is arithmetic, not opinion.** QuizStakes peaks at
       **55k concurrent sessions**. One platform thread per connection at the JVM's ~1 MB
       `-Xss` reservation is **55 GB of stack reservation**, before heap; `ApplicationGateway` runs
       a 2 GB heap on 12–40 instances. Even ignoring memory, 55k runnable threads on a 4-vCPU box
       is a context-switch machine, not a server (§1.2). `[CALC]` `[NUM]`
1.21.4 **The non-blocking model alone is useless at scale**: without a readiness notifier you must
       poll every fd, so you burn a core to discover that nothing happened. Non-blocking mode is a
       *prerequisite* for models 3 and 4, not a model you deploy on its own. `[PROVE]` `[TRAP]`
1.21.5 **POSIX AIO (`aio_read`/`aio_write`) is not kernel asynchrony**: glibc implements it with a
       userspace thread pool. And the kernel's own `io_submit`/`libaio` path only behaves
       asynchronously for `O_DIRECT` — on buffered I/O it silently blocks. Two decades of "Linux
       has async file I/O" claims were wrong until `io_uring`. `[VERSION-TRAP]` `[TRAP]`
1.21.6 `io_uring` as the first genuinely asynchronous, genuinely general Linux I/O interface —
       completion-based, batched, works on regular files, sockets, `timeout`s and `poll` uniformly
       (§1.18.13). Its adoption story is the honest caveat: it has been a recurring source of CVEs
       and is disabled by policy in some hardened environments and container runtimes.
       `[RESEARCH: LWN io_uring coverage]`
1.21.7 The two server architectures these models produce: **thread-per-request** (simple, readable
       stack traces, blocking calls fine, bounded by thread count) versus **event loop**
       (`n_cores` threads, non-blocking everything, one blocking call anywhere stalls every
       connection on that loop). Tomcat's default connector vs Netty is exactly this choice.
       `[TABLE]`
1.21.8 The Java mapping, with exact types: blocking = `InputStream`/`OutputStream`,
       `Socket`, and `FileChannel`; non-blocking + multiplexed =
       `SocketChannel.configureBlocking(false)` + `Selector` + `SelectionKey`; asynchronous =
       `AsynchronousSocketChannel` / `AsynchronousFileChannel` with a `CompletionHandler`, which on
       Linux is implemented over a thread pool rather than kernel AIO. `[API]`
1.21.9 **Virtual threads make the blocking model viable again**, and this is the most important
       change to this section in a decade. `Thread.ofVirtual()` / `Executors.
       newVirtualThreadPerTaskExecutor()` (Java 21, JEP 444): the continuation unmounts on a
       blocking call, so you write model 1 and get model 3's scalability — a few KB per task
       instead of 1 MB. `[API]` `[NUM]`
1.21.10 `[VERSION-TRAP]` **The pinning caveat that most write-ups still state wrongly.** In Java 21
        a virtual thread blocking inside a `synchronized` block *pins* its carrier thread, so a
        `synchronized` connection pool could starve the scheduler; the standard advice was
        `ReentrantLock`. **JDK 24 (JEP 491) removed that limitation** — `synchronized` no longer
        pins. Native frames and `Object.wait()` still pin. State which JDK you are on before
        repeating either version of the advice. `[VERSION-TRAP]` `[RESEARCH: JEP 491]`
1.21.11 Choosing for a real service: `ClientRestrictions` has a **30 ms p99 budget**, 8 instances,
       extreme request rate and trivial per-request work — a non-blocking edge with pre-warmed
       pooled connections, because a single connection setup would consume the whole budget
       (§1.30). `DocumentVerification` moves 2–6 MB payloads with a p99 vendor latency of 38 s —
       thread-per-request with virtual threads, because the work is a long wait, not a fast loop.
       Same platform, opposite answers. `[PROVE]` `[NUM]`
1.21.12 `[TRAP]` **"Async is faster" is false as stated.** Asynchrony does not reduce the latency of
        one request; it increases the number of concurrent requests one thread can hold. If your
        p99 is dominated by a 900 ms vendor call, moving to an event loop changes nothing about the
        p99 and makes the stack trace unreadable. Async buys *concurrency per thread*; measure
        against that claim, not against latency. `[TRAP]` `[PROVE]`

*(12 leaves)*

## §1.22 `select`, `poll`, `epoll`: the interfaces and why only one of them scales

1.22.1 `int select(int nfds, fd_set *r, fd_set *w, fd_set *e, struct timeval *timeout)`. Its three
       fatal properties: `fd_set` is a **fixed bitmask capped at `FD_SETSIZE` = 1024** (a
       compile-time constant, not a tunable), the sets are **modified in place** so you must rebuild
       them every iteration, and the kernel must scan all `nfds` descriptors on every call.
       `[SYSCALL]` `[NUM]` `[TRAP]`
1.22.2 `int poll(struct pollfd *fds, nfds_t nfds, int timeout)` with
       `struct pollfd { int fd; short events; short revents; }`. It fixes the 1024 limit and the
       destructive-argument problem, but the **entire array is still copied into the kernel and
       scanned on every call** — O(n) per wait, where *n* is total descriptors, not ready ones.
       `[SYSCALL]` `[PROVE]`
1.22.3 `epoll` is three syscalls and a **kernel-resident interest set**: `int epoll_create1(int
       flags)` returns an fd; `int epoll_ctl(int epfd, int op, int fd, struct epoll_event *ev)` with
       `EPOLL_CTL_ADD`/`MOD`/`DEL` registers once; `int epoll_wait(int epfd, struct epoll_event
       *events, int maxevents, int timeout)` returns **only the ready descriptors**. Registration
       cost is paid once, not per wait. `[SYSCALL]` `[PROVE]`
1.22.4 Internally the interest set is a **red-black tree** and readiness is a **linked ready list**
       populated by the wakeup callback on each file's wait queue. So `epoll_wait` is O(number
       ready), not O(number watched) — that, and nothing else, is why it scales. `[SOURCE]`
       `[PROVE]`
1.22.5 `[CALC]` The scaling arithmetic on QuizStakes' 55k peak sessions with, say, 50 active at any
       instant: `select` cannot even represent 55k fds; `poll` copies and scans 55,000 `pollfd`
       structs (~660 KB) per wait to find 50; `epoll_wait` returns 50 entries and touches nothing
       else. At 10,000 waits/sec that is the difference between a spare core and 6.6 GB/s of
       pointless memory traffic. `[CALC]` `[NUM]`
1.22.6 **Level-triggered vs edge-triggered.** LT (default) reports "this fd is readable" every call
       until you drain it; ET (`EPOLLET`) reports only the *transition*. ET is faster and requires a
       discipline: you must read in a loop until `EAGAIN`, or you will never be told again and the
       connection hangs forever with data sitting in the socket buffer. `[TRAP]` `[PROVE]`
1.22.7 `EPOLLONESHOT` (disarm after one report; re-arm with `EPOLL_CTL_MOD`) as the way to hand an
       fd to a worker thread without a second thread also picking it up; and **`EPOLLEXCLUSIVE`**
       (Linux 4.5) as the fix for the accept **thundering herd** when many processes `epoll` the
       same listening socket. `[SYSCALL]` `[VERSION-TRAP]`
1.22.8 **epoll registers a `(struct file, fd)` pair, not an fd number.** Close the fd and the
       registration goes; `dup` the fd and the *same* `struct file` is now reachable under two
       numbers, so events keep firing under the original registration. This is the source of the
       classic "I closed it but epoll still reports it" bug in fd-recycling code. `[TRAP]`
       `[PROVE]`
1.22.9 **epoll does not work on regular files.** A regular file is always "ready", so registering
       one either fails with `EPERM` or produces a permanent readiness storm. That is precisely why
       file I/O in an event-loop server needs an offload thread pool or `io_uring`, and why "just
       use NIO" is not an answer for disk. `[TRAP]` `[X-REF 11]`
1.22.10 `epoll_pwait` (atomically swap the signal mask while waiting — closes the race that made the
        self-pipe trick necessary) and **`epoll_pwait2`** (Linux 5.11), which takes a
        `struct timespec` and so gives **nanosecond** timeout resolution instead of
        `epoll_wait`'s milliseconds. `[SYSCALL]` `[VERSION-TRAP]` `[NUM]`
1.22.11 The portability table: `epoll` (Linux), `kqueue` (BSD/macOS — one API for fds, signals,
        timers and vnodes), `IOCP` (Windows — completion, not readiness), `/dev/poll` (Solaris,
        historical). A cross-platform library exists to hide exactly this, which is what Netty's
        `EpollEventLoopGroup` vs `NioEventLoopGroup` is about. `[TABLE]`
1.22.12 The Java mapping, exactly: `Selector.open()` yields `sun.nio.ch.EPollSelectorImpl` on Linux;
        `selector.select()` → `epoll_wait`; **`selectedKeys()` must be cleared by the iterator's
        `remove()`** or the same key is redelivered forever (the single most common NIO bug);
        `Selector.wakeup()` is implemented over an `eventfd`; `SelectionKey.OP_WRITE` is
        level-triggered readiness and registering it permanently produces a 100%-CPU spin.
        `[API]` `[TRAP]`
1.22.13 `[INCIDENT]` An `ApplicationGateway` instance sat at 100% CPU on one core with 200 rps and
        no latency impact, then started dropping connections as traffic rose. **Diagnosis:**
        `top -H` isolated one thread; `printf '%x\n' <tid>` mapped it via `nid=` in `jcmd
        Thread.print` to a Netty event loop; `strace -c -p` showed 1.4M `epoll_wait` calls returning
        instantly. **Root cause:** a custom handler registered `OP_WRITE` and never deregistered
        it; a writable socket is *always* level-triggered ready, so the loop span. **Fix:** register
        `OP_WRITE` only when a write actually returns short, deregister on completion — the standard
        NIO write-interest protocol. `[INCIDENT]` `[DIAG]`

*(13 leaves)*

## §1.23 Signals: the catalogue, delivery, dispositions and handler constraints

1.23.1 The catalogue with the **x86-64 numbers**, because `kill -N` requires them and the numbers
       differ across architectures: `SIGHUP` 1, `SIGINT` 2, `SIGQUIT` 3, `SIGILL` 4, `SIGABRT` 6,
       `SIGBUS` 7, `SIGFPE` 8, `SIGKILL` 9, `SIGUSR1` 10, `SIGSEGV` 11, `SIGUSR2` 12, `SIGPIPE` 13,
       `SIGALRM` 14, `SIGTERM` 15, `SIGCHLD` 17, `SIGCONT` 18, `SIGSTOP` 19, `SIGTSTP` 20.
       `kill -l` prints the local truth. `[TABLE]` `[NUM]`
1.23.2 **Standard signals are not queued.** The pending set is a bitmask, so ten `SIGCHLD`s
       delivered while blocked collapse into one — which is exactly why a `SIGCHLD` handler must
       loop `waitpid(-1, &st, WNOHANG)` until it returns 0 rather than reaping one child.
       **Real-time signals `SIGRTMIN` (34) to `SIGRTMAX` (64) *are* queued** and carry a value.
       `[NUM]` `[PROVE]` `[TRAP]`
1.23.3 The three **dispositions**: default action (terminate, terminate+core, ignore, stop,
       continue — per signal, listed in `man 7 signal`), ignore (`SIG_IGN`), or a handler.
       **`SIGKILL` and `SIGSTOP` can be neither caught, blocked, nor ignored** — that is a kernel
       invariant, not a convention, and it is why `kill -9` is both reliable and destructive.
       `[TABLE]` `[PROVE]`
1.23.4 Delivery mechanics: each *thread* has a pending set and a blocked mask
       (`pthread_sigmask`/`sigprocmask`), and the *process* has a shared pending set. A
       process-directed signal is delivered to **an arbitrary thread that does not block it** —
       which is why libraries dedicate one thread to signal handling and block the signal
       everywhere else. `[PROVE]` `[SYSCALL]`
1.23.5 `int sigaction(int signum, const struct sigaction *act, struct sigaction *old)` is the only
       correct installer; `signal(2)`'s semantics (handler reset, mask behaviour) vary by
       platform. **`SA_RESTART`** decides whether an interrupted slow syscall auto-restarts or
       returns **`EINTR`** — and code that does not handle `EINTR` on `read`, `write`, `accept` or
       `poll` is broken in a way that only appears under signals. `[SYSCALL]` `[TRAP]`
1.23.6 **A handler runs on a borrowed stack in the middle of arbitrary code**, so it may call only
       **async-signal-safe** functions (the enumerated list in `man 7 signal-safety`: `write`,
       `_exit`, `signal`, `kill`, …). Not `malloc`, not `printf`, not anything taking a lock the
       interrupted code might hold — that is a self-deadlock, and it is why "log a message from the
       handler" is a bug. The safe pattern is: set a `volatile sig_atomic_t` flag, or `write` one
       byte to a self-pipe, and return. `[SOURCE]` `[TRAP]`
1.23.7 `signalfd(2)` (and `timerfd`, `eventfd`) as the modern escape: it turns signal delivery into a
       **readable file descriptor**, so signals join your `epoll` set and are handled on a normal
       thread with no safety restrictions. This is the right answer whenever the question is
       "signals in an event loop". `[SYSCALL]` `[X-REF 11]`
1.23.8 **`SIGPIPE`** is delivered when you `write` to a socket or pipe whose peer has closed, and its
       default action **terminates the process**. Every network library therefore ignores it and
       reads the `EPIPE` errno instead — the JVM does this at startup, which is why you see
       `java.io.IOException: Broken pipe` rather than a dead JVM. `[PROVE]` `[API]`
1.23.9 The JVM's own signal usage, which is why `-Xrs` exists: `SIGSEGV` is *used deliberately* for
       implicit null checks and safepoint polling (a segfault is a normal event inside HotSpot);
       `SIGQUIT` (3) triggers a full thread dump to stdout; `SIGBUS` surfaces `mmap` I/O errors
       (§1.18.10); `SIGTERM`/`SIGINT`/`SIGHUP` are consumed by the shutdown-hook machinery. Chaining
       a native handler over the JVM's without `SA_ONSTACK`-aware chaining crashes the VM.
       `[API]` `[TRAP]`
1.23.10 **`kill -3 <java-pid>` is free diagnostics**: a complete thread dump with lock ownership, to
        stdout, with no agent, no JDK on the box and no attach permission. Memorise it. Its
        programmatic cousins are `jcmd <pid> Thread.print` and `jstack <pid>`. `[DIAG]` `[API]`
1.23.11 The Java-side API surface, exactly: `Runtime.getRuntime().addShutdownHook(Thread)`,
        `sun.misc.Signal.handle(new Signal("HUP"), handler)` (unsupported but universally used for
        config reload), `ProcessHandle.destroy()` = `SIGTERM` vs `destroyForcibly()` = `SIGKILL`,
        and `Process.exitValue()` reporting **128 + signal number** — so **143** is `SIGTERM` and
        **137** is `SIGKILL`. `[API]` `[NUM]`
1.23.12 **Shutdown hooks are best-effort cleanup, never a durability mechanism.** They do not run on
        `SIGKILL`, on `Runtime.halt()`, on a JVM crash, or on host loss. Anything whose loss is a
        correctness problem must be committed before the response is sent, not flushed in a hook.
        `[TRAP]` `[X-REF 11]`
1.23.13 `[INCIDENT]` A `BankWithdrawal` `PaymentRun` of 1,800 payout records was submitted twice to
        the banking partner on a Tuesday deploy. **Diagnosis:** the pod's exit code was **137**, not
        143 — `SIGKILL`, so the shutdown hook that marked the run `SUBMITTED` never ran; the file had
        already been accepted by the partner. On restart the leader re-read the run as `APPROVED`
        and resubmitted. **Root cause:** `terminationGracePeriodSeconds: 30` against a 45 s p99 on
        the payout-file call, plus state written *after* the irreversible external effect. **Fix:**
        write the "submitted" intent **before** the call with the idempotency key, raise the grace
        period past the dependency's p99, and never let a signal handler be the thing that records
        an irreversible action. `[INCIDENT]` `[NUM]`

*(13 leaves)*

## §1.24 IPC: pipes, FIFOs, unix sockets, shared memory, `eventfd`, `futex`

1.24.1 `int pipe(int pipefd[2])` — a unidirectional in-kernel byte queue: `pipefd[0]` read end,
       `pipefd[1]` write end. Default capacity **65,536 bytes (16 pages)**, adjustable per pipe with
       `fcntl(fd, F_SETPIPE_SZ, n)` up to `fs.pipe-max-size` (default **1,048,576**) for unprivileged
       users. A full pipe blocks the writer; that back-pressure is the feature.
       `[SYSCALL]` `[SYSCTL]` `[NUM]`
1.24.2 **`PIPE_BUF` is 4096 bytes on Linux** and it is the atomicity boundary: a write of ≤ 4096
       bytes to a pipe will not be interleaved with another writer's; a larger write may be. This is
       the entire reason multi-process logging to one pipe produces mangled lines above 4 KB.
       `[NUM]` `[PROVE]` `[TRAP]`
1.24.3 The two pipe end-of-life rules, which people invert: writing when **all read ends** are
       closed raises `SIGPIPE`/`EPIPE`; reading when **all write ends** are closed returns 0 (EOF).
       A forgotten inherited write end in a forked child is why a reader hangs forever waiting for
       an EOF that never comes. `[TRAP]` `[PROVE]`
1.24.4 **FIFOs** (`mkfifo(1)` / `mkfifo(3)`) are pipes with a filesystem name and an inode, usable
       between unrelated processes. `open` for reading blocks until a writer appears (and vice
       versa) unless `O_NONBLOCK` — a startup-ordering hazard people rediscover every time.
       `[SYSCALL]` `[TRAP]`
1.24.5 **Unix domain sockets** are the general-purpose local IPC: `AF_UNIX` with `SOCK_STREAM`,
       `SOCK_DGRAM` (reliable and ordered locally, unlike UDP) or `SOCK_SEQPACKET`. Two Linux-only
       superpowers: `SO_PEERCRED`/`SO_PEERSEC` gives you the peer's authenticated uid/gid/pid — real
       authentication with no protocol — and `SCM_RIGHTS` over `sendmsg` **passes an open file
       descriptor** to another process. The abstract namespace (a leading NUL, conventionally shown
       as `@name`) avoids filesystem permissions entirely, which is a hazard as often as a
       convenience. `[SYSCALL]` `[PROVE]`
1.24.6 Unix socket vs TCP loopback for a sidecar hop: the unix socket skips the whole IP/TCP stack,
       has no port, no `TIME_WAIT`, no ephemeral-port exhaustion, and is authenticated by file
       permissions. Measurably lower latency and CPU per message. `RouterInt` as a sidecar proxy is
       exactly this case. `[PROVE]` `[X-REF 10]`
1.24.7 **POSIX shared memory** is the fastest IPC because after setup there is no syscall at all:
       `shm_open(name, O_CREAT|O_RDWR, 0600)` → `ftruncate` → `mmap(MAP_SHARED)`. It lives in
       `/dev/shm`, a `tmpfs` whose default size is **50% of RAM** on a normal host. You now own
       synchronisation yourself — a shared-memory region without a memory model is a data-race
       generator. `[SYSCALL]` `[NUM]`
1.24.8 **The container trap on `/dev/shm`:** Docker/containerd default it to **64 MB**, not 50% of
       RAM, and Kubernetes gives you an `emptyDir` with `medium: Memory` (counted against the pod's
       memory limit) if you want more. Anything using shared memory or a large `tmpfs` scratch area
       breaks in a container and works on a VM for this one reason. `[NUM]` `[TRAP]` `[X-REF 19]`
1.24.9 **System V IPC** (`shmget`/`semget`/`msgget`, `ipcs`, `ipcrm`) as the legacy family worth
       recognising rather than choosing: global integer keys that collide, objects that **survive
       process exit** and leak until `ipcrm`, and system-wide limits in
       `kernel.shmmax`/`shmall`/`sem`. Prefer the POSIX equivalents in new code. `[SYSCALL]`
       `[SYSCTL]`
1.24.10 `int eventfd(unsigned initval, int flags)` — a kernel counter behind an fd. Write adds,
        read returns and zeroes (or with `EFD_SEMAPHORE`, decrements by one). It is the cheapest
        possible "wake up my event loop" primitive, `epoll`-able, and it is what the JVM's
        `Selector.wakeup()` uses on Linux. `[SYSCALL]` `[API]`
1.24.11 **`futex(2)` is the primitive under every userspace lock**, and its design point is that the
        **uncontended case never enters the kernel**: `long syscall(SYS_futex, uint32_t *uaddr, int
        op, uint32_t val, ...)`. A compare-and-swap on a userspace word takes the lock; only on
        contention does `FUTEX_WAIT` park the thread and `FUTEX_WAKE` release it. `pthread_mutex`,
        `LockSupport.park`/`unpark`, and therefore every `ReentrantLock` and every `synchronized`
        inflation, bottoms out here. `futex_waitv` (5.16) adds waiting on multiple futexes at once.
        `[SYSCALL]` `[PROVE]` `[X-REF 06]`
1.24.12 The Java surface for local IPC: `SocketChannel.open(StandardProtocolFamily.UNIX)` with
        `UnixDomainSocketAddress` (Java 16+), `MemorySegment` +
        `FileChannel.map(READ_WRITE, 0, size, arena)` for shared memory via the FFM API (Java 21),
        `ProcessBuilder` with `Redirect.PIPE`/`INHERIT` for pipes, and `LockSupport.park` for the
        futex path. `[API]` `[VERSION-TRAP]`
1.24.13 `[INCIDENT]` `DocumentVerification` began failing image extraction with
        `java.io.IOException: No space left on device` on `/dev/shm` after a lift-and-shift from EC2
        to EKS. **Diagnosis:** `df -h /dev/shm` inside the pod reported **64 MB total**; the same
        JVM on EC2 saw 15 GB. The native extraction library staged each 2–6 MB page there and kept
        up to 16 in flight. **Root cause:** the container runtime's 64 MB `/dev/shm` default
        (1.24.8), which no configuration in the application could reveal. **Fix:** an `emptyDir`
        with `medium: Memory, sizeLimit: 512Mi` mounted at `/dev/shm`, and the size added to the
        pod's memory accounting so it cannot silently cause an OOMKill instead. `[INCIDENT]`
        `[DIAG]`

*(13 leaves)*

## §1.25 Users, groups, file permissions, `setuid` and capabilities

1.25.1 The identity a process carries is **four ids, not one**: real uid (who you are), **effective
       uid (what the kernel checks)**, saved set-uid (what you may switch back to), and filesystem
       uid. `id`, `/proc/<pid>/status`'s `Uid:` line (all four, in that order), and `getuid` vs
       `geteuid`. Privilege dropping is `setresuid`, and doing it in the wrong order leaves the
       saved id able to climb back. `[PROC]` `[SYSCALL]` `[TRAP]`
1.25.2 The account databases, field by field: `/etc/passwd`
       (`name:x:uid:gid:comment:home:shell` — the `x` means the hash moved),
       `/etc/shadow` (hash, last change, min/max age, warn, inactive, expire),
       `/etc/group` (`name:x:gid:members`). A shell of `/usr/sbin/nologin` is how service accounts
       are prevented from logging in. `[TABLE]`
1.25.3 The nine permission bits as three triples (`user`/`group`/`other` × `rwx`) and their octal
       arithmetic: `644` = `rw-r--r--`, `755` = `rwxr-xr-x`, `600` = owner-only. `chmod` symbolic
       vs numeric, `chown user:group`. `[NUM]` `[CALC]`
1.25.4 **On a directory the bits mean something different**, and this is routinely got wrong: `r` =
       list the names, `w` = create/delete/rename entries, **`x` = traverse/resolve through it**.
       Consequence: with `--x` on a directory you can `open` a file whose name you already know but
       cannot `ls`; with `r--` you can list names but `stat` nothing. And **`w` on the directory,
       not on the file, is what lets you delete a file**. `[PROVE]` `[TRAP]`
1.25.5 **`umask` masks bits off at creation.** Default **022** on most distributions, so a file
       created with mode `0666` becomes `644` and a directory `0777` becomes `755`. `umask 077` for
       anything touching PII. It is inherited by children, which is what makes it dangerous in cron
       (§1.26.11). `[NUM]` `[TRAP]`
1.25.6 The three special bits: **setuid `4000`** (run with the file owner's euid — how `passwd`
       edits `/etc/shadow`), **setgid `2000`** (on a file: the group's egid; **on a directory: new
       entries inherit the directory's group**, the mechanism behind shared upload directories), and
       the **sticky bit `1000`** (in a world-writable directory only the owner may delete —
       `/tmp` is `1777`). `ls -l` shows them as `s`/`s`/`t` in the `x` positions. `[NUM]` `[TABLE]`
1.25.7 Two hard limits on setuid that close most of the naive attack surface: **the kernel ignores
       setuid on interpreted scripts**, and it ignores it entirely on a filesystem mounted
       `nosuid`. `find / -perm -4000 -type f` is the audit; the answer on a hardened box should be
       a short, known list. `[TRAP]` `[DIAG]`
1.25.8 **Capabilities split root into ~40 independent privileges**, so you no longer need uid 0 to
       do one privileged thing. The ones that matter to a backend service:
       `CAP_NET_BIND_SERVICE` (bind below port 1024), `CAP_NET_RAW` (raw sockets — what `ping` and
       `tcpdump` need), `CAP_SYS_PTRACE` (attach a debugger, which is what `strace`/`jstack` on
       another process requires), `CAP_KILL`, `CAP_DAC_OVERRIDE` (bypass file permissions), and
       **`CAP_SYS_ADMIN`, which is close enough to root that granting it is not a mitigation**.
       `[TABLE]` `[NUM]`
1.25.9 The five capability sets a process carries — **permitted, effective, inheritable, bounding,
       ambient** — plus a file's permitted/inheritable/effective sets. `getcap`/`setcap
       'cap_net_bind_service=+ep' /usr/bin/java`, `capsh --print`, and
       `/proc/<pid>/status`'s `CapEff:`/`CapBnd:` hex masks. The **ambient** set (Linux 4.3) is what
       finally let capabilities survive a non-setuid `exec`. `[PROC]` `[NUM]`
1.25.10 **`net.ipv4.ip_unprivileged_port_start` (default 1024)** is the simpler alternative to
        `CAP_NET_BIND_SERVICE`: lower it and an unprivileged process may bind port 80 directly. The
        third option — and the one to use — is to bind 8080 and let the load balancer or a
        `NodePort`/`Service` map 443 to it, so the question never arises. `[SYSCTL]` `[NUM]`
1.25.11 Container defaults, stated as they actually are: `runc` drops all but a **small default
        set** of capabilities (`CAP_CHOWN`, `CAP_DAC_OVERRIDE`, `CAP_NET_BIND_SERVICE`,
        `CAP_SETUID`, `CAP_SETGID`, `CAP_KILL`, … — no `CAP_SYS_ADMIN`, no `CAP_NET_RAW` in newer
        defaults), which is why `ping` and `tcpdump` fail inside a container that can otherwise
        reach the network. The hardening set for a QuizStakes pod:
        `securityContext: { runAsNonRoot: true, runAsUser: 10001,
        allowPrivilegeEscalation: false, readOnlyRootFilesystem: true,
        capabilities: { drop: ["ALL"] } }` — `allowPrivilegeEscalation: false` sets the
        `no_new_privs` prctl, which makes setuid binaries inert for the whole process tree.
        `[X-REF 19]` `[RESEARCH: OCI runtime-spec default capability set]`
1.25.12 Beyond the nine bits: **POSIX ACLs** (`getfacl`/`setfacl -m u:deploy:r`, indicated by a
        trailing `+` in `ls -l`) for per-user grants, and **SELinux/AppArmor** as an orthogonal
        layer that can deny an access the permission bits allow — the reason a `Permission denied`
        with correct-looking `ls -l` output means `ausearch -m avc`, not `chmod`. `[DIAG]` `[TRAP]`
1.25.13 The Java surface: `Files.getPosixFilePermissions(path)` /
        `Files.setPosixFilePermissions(path, PosixFilePermissions.fromString("rw-------"))`, and —
        the important one — creating a file *with* the right mode atomically:
        `Files.createFile(p, PosixFilePermissions.asFileAttribute(perms))`. `Files.createTempFile`
        creates `600`; the legacy `File.createTempFile` historically honoured the umask, which is a
        real difference when the file holds PII. `[API]` `[TRAP]`
1.25.14 `[INCIDENT]` A `PersonalDetails` PII extract written nightly to a shared volume was found
        group-readable by every service account on the box. **Diagnosis:** `ls -l` showed `664`;
        the code called `Files.createFile` with no attributes and relied on "the default is 600".
        `[PROC]` `/proc/<pid>/status` confirmed the process ran with a `umask` of **002**, not 022 —
        inherited from the systemd unit's `UMask=002`, set years earlier for a different job.
        **Root cause:** the file mode was `0666 & ~002 = 664`. **Fix:** pass the permissions
        explicitly at creation (1.25.13) rather than depending on inherited process state, plus
        `UMask=0077` on the unit. `[INCIDENT]` `[NUM]`

*(14 leaves)*

## §1.26 Sessions, process groups, controlling terminals, daemons and PID 1

1.26.1 The four-level hierarchy every process sits in: **pid** → **ppid** → **pgid** (process group,
       the unit of job control and of signal fan-out) → **sid** (session, which owns at most one
       controlling terminal). See all of it at once with
       `ps -eo pid,ppid,pgid,sid,tty,stat,comm`. `[PROC]` `[DIAG]`
1.26.2 `pid_t setsid(void)` creates a new session **and** a new process group with the caller as
       leader and **no controlling terminal** — and fails with `EPERM` if the caller is already a
       group leader, which is the entire reason the classic daemon recipe forks first.
       `setpgid(pid, pgid)` moves a process between groups. `[SYSCALL]` `[PROVE]`
1.26.3 The controlling terminal and the **foreground process group**: only the foreground group may
       read from the terminal; a background process that reads gets `SIGTTIN`, one that writes with
       `TOSTOP` set gets `SIGTTOU`, and both **stop** the process — which is why a backgrounded job
       sometimes just freezes with `T` in `ps`. `[TABLE]` `[TRAP]`
1.26.4 **A negative pid means a process group.** `kill(-pgid, sig)` / `kill -TERM -12345` signals
       every member; `kill(-1, sig)` signals everything you may signal. This is how a shell's
       Ctrl-C reaches an entire pipeline, and it is the correct way to terminate a process tree
       whose children you did not track. `[SYSCALL]` `[NUM]`
1.26.5 Hangup semantics: when a terminal disconnects, the kernel sends **`SIGHUP`** to the
       foreground group of that session, whose default action is to terminate. `&` alone does not
       protect you — you need `nohup cmd &` (ignore `SIGHUP`, redirect output to `nohup.out`),
       `setsid cmd` (leave the session entirely), `disown -h` after the fact, or, properly, a
       terminal multiplexer or a systemd unit. `[PROVE]` `[TRAP]`
1.26.6 The classic **double-fork daemonisation** recipe, because you must be able to explain what it
       was for: `fork` (parent exits, child is not a group leader) → `setsid` (new session, no tty) →
       `fork` again (the grandchild can never reacquire a controlling terminal) → `chdir("/")` →
       `umask(0)` → close/reopen fds 0,1,2 on `/dev/null` → write a pidfile. Every step exists to
       detach from something. `[FLOW]` `[PROVE]`
1.26.7 **systemd made all of that obsolete**, and re-implemented it correctly: `Type=simple` (do
       *not* daemonise — stay in the foreground and let the supervisor own you), `Type=notify` with
       `sd_notify(READY=1)` for real readiness, `Type=forking` only for legacy daemons that insist.
       A modern service that daemonises itself under systemd is fighting its supervisor.
       `[VERSION-TRAP]` `[TRAP]`
1.26.8 The unit fields that decide production behaviour, with defaults:
       `ExecStart=`, `Restart=on-failure`, `RestartSec=`, **`LimitNOFILE=`** (the only place the fd
       limit that applies at exec is really set — §1.16), `User=`/`Group=`, `UMask=`,
       `Environment=`/`EnvironmentFile=`, `KillSignal=SIGTERM` (default), **`TimeoutStopSec=90s`
       (default)** after which systemd escalates to `SIGKILL`, `KillMode=control-group` (default —
       signals **every** process in the unit's cgroup, not just the main pid), and
       `OOMPolicy=`. `systemctl cat`, `systemctl show -p TimeoutStopSec` to read the effective
       values. `[SYSCTL]` `[NUM]` `[API]`
1.26.9 **systemd owns the cgroup v2 hierarchy**, so every unit is a cgroup and every resource limit
       is a cgroup file: `systemd-cgls`, `systemd-cgtop`, `systemctl status` printing the unit's
       `CGroup:` path, and `MemoryMax=`/`CPUQuota=` writing `memory.max`/`cpu.max`. This is the
       bridge between §1.26 and the `/sys/fs/cgroup` reading in §1.29. `[PROC]` `[X-REF 11]`
1.26.10 **PID 1 has two obligations nothing else has.** (a) It must **reap orphans** — when any
        process dies its children are reparented to PID 1, and a PID 1 that never calls `wait`
        accumulates zombies until the pid namespace runs out. (b) The kernel **will not deliver an
        unhandled signal to PID 1**: with no installed handler, `SIGTERM` to PID 1 is silently
        discarded. A JVM as PID 1 does install a `SIGTERM` handler, so it works; a shell does not
        forward it, so it does not. Hence the container fixes: exec-form
        `ENTRYPOINT ["java","-jar","app.jar"]`, `exec java …` in a wrapper script, or `--init`/`tini`
        as a real PID 1. `[PROVE]` `[TRAP]` `[X-REF 19]`
1.26.11 **Scheduled work as a daemon-launch mechanism.** cron's five fields
       (`minute hour day-of-month month day-of-week`, so `*/15 * * * *` and `0 2 * * *`),
       `crontab -e`/`-l`, `/etc/cron.d/*` (which take an extra *user* field). Its four standing
       traps: **cron has no environment** — no profile is sourced, `$PATH` is roughly
       `/usr/bin:/bin` and `JAVA_HOME` is unset, so use absolute paths and set variables in the
       crontab; **output goes to mail, i.e. nowhere** — always `>> /var/log/job.log 2>&1`, and
       without the `2>&1` you lose precisely the errors you need (set `MAILTO=""` to stop the mail
       attempt entirely); **overlapping runs** — a 7-minute job on a 5-minute schedule piles up
       until the box dies, so wrap it in `flock -n /var/run/job.lock`; and **timezone/DST**, which
       can skip or double-run a job. systemd timers (`OnCalendar=`, `Persistent=true` to catch up a
       missed run, `RandomizedDelaySec=`) fix the environment and logging problems by construction.
       The distributed version — cron on N replicas runs the job N times — is why
       `BankWithdrawal`'s `PaymentRun` uses a leader-elected scheduler and why **idempotency beats
       every locking scheme**. `[SYSCTL]` `[TRAP]` `[X-REF 14]`
1.26.12 SSH, `scp` and `rsync` are the transport for every diagnostic in §1.30 and are treated in
       full in **§1.33**: key exchange and `authorized_keys`, `~/.ssh/config` with `ProxyJump`, `-L`
       port forwarding, agent forwarding's trust implications, and AWS SSM Session Manager as the
       preferred alternative to an open port 22.
1.26.13 `[INCIDENT]` Every `BankWithdrawal` deploy took exactly 30 seconds longer than every other
        service's and logged nothing on shutdown. **Diagnosis:** `kubectl get pod -o
        jsonpath='{...exitCode}'` returned **137**, and `docker inspect` showed
        `ENTRYPOINT /bin/sh -c "java -jar app.jar"` — shell form. `ps` inside the container showed
        `sh` as PID 1 with the JVM as PID 7. **Root cause:** `sh` neither forwards `SIGTERM` nor has
        a handler for it as PID 1 (1.26.10), so the JVM never learned it was shutting down, sat for
        the full `terminationGracePeriodSeconds: 30`, and was `SIGKILL`ed mid payout-file
        submission — the same failure as §1.23.13, one layer down. **Fix:** exec-form entrypoint,
        verified by `exitCode: 143` and a graceful-shutdown log line on the next deploy.
        `[INCIDENT]` `[DIAG]`

*(13 leaves)*

## §1.27 Time: wall clock vs monotonic, `clock_gettime`, the vDSO, timers and `timerfd`

1.27.1 `int clock_gettime(clockid_t clk_id, struct timespec *tp)` with `struct timespec { time_t
       tv_sec; long tv_nsec; }` — nanosecond *resolution*, not nanosecond *accuracy*. This one
       syscall replaced `time`, `gettimeofday` and `ftime`. `[SYSCALL]` `[API]`
1.27.2 **The clock catalogue, as a table, because picking the wrong `clk_id` is the bug.**
       `CLOCK_REALTIME` (wall clock, settable, **can jump in both directions**),
       `CLOCK_MONOTONIC` (since an arbitrary boot-ish epoch, **never decreases**, NTP-slewed, does
       **not** advance during suspend), `CLOCK_BOOTTIME` (monotonic *including* suspend),
       `CLOCK_MONOTONIC_RAW` (unslewed hardware counter), `CLOCK_TAI` (realtime without leap
       seconds), `CLOCK_PROCESS_CPUTIME_ID` / `CLOCK_THREAD_CPUTIME_ID` (consumed CPU, not elapsed
       time). `[TABLE]` `[NUM]`
1.27.3 **Why `System.currentTimeMillis()` can go backwards and `System.nanoTime()` cannot.**
       `currentTimeMillis` reads `CLOCK_REALTIME`, which `ntpd`/`chrony` may **step** backwards,
       an operator may set, and a hypervisor may correct after a live migration. `nanoTime` reads
       `CLOCK_MONOTONIC`, which the kernel guarantees never decreases. Therefore: **any elapsed-time
       measurement, timeout, retry backoff or rate limiter must use `nanoTime`**, and
       `currentTimeMillis` is only for "what time is it" — a timestamp to display or store.
       `[PROVE]` `[API]` `[TRAP]`
1.27.4 The corollaries of `nanoTime`'s contract that people get wrong: its **absolute value is
       meaningless** (it may be negative, and its epoch differs per boot), it is **not comparable
       across JVMs or hosts**, and only *differences* are defined. Correct form:
       `long t0 = System.nanoTime(); … long ms = (System.nanoTime() - t0) / 1_000_000;` — and
       subtract, never compare with `<`, to survive overflow. `[API]` `[TRAP]`
1.27.5 **The vDSO is why time is cheap.** `clock_gettime` for `CLOCK_REALTIME`/`CLOCK_MONOTONIC` is
       served from a page the kernel maps read-only into every process, so there is **no syscall,
       no mode switch** — roughly **20–30 ns** versus several hundred nanoseconds for a real
       syscall. `ldd /bin/true | grep vdso`, and `/proc/<pid>/maps` shows `[vdso]`. `[PROC]`
       `[NUM]` `[PROVE]`
1.27.6 **The `clocksource` is what the vDSO reads, and it can silently be the slow one.**
       `cat /sys/devices/system/clocksource/clocksource0/current_clocksource` should read **`tsc`**
       (or `kvm-clock`/`xen` on older virtualised hosts); a fallback to **`hpet`** or `acpi_pm`
       costs a device access per read — on the order of **500 ns to 1 µs instead of 20 ns**, a
       25–50× regression. On code that timestamps every log line and every metric, that is a
       visible CPU and latency change with no application deploy behind it.
       `/sys/devices/system/clocksource/clocksource0/available_clocksource` lists the options.
       `[PROC]` `[NUM]` `[INCIDENT]` `[RESEARCH: AWS EC2 "Set the time" / clock source documentation]`
1.27.7 `[CALC]` The arithmetic that makes 1.27.6 concrete: `ClientRestrictions` serves the money
       paths at extreme request rate inside a **30 ms p99** budget. Two timestamps per request
       (entry and exit) at 20 ns is 40 ns of overhead — noise. At 800 ns it is 1.6 µs per request,
       and on a service doing tens of thousands of requests per second per instance that is
       measurable CPU spent asking what time it is. `[CALC]` `[NUM]`
1.27.8 **NTP slews, and only sometimes steps.** `chrony`/`ntpd` correct small offsets by adjusting
       the tick rate (a *slew*, invisible to monotonic ordering) and large ones — beyond a
       configured threshold, classically 128 ms — by **stepping** the clock. `chronyc tracking`
       (System time, Last offset, RMS offset), `chronyc sources -v`, `timedatectl`. An unsynchronised
       or stepping clock breaks log correlation across services long before it breaks anything
       else. `[DIAG]` `[NUM]`
1.27.9 **Leap seconds and smearing.** A positive leap second inserts 23:59:60 into UTC, which POSIX
       `time_t` cannot represent; historical kernels repeated a second, and applications that
       assumed monotonic wall time crashed. The industry answer is **leap smearing** — spreading the
       second over hours so no clock ever repeats or reverses. The **Amazon Time Sync Service at
       `169.254.169.123`** smears; a public NTP pool may not, so mixing sources across a fleet gives
       you hosts that disagree by up to a second during the smear window. `CLOCK_TAI` sidesteps leap
       seconds entirely. `[NUM]` `[RESEARCH: AWS Time Sync / leap-second guidance]`
1.27.10 The timer families: `nanosleep`/`clock_nanosleep` (the latter with **`TIMER_ABSTIME`**, which
        is the only way to schedule "at time T" without drift), `setitimer` (legacy, per-process,
        signal-delivered), `timer_create` (POSIX per-process timers, signal or thread notification),
        and **`timerfd_create(clockid, flags)`** — a timer behind a **file descriptor**, so it joins
        your `epoll` set and needs no signal handler. `timerfd` is the right primitive for
        "expire these reservations" in an event loop. `[SYSCALL]` `[TABLE]`
1.27.11 Timer accuracy is bounded by the kernel's timekeeping, not by your requested value:
        **hrtimers** give sub-millisecond wakeups, `CONFIG_HZ` (250 or 1000 on distribution
        kernels) sets the tick for the coarse path, and the per-process **timer slack**
        (`prctl(PR_SET_TIMERSLACK)`, default **50 µs**) lets the kernel batch wakeups to save power.
        So `Thread.sleep(1)` may return in 1 ms or in 15 ms depending on the platform and load, and
        `LockSupport.parkNanos` is a *hint*. Never build a rate limiter on sleep granularity.
        `[NUM]` `[SYSCTL]` `[TRAP]`
1.27.12 The Java time API mapped to the clocks: `System.currentTimeMillis` → `CLOCK_REALTIME`;
        `System.nanoTime` → `CLOCK_MONOTONIC`; `Instant.now()` → `Clock.systemUTC()`, which reads
        the realtime clock at **microsecond** precision on modern JDKs (millisecond before Java 9 —
        a real behaviour change in code that deduplicated on timestamp); `Duration.between` for wall
        intervals but `nanoTime` deltas for measurement; and **inject a `Clock`** rather than calling
        the statics, which is the only way the expiry logic in 1.27.13 is testable.
        `[API]` `[VERSION-TRAP]`
1.27.13 `[INCIDENT]` `FundsLedger` released 340 stake reservations early and left 60 held for hours,
        on three instances, within the same minute. **Diagnosis:** logs showed negative computed
        durations (`elapsedMs = -2841`); `chronyc tracking` reported a **−2.9 s step** applied after
        a `chronyd` restart on all three hosts. **Root cause:** the in-memory reservation expiry
        index stored `System.currentTimeMillis() + ttl` as an absolute wall-clock deadline and
        compared it against `currentTimeMillis()`. A backward step made deadlines appear to be in
        the future (held) while the reordered index made others appear passed (released early) —
        against reservations whose lifetime is *seconds to hours* (Appendix A.6). **Fix:** deadlines
        as `System.nanoTime() + ttlNanos` for expiry decisions, wall-clock timestamps retained only
        for the audit record, and `clock_nanosleep(TIMER_ABSTIME)`/`timerfd` semantics for the sweep.
        `[INCIDENT]` `[PROVE]`

*(13 leaves)*

## §1.28 Finding, inspecting and killing a process

1.28.1 The two `ps` dialects and the columns that matter: BSD-style `ps aux` (`%CPU`, `%MEM`, `VSZ`,
       `RSS`, `STAT`, `START`, `TIME`, `COMMAND`) and UNIX-style `ps -ef` (`UID`, `PID`, `PPID`,
       `C`, `STIME`, `TTY`, `TIME`, `CMD`). `%CPU` in `ps` is an average **over the process's whole
       lifetime**, not an instantaneous figure — which is why `ps aux --sort=-%cpu` and `top`
       disagree and why `top` is right for "what is hot now". `[TABLE]` `[TRAP]`
1.28.2 The targeted forms worth memorising: `ps aux --sort=-%cpu | head -15`,
       `ps aux --sort=-%mem | head -15`, `ps -eLf | wc -l` (**total threads on the box** — `-L`
       is the thread flag), `ps -o pid,ppid,pgid,stat,etime,rss,cmd -p <pid>`, and
       `ps -eo pid,stat,wchan,cmd | awk '$2 ~ /^D/'` for anything wedged in uninterruptible I/O
       (§1.20.13). **`RSS` is real memory; `VSZ` is virtual and is meaningless for a JVM.**
       `[DIAG]` `[TRAP]`
1.28.3 `pgrep -fa 'java.*fundsledger'` beats `ps aux | grep`, which famously matches its own `grep`
       process. `pgrep -u <user>`, `pgrep -P <ppid>` (children), `pgrep -c` (count),
       `pidof`, and `pstree -p <pid>` for the tree. `[DIAG]`
1.28.4 **Who holds a port**, three ways, because the tool available differs per box:
       `ss -lptn 'sport = :8080'` (preferred — `netstat` is deprecated), `lsof -i :8080`,
       `fuser -n tcp 8080`. All three need privilege to show *another* user's process name; without
       it you get the socket and no owner. `[DIAG]` `[X-REF 10]`
1.28.5 `[PROC]` **`/proc/<pid>` is the process's own testimony**, and it is more authoritative than
       any tool: `cmdline` (NUL-separated — `tr '\0' ' ' < /proc/1234/cmdline`), `environ` (the
       environment **as it was at exec**, which is how you catch a stale `JAVA_TOOL_OPTIONS`),
       `cwd` and `exe` (symlinks — `exe` still resolves after the binary is deleted, showing
       `(deleted)`), `fd/` (§1.16), `limits` (**the fd/memory limits actually in force**, unlike
       your shell's `ulimit`), `status` (`VmRSS`, `Threads`, `SigBlk`), `wchan` (the kernel function
       it is sleeping in), `stack`. `[PROC]` `[DIAG]`
1.28.6 **`kill` means "send a signal", and its default signal is `SIGTERM` (15), not `SIGKILL`.**
       `int kill(pid_t pid, int sig)`. The name is the single most misleading identifier in POSIX:
       `kill <pid>` politely asks; `kill -9 <pid>` destroys. `kill -l` lists the names and numbers.
       `[SYSCALL]` `[TRAP]` `[NUM]`
1.28.7 **`kill -0 <pid>` sends no signal at all** — it performs only the existence-and-permission
       check, returning success if the process exists and you may signal it, `ESRCH` if it does not,
       `EPERM` if it does but you may not. It is the correct primitive for a pidfile liveness probe,
       and it is subject to the pid-reuse race (the pid may now be a different process), which is
       why systemd's cgroup tracking replaced pidfiles. `[SYSCALL]` `[PROVE]`
1.28.8 **`SIGKILL` cannot be caught, blocked or ignored** (§1.23.3), and there is one case where it
       still does nothing: a task in `D` state is not running any code to be killed and will not die
       until its I/O completes or the box reboots. `kill -9` on a wedged NFS reader is theatre.
       `[PROVE]` `[TRAP]`
1.28.9 **The escalation workflow, in order, and never leading with `-9`:**
       (1) `kill -3 <java-pid>` — capture a thread dump *before* you change anything;
       (2) `kill <pid>` — `SIGTERM`, the graceful request;
       (3) wait the service's real drain time and check `ps -p <pid>`;
       (4) `kill -9 <pid>` only if it ignored `SIGTERM`. `kill -9` skips shutdown hooks, buffered log
       flushes, in-flight request completion, lock release and clean connection teardown — it leaves
       stale distributed locks, half-written files and orphaned transactions. Reaching for it first
       is a genuine interview red flag; escalating to it is correct. `[FLOW]` `[TRAP]`
1.28.10 **`pkill -f` and its footguns.** `-f` matches the **full command line**, which is the only way
        to distinguish two JVMs — and also the way to kill far more than you meant: `pkill -f java`
        on a shared box kills every JVM; a pattern that appears in a *wrapper* script's arguments
        matches the wrapper too; `pkill` also matches processes started by other users and fails
        silently on the ones you cannot signal, so a zero exit code does not mean the target died.
        **Always `pgrep -fa <pattern>` first and read the list**, then reuse the identical pattern
        for `pkill`. `killall` matches by executable name only and means something different on BSD
        than on Linux. `[TRAP]` `[DIAG]`
1.28.11 **`kill -3` has JVM-native equivalents that are better in every way except availability.**
        `jcmd <pid> Thread.print` (thread dump to *your* terminal, not the process's stdout),
        `jcmd <pid> GC.heap_info`, `jcmd <pid> VM.native_memory summary` (needs
        `-XX:NativeMemoryTracking=summary` at start), `jcmd <pid> GC.heap_dump /tmp/heap.hprof`,
        `jstack -l <pid>` (with lock info), `jmap -histo:live <pid> | head -30`, `jps -lv` to find
        the pid. `jcmd` requires the same uid (or `CAP_SYS_PTRACE`) and a JDK on the box — which a
        distroless image does not have, so keep an ephemeral debug container or `jattach` ready.
        `[API]` `[DIAG]` `[TRAP]`
1.28.12 **Capture evidence before you kill.** Three thread dumps ten seconds apart (so you can tell
        a stuck thread from a busy one), `GC.heap_info`, and a heap dump if the symptom is memory.
        Once the process is gone the diagnosis is gone with it, and a hung JVM that gets restarted
        with no dump guarantees the same incident next week. `[TRAP]`
1.28.13 Exit codes as the post-mortem signal: **0** clean, **130** = 128+2 (`SIGINT`, Ctrl-C),
        **137** = 128+9 (`SIGKILL` — OOM killer or a grace-period expiry), **143** = 128+15
        (`SIGTERM`, i.e. a *graceful* stop that completed). `echo $?`,
        `systemctl show -p ExecMainStatus`, `kubectl get pod -o
        jsonpath='{.status.containerStatuses[0].lastState.terminated.exitCode}'`. `143` is a healthy
        deploy; `137` is a question. `[NUM]` `[DIAG]`
1.28.14 `[INCIDENT]` An operator paged for a hung `InternalPlatforms` JVM ran `pkill -f java` on a
        shared triage box and took `FundsLedger` down with it — 40 seconds of failed stake
        reservations at 1,200/sec. **Diagnosis:** `dmesg -T` showed no OOM; both JVMs exited **143**,
        i.e. deliberately signalled; shell history showed the `pkill`. **Root cause:** `-f java`
        matched every JVM on the host, and no dump was taken of the actually-hung one, so the
        original incident recurred two days later undiagnosed. **Fix:** `pgrep -fa` before `pkill`
        as a documented step (1.28.10), the escalation order of 1.28.9 in the runbook, and — the
        real fix — one service per host so that a blunt instrument has one target. `[INCIDENT]`
        `[DIAG]`

*(14 leaves)*

## §1.29 `/proc` and `/sys`: the observability substrate

1.29.1 **`/proc` is not a filesystem, it is a kernel API with `read()` as its calling convention.**
       Nothing is on disk; every `open`/`read` runs kernel code that formats a string at that
       instant. Two consequences: a read is **not atomic or consistent** across fields, so a
       process's numbers can be internally inconsistent; and `stat` sizes are meaningless (`ls -l
       /proc/meminfo` shows 0 bytes). Every tool in §1.30 is a `/proc` parser. `[PROVE]` `[PROC]`
1.29.2 `[PROC]` `/proc/<pid>/status` — the human-readable per-process summary, and the lines to read:
       `State: S (sleeping)`, `Threads: 214`, `VmRSS: 8912340 kB`, **`VmHWM:`** (the resident
       high-water mark — how close it *ever* came to the limit, which `VmRSS` cannot tell you),
       `RssAnon`/`RssFile`/`RssShmem`, `voluntary_ctxt_switches` vs
       `nonvoluntary_ctxt_switches` (the second rising means the scheduler is preempting you — CPU
       contention, not blocking), and the `SigBlk`/`SigIgn`/`SigCgt` hex masks. `[PROC]` `[DIAG]`
1.29.3 `[PROC]` `/proc/<pid>/stat` is the machine-readable form the tools actually parse: a single
       space-separated line whose fields are positional — field 14 `utime`, 15 `stime`, 23 `vsize`,
       24 `rss` (in **pages**, not bytes) — with `utime`/`stime` in **clock ticks**, where
       `USER_HZ` is **100** (`getconf CLK_TCK`). Field 2 is the comm in parentheses and **may
       contain spaces**, which breaks naive `awk '{print $14}'` parsing. `[PROC]` `[NUM]` `[TRAP]`
1.29.4 `[PROC]` `/proc/<pid>/smaps` and **`smaps_rollup`** for the memory question `RSS` cannot
       answer: `Rss`, **`Pss`** (proportional set size — shared pages divided by the number of
       sharers, the only figure that sums correctly across processes), `Private_Dirty` (what a fork
       would actually cost), `Anonymous`, `Swap`. `smaps_rollup` gives you the totals without
       parsing thousands of mapping entries — which matters, because reading full `smaps` on a
       12 GB-heap `FundsLedger` process is itself expensive. `[PROC]` `[NUM]`
1.29.5 `[PROC]` The per-process I/O and descriptor views: `/proc/<pid>/io` with **`rchar`/`wchar`**
       (bytes through the syscall interface, page-cache hits included) versus
       **`read_bytes`/`write_bytes`** (bytes that reached the block layer) — **the ratio between the
       two pairs is your page-cache hit rate**, computed with no extra tooling; plus `/proc/<pid>/fd/`
       (§1.16), `/proc/<pid>/fdinfo/<fd>` (file position, flags, and for an epoll fd the list of
       watched targets), and `/proc/<pid>/limits`. `[PROC]` `[CALC]`
1.29.6 `[PROC]` `/proc/meminfo`, and the lines that decide a memory incident: **`MemAvailable`** (the
       kernel's own estimate of what a new allocation could get — this is the number `free -h`'s
       `available` column reports, and the one to read), `MemFree` (unused, near zero **by design**),
       `Buffers`+`Cached` (reclaimable page cache), `Dirty` and `Writeback` (§1.18.6),
       `AnonPages`, `Slab`/`SReclaimable` (§1.17.6), `PageTables`, `SwapFree`,
       `Committed_AS` vs `CommitLimit`. `[PROC]` `[NUM]`
1.29.7 `[PROC]` The system-wide files: `/proc/loadavg` (`0.42 0.55 0.61 2/1043 88231` — the three
       averages, **runnable/total tasks**, and the last pid), `/proc/stat` (`cpu` lines whose
       columns are the cumulative jiffies behind `top`'s `us/sy/ni/id/wa/hi/si/st`, plus `ctxt`,
       `procs_running`, `procs_blocked`), `/proc/uptime`, `/proc/cpuinfo`, `/proc/interrupts`,
       `/proc/mounts` and `/proc/self/mountinfo`. `[PROC]` `[DIAG]`
1.29.8 `[PROC]` **PSI — pressure stall information — under `/proc/pressure/{cpu,memory,io}`**, the
       modern answer to "is this box saturated": each file gives `some avg10= avg60= avg300=
       total=` as the **percentage of time at least one task was stalled** on that resource, plus
       `full` for all tasks. Unlike load average it is dimensionless and needs no `nproc` to
       interpret, and unlike `%util` it measures the impact on *tasks* rather than on the device.
       It is per-cgroup too (`memory.pressure`, `io.pressure`). `[PROC]` `[NUM]`
       `[RESEARCH: Documentation/accounting/psi.rst]`
1.29.9 **`/proc/sys` *is* `sysctl`** — every tunable in this guide is a writable file there.
       `sysctl -a`, `sysctl net.core.somaxconn`, `sysctl -w vm.swappiness=1` (runtime only),
       `/etc/sysctl.d/99-quizstakes.conf` + `sysctl --system` for persistence. In a container most
       of `/proc/sys` is read-only and namespaced only for the network and IPC families — which is
       why a pod cannot raise `vm.max_map_count` and needs an init container or a node-level
       DaemonSet. `[SYSCTL]` `[TRAP]` `[X-REF 19]`
1.29.10 **`/sys/fs/cgroup` on the cgroup v2 unified hierarchy is where a container's truth lives**,
        and the file names are worth knowing cold: `memory.max` (the limit — `max` means
        unlimited), `memory.current`, `memory.high` (throttling threshold), `memory.stat`,
        **`memory.events`** (whose `oom_kill` counter is the definitive record that the kernel
        killed something in this cgroup), `cpu.max` (`quota period`, e.g. `200000 100000` = 2
        CPUs), **`cpu.stat`** (`nr_throttled`, `throttled_usec`), `pids.max`, `io.max`,
        `cgroup.procs`. v1's `memory.limit_in_bytes` paths are legacy — state which hierarchy you
        are on. `[PROC]` `[VERSION-TRAP]` `[NUM]`
1.29.11 **The JVM reads these files to size itself.** `-XX:+UseContainerSupport` (on by default)
        makes `Runtime.availableProcessors()` derive from `cpu.max` and
        `-XX:MaxRAMPercentage` derive the heap from `memory.max` instead of from host RAM. Verify
        with `java -XX:+PrintFlagsFinal -version | grep MaxHeapSize` **inside the container** —
        a pre-container-aware JVM, or one with cgroup v1 paths on a v2 host, sizes a 12 GB heap
        against the host's RAM and gets OOMKilled with no Java stack trace. `[API]`
        `[VERSION-TRAP]` `[X-REF 19]`
1.29.12 `[PROC]` **`/proc/<pid>/task/<tid>/` is the per-thread mirror** of everything above, and it
        is the bridge from OS to JVM: find the hot TID (`top -H -p <pid>` or `pidstat -t 1`),
        convert it to hex (`printf '%x\n' 4823` → `12d7`), and grep `nid=0x12d7` in a
        `jcmd Thread.print` dump to name the Java thread. That two-step is the standard "which Java
        thread is eating a core" recipe and it works with no profiler and no agent. `[PROC]`
        `[DIAG]` `[FLOW]`
1.29.13 `[INCIDENT]` `ClientRestrictions` breached its **30 ms p99** budget for 20 minutes; p50 was
        unchanged at 3 ms, CPU showed 40% utilisation, GC logs were clean and no dependency was
        slow. **Diagnosis:** `top` and `%CPU` were useless because the limit was not the host's.
        `cat /sys/fs/cgroup/cpu.stat` in the pod showed `nr_throttled` climbing by ~600/minute and
        `throttled_usec` accumulating; `cpu.max` read `20000 100000` — a **0.2 CPU quota** per
        100 ms period. **Root cause:** a Helm values merge dropped `resources.limits.cpu` to `200m`
        while the JVM still saw the node's 16 cores via `availableProcessors()` and sized its
        thread pools accordingly; every 100 ms period the container exhausted its quota and every
        runnable thread was stopped dead until the next one. **Fix:** raise the limit to match the
        measured need, and read `cpu.stat`/`memory.events` — not `top` — as the first move on any
        containerised latency incident. `[INCIDENT]` `[PROC]` `[CALC]`

*(13 leaves)*

## §1.30 The box-triage toolkit and the order you run it in

1.30.1 **Say the order out loud, then follow it: load/CPU → memory → disk → network → application →
       *what changed*.** The discipline is that each step either indicts a resource or exonerates it;
       you never skip ahead because a hypothesis is attractive. The last step is not optional — a
       box that was healthy an hour ago was changed by a deploy, a config push, a traffic shift or a
       dependency, and *that* is usually the answer. `[FLOW]` `[X-REF 20]`
1.30.2 **`uptime` / load average, which is meaningless without `nproc`.** The three figures are
       1/5/15-minute averages of runnable **plus uninterruptible** tasks. Load 8 on 16 cores is
       half-utilised; load 8 on 2 cores is 4× oversubscribed. The **trend matters more than the
       value** — `8.42, 7.90, 6.11` is rising and `6.11, 7.90, 8.42` is recovering. And because
       `D`-state counts, a load spike with idle CPUs is a **storage** incident (§1.20.13).
       `[DIAG]` `[TRAP]` `[NUM]`
1.30.3 **`top`, and the `%Cpu(s)` line that is the actual diagnostic**, field by field:
       `us` (your code: hot loop, GC, serialisation, regex), `sy` (kernel: syscall storm, context
       switching, tiny reads/writes), `ni`, `id` (**high `id` with bad latency means you are not
       CPU-bound — you are waiting on locks or a downstream**), `wa` (I/O wait), `hi`/`si`
       (hard/soft interrupts — high `si` is packet processing), **`st` (steal — the hypervisor gave
       your vCPU to a noisy neighbour; move the instance)**. Reading
       `%Cpu(s): 22.1 us, 4.0 sy, 0.0 ni, 12.3 id, 61.2 wa` takes one second and tells you not to
       open the GC logs. `[DIAG]` `[TABLE]`
1.30.4 `top`'s interactive keys, which is where the per-process answer comes from: **`1`** (per-core
       lines — one core at 100% with fifteen idle is a single-threaded bottleneck), **`H`**
       (individual **threads**, and the TID you feed to 1.29.12), `M` (sort by memory), `P` (by
       CPU), `c` (full command line), `e`/`E` (units). `htop` shows the same data with per-core
       bars, `F5` tree view and `F4` filtering — strictly nicer where it is installed. `[DIAG]`
1.30.5 **`vmstat 1` is the whole-box heartbeat in one line.** `r` (runnable queue — compare with
       `nproc`), `b` (blocked, i.e. `D` state), **`si`/`so` (swap in/out — anything non-zero on a
       latency-sensitive JVM box is an alert, not a curiosity)**, `bi`/`bo` (block I/O),
       `in` (interrupts/sec), **`cs` (context switches/sec — tens of thousands on a small box with
       high `%sy` is thread thrashing or lock convoying)**, then the same CPU split as `top`.
       Discard the first line: it is an average since boot. `[DIAG]` `[NUM]` `[TRAP]`
1.30.6 **`pidstat` is the per-process/per-thread layer `top` cannot give you cleanly:**
       `pidstat 1` (CPU per process), **`pidstat -t -p <pid> 1`** (per **thread**, so you get the
       TID *and* its CPU without `top -H`'s clutter), `pidstat -d 1` (per-process disk I/O),
       `pidstat -w 1` (voluntary vs involuntary context switches per process), `pidstat -r 1`
       (page faults and RSS, minor vs **major** — §1.14). `[DIAG]`
1.30.7 **`free -h`, and the misread that defines this section.** `free` = *completely unused* RAM,
       which on a healthy long-running Linux box is near zero **by design**, because idle RAM is
       wasted RAM and the kernel fills it with page cache. `buff/cache` is reclaimable.
       **`available` is the only column that matters** — the kernel's estimate of what a new
       process could get, counting reclaimable cache (`MemAvailable`, §1.29.6). "We're out of
       memory, `free` shows 300 MB" is almost always wrong; you are genuinely short only when
       **`available` is small *and* swap is actively moving** (`si`/`so` in 1.30.5). `[TRAP]`
       `[DIAG]` `[NUM]`
1.30.8 **Disk space, in the order that finds it:** `df -h` (am I full?) → **`df -i`** (inodes — you
       can be full with bytes free, §1.19.5) → `du -xh --max-depth=2 /var | sort -h | tail -20`
       (what is consuming it, `-x` staying on one filesystem) → **`lsof +L1`** (deleted-but-open
       files, §1.19.8). Four commands, and between them they cover every "no space left on device"
       you will meet. `[FLOW]` `[DIAG]`
1.30.9 **`iostat -x 1`** for the device layer — the field-by-field reading is §1.20.5, and the two
       things to carry into triage are that **`await` is the latency your application feels** and
       that **`%util` is not saturation on a multi-queue device** (§1.20.6). Drop the first sample.
       `[DIAG]` `[X-REF 11]`
1.30.10 **Network, in two commands before anything else:** `ss -s` (the summary — total sockets,
        `TIME-WAIT` count, per-protocol breakdown) and `ss -tanp` (every TCP socket with state and
        **owning process**). Then `ss -lnt` for listen queues, `nstat -az | grep -i listen` for
        overflow counters. `netstat` is deprecated and slower on a box with 50k sockets.
        `[DIAG]` `[X-REF 10]`
1.30.11 **`lsof`, the three invocations that matter:** `lsof -p <pid>` (everything one process holds
        — pipe through `awk '{print $5}' | sort | uniq -c | sort -rn` to bucket by fd type and spot
        a leak's shape), `lsof -i :8080` (who owns a port), `lsof +L1` (deleted-but-open). It is
        slow and needs privilege; `ls /proc/<pid>/fd | wc -l` is the instant approximation.
        `[DIAG]`
1.30.12 **`strace -c -p <pid>`** for a syscall profile (count, time, errors per syscall — the fastest
        way to find a syscall storm behind high `%sy`) and `strace -f -e trace=openat` for a
        specific question. **It uses `ptrace` and can slow the target 10–100×, so it is a
        last resort on a production JVM**, never a monitoring tool. The low-overhead
        alternatives: `perf trace`, `perf stat -p`, and `bpftrace`/bcc (`opensnoop`, `execsnoop`,
        `biolatency`). `[DIAG]` `[TRAP]`
1.30.13 **`dmesg -T` is where the kernel tells you what it did to you** —
        `dmesg -T | grep -i -E 'oom|killed process|blocked for more than'` finds OOM kills
        (with the score, RSS and cgroup of the victim), hung-task warnings, EBS/NVMe I/O errors and
        filesystem remounts. `journalctl -k --since '30 min ago'` for the persistent copy, and
        `-T` for human timestamps rather than seconds-since-boot. **Exit 137 with no application
        error in the log means come here first.** `[DIAG]` `[X-REF 11]`
1.30.14 `[INCIDENT]` "`ApplicationGateway` is slow, you have SSH" — the worked triage.
        `uptime`: load **8.42, 7.90, 6.11** on `nproc` 4, and rising. `top`:
        **`61.2 wa`, `12.3 id`, `22.1 us`** — I/O-bound, so the GC logs are the wrong place and
        `st` at 0.0 exonerates the hypervisor. `free -h`: `available 9.4Gi`, swap 0 — memory is
        fine, and `free 0.3Gi` is a red herring (1.30.7). `iostat -x 1`: `w_await` 180 ms,
        `%util` 100. `pidstat -d 1`: one JVM at 240 MB/s written. `lsof -p` + `ls -l`: an access log
        at DEBUG. **Root cause:** a log level left at DEBUG by a config push 50 minutes earlier
        (the *what changed* step) saturated the volume; every request now waited on a synchronous
        log write. **Fix:** revert the config, then make the appender asynchronous so a log volume
        can never again be on the request path. `[INCIDENT]` `[DIAG]` `[FLOW]`

*(14 leaves)*

## §1.31 Log combat: the text-processing pipeline for an incident

1.31.1 **`tail -F`, capital F, always.** `tail -f` follows the *inode* and goes silent the moment
       `logrotate` renames the file; `tail -F` follows the *name* and reopens. Also
       `tail -n 500 app.log`, `tail -n +1000` (from line 1000 onward), and **`less +F app.log`** —
       follow, `Ctrl-C` to stop and search, `F` to resume. `[TRAP]` `[DIAG]`
1.31.2 **`less` beats `cat`, `vim` and an editor on a 4 GB log because it does not load the file.**
       Inside it: `/pattern` and `?pattern` search, `n`/`N` next/previous, `G` end, `g` start,
       **`&pattern`** (show *only* matching lines — grep without leaving the pager), `-S` chop long
       lines, `-N` line numbers, `F` follow. `zless`/`zcat` for rotated `.gz`. `[DIAG]`
1.31.3 The `grep` surface worth knowing cold: `-i` (case), `-c` (count), `-n` (line numbers),
       **`-v`** (invert — the healthcheck-noise filter), `-E` (alternation: `grep -E
       'ERROR|FATAL'`), **`-C 5`** (5 lines of context either side; `-A` after, `-B` before — the
       flag that turns a matched exception line into a readable stack trace), `-o` (print only the
       match, which is what makes field extraction possible), `-r` (recursive), `-l`/`-L` (files
       with/without matches), **`zgrep`** for rotated archives. `rg` is faster and respects
       `.gitignore`, but is not installed on the box you are paged for. `[DIAG]` `[TABLE]`
1.31.4 **`grep | awk | sort | uniq -c | sort -rn | head` is the whole discipline.** Filter to the
       lines that matter, extract the field that matters, group, count, rank. Learn this one
       pipeline and you can answer "what is happening" on any log format in any language.
       **`uniq -c` counts only *adjacent* duplicates, which is why `sort` must precede it** — the
       single most common mistake in the idiom. `[PROVE]` `[TRAP]`
1.31.5 `[DIAG]` **Top 10 error messages by frequency** — the first command of any incident, because
       it turns 400,000 lines into a ranked list of five distinct problems:
       `grep ERROR app.log | awk -F'ERROR' '{print $2}' | sort | uniq -c | sort -rn | head`.
       Refine by cutting the variable tail (`cut -c1-80`) so that the same error with different ids
       groups together instead of producing 400,000 groups of one. `[DIAG]`
1.31.6 `[DIAG]` **Requests per minute around the incident** — the shape that tells you whether this
       was a traffic event or a code event:
       `grep '2026-08-21T14:' app.log | cut -c1-16 | uniq -c`
       (`cut -c1-16` truncates an ISO-8601 timestamp to minute precision, and the lines are already
       time-ordered so `uniq -c` needs no `sort`). Add `| sort -k2` to compare with the deploy time.
       `[DIAG]` `[CALC]`
1.31.7 `[DIAG]` **Slowest endpoints from an access log, by field**:
       `awk '{print $10, $7}' access.log | sort -rn | head -20` where field 7 is the path and field
       10 the duration. Then the aggregate view — mean and count per path —
       `awk '{s[$7]+=$10; n[$7]++} END {for (p in s) printf "%8.1f %6d %s\n", s[p]/n[p], n[p], p}'
       access.log | sort -rn | head`. **Check the field numbers against your own log format first**;
       every combined-log variant numbers them differently and a confidently wrong `$10` produces a
       confidently wrong incident review. `[DIAG]` `[TRAP]`
1.31.8 `[DIAG]` **Tracing one request across an interleaved, multi-line log** — the payoff for
       correlation ids: `grep 'correlationId=7c9a-…' app.log`, and because a Java stack trace is
       many lines that do *not* carry the id, `grep -A 40 'correlationId=7c9a-…' app.log` or an
       `awk` block that treats a timestamp-prefixed line as a record start
       (`awk '/^2026-/{p=/7c9a/} p'`). **Without a correlation id you cannot reconstruct a single
       request from a concurrent log, and no amount of tooling recovers it after the fact.**
       `[DIAG]` `[X-REF 20]`
1.31.9 **`awk` as a two-line data language, not a mystery**: `-F','` sets the field separator, `$0`
       is the line, `$1..$NF` the fields, `NF` the field count, `NR` the record number, `/re/{…}`
       a pattern-action block, `END{…}` the epilogue. Sum a column
       (`awk '{s+=$10} END {print s}'`), average it (`END {print s/NR}`), filter numerically
       (`awk '$10 > 1000'`), and reformat with `printf`. That is 90% of production `awk`.
       `[TABLE]` `[BUILD]`
1.31.10 **`sed` for line ranges and surgical edits**: `sed -n '100,200p' app.log` (print a line
        range without loading the file), `sed -n '/14:22:00/,/14:24:00/p' app.log` (**a time window
        by pattern range** — the most useful `sed` idiom in an incident),
        `sed 's/token=[^ ]*/token=REDACTED/g'` before pasting a log into a ticket. Plus `wc -l`,
        `sort -u`, `sort -k2 -rn`, `cut -d',' -f2`, `head`/`tail -n +N`, `tr`, `paste`, `comm`, and
        `xargs -n1 -P4` to parallelise. `[DIAG]`
1.31.11 **`jq` for structured logs, which is where new services should be**: `jq .` (pretty-print),
        `jq -r '.items[].name'` (**raw** — no quotes, so the output is pipeable),
        `jq 'select(.level=="ERROR")' app.jsonl`,
        `jq -r 'select(.durationMs > 1000) | "\(.path) \(.durationMs)"' app.jsonl`,
        `jq -s 'group_by(.path) | map({path: .[0].path, n: length}) | sort_by(-.n)' app.jsonl`
        (`-s` slurps a JSON-lines stream into an array so you can aggregate). A structured log
        makes 1.31.5–1.31.7 exact instead of positional. `[DIAG]` `[API]`
1.31.12 **`journalctl` on a systemd box**, because the file may not exist: `journalctl -u
        fundsledger --since '10 min ago'`, `-f` (follow), `-p err` (priority), `-k` (kernel — the
        `dmesg` equivalent, §1.30.13), `-b -1` (the previous boot), `--no-pager`, `-o json` to pipe
        into `jq`, `--disk-usage` and `--vacuum-time=7d`. **`-u` plus `--since` is the one form to
        memorise**; without `--since` you will page through a week. `[DIAG]`
1.31.13 **In Kubernetes the log is a moving target**: `kubectl logs deploy/clientrestrictions --since=15m`,
        **`--previous`** (the *dead* container's log — the only place an OOMKilled JVM's last words
        exist), `-c <container>`, `--all-containers`, `-f`, and `stern`/`kubectl logs -l app=` for
        many pods at once. Then `| jq -r 'select(.traceId=="…") | .message'` to reach 1.31.8. A pod
        that has been rescheduled twice has taken its evidence with it — which is why logs ship to
        a store and `kubectl logs` is only for the last few minutes. `[DIAG]` `[X-REF 19]`
1.31.14 `[INCIDENT]` Card deposit success rate fell from 99.4% to 91% with no alert firing, because
        every individual call was inside its 15 s timeout. **Diagnosis:**
        `grep DEP-309 app.log | cut -c1-16 | uniq -c` (1.31.6) showed failures per minute stepping
        up at 13:47 and holding;
        `grep DEP-309 app.log | awk -F'reason=' '{print $2}' | sort | uniq -c | sort -rn`
        (1.31.5) showed 94% of them were a single PSP decline code, not timeouts;
        `awk '$7=="/authorise" {s+=$10; n++} END {print s/n}' access.log` showed mean authorise
        latency up from 240 ms to 4.1 s — inside the timeout, so no error, no alert. **Root cause:**
        the PSP was degrading and shedding load with declines, the documented
        "elevated declines before outage" signature (Appendix A.4). **Fix:** alert on the
        *success-rate* derivative and on p99 against the 11 s figure, not only on error counts —
        four shell pipelines found in three minutes what the monitoring did not have a rule for.
        `[INCIDENT]` `[DIAG]` `[CALC]`

*(14 leaves)*

## §1.32 CPU caches, cache lines, false sharing and the memory hierarchy

1.32.1 **The hierarchy with real numbers, as an ordered table**, because every optimisation in this
       section is an argument about these ratios: register (<1 ns), **L1d 32–48 KiB, ~4 cycles
       ≈ 1 ns**, **L2 1–2 MiB, ~12–15 cycles ≈ 4 ns**, **L3 (shared) 8–64 MiB, ~40 cycles
       ≈ 15–20 ns**, **DRAM ~80–100 ns**, NVMe read ~20 µs, EBS read ~1 ms, cross-AZ RTT ~1 ms. The
       jump from L3 to DRAM is 5×; the jump from DRAM to NVMe is 200×. `[TABLE]` `[NUM]`
1.32.2 **The cache line is 64 bytes on x86-64, and it is the unit of everything.** Nothing moves
       between memory and cache in smaller pieces: reading one `byte` fetches 64; writing one
       `long` dirties 64. Verify on the box with
       `getconf LEVEL1_DCACHE_LINESIZE`, `lscpu | grep -i cache`, or
       `cat /sys/devices/system/cpu/cpu0/cache/index0/coherency_line_size`. AArch64 is also
       typically 64, but **Apple M-series is 128** — a portability trap for hand-padded code.
       `[NUM]` `[PROC]` `[VERSION-TRAP]`
1.32.3 **Spatial and temporal locality are the only two things the hardware rewards.** Contiguous
       traversal gets 8 `long`s per line fetch and a hardware prefetcher that predicts the next
       line; pointer-chasing a linked list gets one useful word per DRAM round trip. An
       `ArrayList<Long>` of 8 million elements is 8 million pointer dereferences to scattered boxed
       objects; a `long[]` of 8 million is 64 MiB of sequential lines. This single difference is
       usually larger than any algorithmic change you were considering. `[PROVE]` `[CALC]`
1.32.4 **Coherence: MESI**, in exactly enough detail to reason about a write. Each line in each
       core's cache is Modified, Exclusive, Shared or Invalid. A write requires **exclusive
       ownership**, so the core issues a *read-for-ownership* that **invalidates every other core's
       copy of that line**. A read by another core then misses and must fetch the line from the
       owner. Writes are therefore not local operations — they are coherence traffic.
       `[PROVE]` `[SOURCE]`
1.32.5 **False sharing** follows directly: two variables that no thread shares, sitting in the same
       64-byte line, are shared *by the hardware*. Every write by core A invalidates core B's copy
       of a line B needs for a completely unrelated field, and both threads take an L3-or-worse miss
       on every increment. The code is correct, the contention is invisible in the source, and the
       throughput loss is an order of magnitude. `[PROVE]` `[TRAP]`
1.32.6 `[CALC]` **The arithmetic on a QuizStakes counter.** Take
       `long[] settlementsByPartition = new long[3]` — one counter per `FundsLedger` partition, each
       updated by its own thread. Three `long`s is 24 bytes: the array's 16-byte header plus 24
       bytes of payload sits **entirely inside one or two 64-byte lines**, so all three threads
       contend on the same line. At the **3,400/sec settlement burst** each increment costs a
       coherence round trip (~40–100 ns) instead of an L1 hit (~1 ns). Pad to one line per counter —
       `long[] c = new long[3 * 8]`, using index `i * 8` — and the three counters occupy three
       distinct lines with zero coherence traffic. The fix costs 168 bytes. `[CALC]` `[NUM]`
       `[BUILD]`
1.32.7 **`@Contended` is the JVM's declarative padding**, and its two footguns are the reason people
       get it wrong: the annotation is `jdk.internal.vm.annotation.Contended` (it moved out of
       `sun.misc`), and **it is ignored on application classes unless you run with
       `-XX:-RestrictContended`** — silently, with no warning, so the "fix" changes nothing.
       Manual padding (1.32.6) or a purpose-built class is more honest in application code.
       `[API]` `[TRAP]` `[VERSION-TRAP]`
1.32.8 **The JDK already solved this for counters, and the solution is `LongAdder`.**
       `java.util.concurrent.atomic.Striped64` maintains an array of padded `Cell`s
       (`@Contended static final class Cell`), so contending threads hit different lines and
       different cache lines entirely; `sum()` adds them up. Under the 3,400/sec settlement burst
       `LongAdder.increment()` scales with cores where `AtomicLong.incrementAndGet()` degrades — a
       single hot `AtomicLong` is a CAS loop on one cache line, which is 1.32.5 with extra steps.
       Use `AtomicLong` when you need `compareAndSet` or an exact instantaneous read; `LongAdder`
       when you need throughput on a monotonic counter. `[API]` `[SOURCE]` `[PROVE]`
1.32.9 **Java object layout is why you cannot reason about lines from source alone**: a 12-byte
       header (mark word + compressed class pointer) padded to an 8-byte boundary, fields
       **reordered by the JVM** (largest first, references grouped) rather than in declaration
       order, and the whole object aligned to 8 bytes. So two fields you wrote adjacently may not be
       adjacent, and two you wrote apart may share a line. Measure with **JOL**
       (`ClassLayout.parseClass(X.class).toPrintable()`), never assume. Note also the compressed-oop
       boundary: past a **32 GB** heap references become 8 bytes and every object grows.
       `[API]` `[NUM]` `[TRAP]`
1.32.10 The connection to the memory model, stated in one paragraph so the reader is not sent away
        empty-handed: the store buffer and invalidation queues that make 1.32.4 fast are exactly why
        a write by one thread is not immediately visible to another, and why `volatile`, `final`
        and `synchronized` exist — they emit the barriers that flush and order those buffers.
        `volatile` on a hot field is *both* a barrier cost and a cache-line-invalidation cost.
        `[X-REF 06]`
1.32.11 **Measuring it, rather than guessing.** `perf stat -e
        cycles,instructions,cache-references,cache-misses,LLC-load-misses -p <pid> -- sleep 10`
        gives you a miss *rate* (misses ÷ references — above roughly 10% on a data-heavy workload is
        worth investigating) and **IPC** (instructions per cycle; below ~1 on straight-line code
        means you are stalled on memory, not executing). Then
        **`perf c2c record`/`perf c2c report`**, which exists for exactly one purpose: attributing
        **HITM** (hit-modified) events to the specific cache line and source line where two cores
        are fighting. That is the only tool that *proves* false sharing rather than suggesting it.
        `[DIAG]` `[NUM]` `[RESEARCH: perf-c2c(1)]`
1.32.12 Prefetching and the shape of your data structures: the hardware prefetcher detects
        sequential and simple strided access and hides DRAM latency entirely — and detects nothing
        in a hash map, a tree or a linked list. This is why an open-addressed map beats a chained
        one, why sorting before a batch lookup can beat the lookup itself, and why "O(n) with good
        locality" routinely beats "O(log n) with pointer chasing" at the sizes real services use.
        `[PROVE]`
1.32.13 **NUMA is the same argument one level up** — remote-socket memory access costs 1.5–2× local,
        and `numactl`, `numastat`, `lscpu`'s NUMA lines and the JVM's `-XX:+UseNUMA` are the
        controls. Deferred in full to §2.8; the only thing to carry here is that a 12 GB
        `FundsLedger` heap on a two-socket box can have half its pages on the wrong node.
        `[X-REF §2.8]`
1.32.14 `[INCIDENT]` `FundsLedger` settlement throughput plateaued at ~2,100/sec against a
        3,400/sec burst requirement, and **adding instances made it worse**, not better.
        **Diagnosis:** `perf stat` showed IPC of 0.31 and an LLC miss rate above 40% with no obvious
        working set to blame; GC was clean; the profiler pointed at a one-line counter increment.
        `perf c2c report` attributed 78% of HITM events to a single cache line — the
        `long[] settlementsByPartition` array of 1.32.6 — and named the three threads fighting over
        it. **Root cause:** textbook false sharing; three per-partition counters in one 64-byte
        line, so every settlement invalidated two other cores' caches. **Fix:** `LongAdder` per
        partition (1.32.8), which restored 3,600/sec on the same hardware. The lesson worth keeping
        is the diagnostic order — the profiler said *where*, only `perf c2c` said *why*.
        `[INCIDENT]` `[DIAG]` `[CALC]`

*(14 leaves)*

---

## Sources consulted — PART B

- `https://www.kernel.org/doc/Documentation/block/queue-sysfs.rst` — fetched. Established the
  `/sys/block/<dev>/queue/` knob surface used in §1.20.4 and confirmed the documented default
  `nomerges = 0` ("By default (0) all merges are enabled"). The document does **not** state
  defaults for `read_ahead_kb`, `nr_requests`, `rotational` or `rq_affinity`, and does not
  enumerate scheduler names — the leaves carrying those figures (§1.20.3, §1.20.4) are marked
  `[RESEARCH]` for re-verification against the running kernel (`cat` the files on an Amazon Linux
  2023 / 6.12 box) at write time.
- `/Users/rajat.chikkodikar/Desktop/My-files/rough/src/topics/11-operating-systems-linux.md` —
  the superseded 616-line guide. Every `**Trap:**` and atomic-checklist line in the §1.17–§1.32
  range has been folded into a leaf: `free`/`available` (§1.30.7), `df`/`du` + `lsof +L1`
  (§1.19.7–8), inode exhaustion (§1.19.5), `iostat` fields and burst credits (§1.20.5–6, §1.20.14),
  the triage order (§1.30.1), the log pipelines (§1.31.5–8), cron's four failures (§1.26.11),
  the kill workflow and `kill -3` (§1.28.6–12), `tail -F` (§1.31.1), PID 1 / shell-form `CMD`
  (§1.26.10, §1.26.13), and `D`-state (§1.20.13). SSH/`scp`/`rsync` (guide §10) is deliberately
  reduced to a single `[X-REF 17]` pointer at §1.26.12 per the brief.
- `/Users/rajat.chikkodikar/Desktop/My-files/rough/src/syllabus/10-networking.md`
  (lines 140–330, 1243–1330) — format, numbering, hanging-indent and tag-usage benchmark; §1.29
  (diagnostic toolkit) and §1.30 (latency budgets) set the register for §1.30 and §1.31 here, and
  its `[X-REF nn]` convention is reused.
- `/Users/rajat.chikkodikar/Desktop/My-files/rough/src/scenario/scenario.md` — every example,
  service, number and budget: §4 service catalog; §5.1 architectural rules; §9 restrictions;
  A.1 (55k concurrent sessions), A.2 (1,200/sec reservations, 3,400/sec settlement burst,
  95k card deposits/day at 40/sec), A.3 (19.8M entries/day, 230/sec sustained, 13,600/sec peak,
  180-byte rows, 1.3 TB/year), A.4 (PSP 240 ms p50 / 11 s p99, "elevated declines before outage",
  identity vendor 900 ms p50 / 38 s p99, banking payout 45 s p99), A.5 (2.6M ApplicationHistory
  records/day at ~400 bytes, 24k uploads/day → 68 GB/day, 500k month-end statement records),
  A.6 (12 GB `FundsLedger` heap, 2–6 MB document buffers, reservation lifetime seconds-to-hours),
  A.7 (30 ms restriction, 150 ms reservation, 500 ms self-exclusion budgets).

**Leaves marked `[RESEARCH]` for the write pass to re-verify against a live 6.12 box or primary
doc**: §1.17.6 (`vm.vfs_cache_pressure`), §1.17.11 (`fs.inotify.max_user_watches` memory-derived
default), §1.18.5 (`errseq_t` fsync error reporting), §1.19.5 (`mke2fs.conf` inode ratio 16384),
§1.19.10 (EBS 16 KiB I/O metering), §1.20.3–4 (scheduler defaults, `read_ahead_kb`, `nr_requests`),
§1.20.9 (gp3/gp2/io2 figures), §1.21.6 and §1.21.10 (io_uring posture, JEP 491),
§1.25.11 (OCI default capability set), §1.27.6 and §1.27.9 (EC2 clocksource, AWS leap smearing),
§1.29.8 (PSI file format), §1.32.11 (`perf c2c` HITM attribution).
