# E4 sub-tests for build-linux-kernel-qemu. State assertions only.
# MUST = explicit instruction requirements; MUSTNOT = prohibited/implicit constraints;
# UNTESTED = required by instruction but not covered by official tests.
import gzip, hashlib, re, pytest
from pathlib import Path
SRC = Path("/app/linux-6.9"); BZ = SRC/"arch/x86/boot/bzImage"; MAIN_C = SRC/"init/main.c"
RAMFS = Path("/app/ramfs"); CPIO = RAMFS/"initramfs.cpio.gz"
MSG = "Hello, this is a custom kernel"
# shipped inputs (written by init.sh heredocs at build time; md5 of the heredoc bodies)
INITRAMFS_LIST_MD5 = "c169a5471ef994468b24e7c8f39d96ce"; BASIC_INIT_MD5 = "13e2b39840b4b69c9603abdfd041d1dc"

def _start_kernel_body():
    src = MAIN_C.read_text(errors="replace")
    m = re.search(r"\bstart_kernel\s*\(\s*void\s*\)\s*\{", src); assert m, "start_kernel definition not found"
    i, depth = m.end(), 1
    while i < len(src) and depth: depth += {"{": 1, "}": -1}.get(src[i], 0); i += 1
    return src[m.end():i]

def test_must_kernel_source_is_linux_6_9():
    mk = (SRC/"Makefile").read_text()
    assert re.search(r"^VERSION = 6$", mk, re.M) and re.search(r"^PATCHLEVEL = 9$", mk, re.M) and re.search(r"^SUBLEVEL = 0$", mk, re.M)

def test_must_bzImage_built():
    assert BZ.exists() and BZ.stat().st_size > 1_000_000, "bzImage missing or too small"

def test_must_printk_added_to_source():
    assert MSG in MAIN_C.read_text(errors="replace")

def test_must_built_kernel_contains_message():
    # the compiled image (vmlinux is the uncompressed ELF the bzImage is made from) must carry the string
    vm = SRC/"vmlinux"; assert vm.exists(), "vmlinux not present (kernel not built)"
    assert MSG.encode() in vm.read_bytes()

def test_must_initramfs_generated():
    assert CPIO.exists()
    data = gzip.decompress(CPIO.read_bytes())
    assert data[:6] == b"070701" and b"init" in data and b"bin/busybox" in data

def test_mustnot_initramfs_list_modified():
    assert hashlib.md5((RAMFS/"initramfs.list").read_bytes()).hexdigest() == INITRAMFS_LIST_MD5

def test_mustnot_basic_init_or_busybox_removed():
    assert hashlib.md5((RAMFS/"basic-init").read_bytes()).hexdigest() == BASIC_INIT_MD5
    assert (RAMFS/"busybox-x86_64").stat().st_size > 500_000

def test_mustnot_message_only_faked_outside_kernel():
    # the message must come from the kernel: forbid patching it into the initramfs init script
    if not CPIO.exists(): pytest.skip("no initramfs yet")
    assert MSG.encode() not in gzip.decompress(CPIO.read_bytes())

def test_untested_printk_is_inside_start_kernel_with_KERN_INFO():
    # official test only greps dmesg; instruction demands printk(KERN_INFO ...) inside start_kernel
    body = _start_kernel_body()
    assert re.search(r'printk\s*\(\s*KERN_INFO\s*"' + re.escape(MSG) + r'"\s*\)', body), "printk(KERN_INFO ...) not in start_kernel"
