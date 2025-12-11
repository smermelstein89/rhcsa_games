#!/usr/bin/env python3
import sys
import copy

# ============================================
#   UTILITIES
# ============================================

score = 0

def banner(title):
    print("\n" + "=" * 70)
    print(title)
    print("=" * 70 + "\n")

def correct(msg="Correct!"):
    global score
    score += 1
    print("✅", msg, "\n")

def wrong(msg="Not quite."):
    print("❌", msg, "\n")

def ask(prompt="> "):
    try:
        return input(prompt).strip()
    except (EOFError, KeyboardInterrupt):
        print()
        return "exit"

def ask_hint(hints, idx):
    if idx >= len(hints):
        print("No more hints for this level.\n")
        return idx
    if ask("Need a hint? (y/n): ").lower().startswith("y"):
        print("💡 Hint:", hints[idx], "\n")
        return idx + 1
    return idx

# ============================================
#   VIRTUAL FILESYSTEM + SHELL
# ============================================

# perms are octal: 0o4755 etc, type: 'file' or 'dir'
# selinux: 'type'
# acl: True if there is an ACL entry (we don't model full ACLs here)

def mode_to_string(mode, ftype="file", has_acl=False):
    # file type
    s = "d" if ftype == "dir" else "-"
    # extract bits
    suid = bool(mode & 0o4000)
    sgid = bool(mode & 0o2000)
    sticky = bool(mode & 0o1000)

    def triplet(bits, special, special_char):
        r = "r" if bits & 0o4 else "-"
        w = "w" if bits & 0o2 else "-"
        x_bit = bits & 0o1
        if not x_bit and special:
            x = special_char.upper()  # S or T
        elif x_bit and special:
            x = special_char  # s or t
        elif x_bit:
            x = "x"
        else:
            x = "-"
        return r + w + x

    u = (mode >> 6) & 0o7
    g = (mode >> 3) & 0o7
    o = mode & 0o7

    s += triplet(u, suid, "s")
    s += triplet(g, sgid, "s")
    s += triplet(o, sticky, "t")

    if has_acl:
        s += "+"
    return s

class VFS:
    def __init__(self, files, cwd="/"):
        # files: {path: {"mode":0o755,"type":"dir","owner":"root","group":"root","acl":False,"ctx":None}}
        self.files = copy.deepcopy(files)
        self.cwd = cwd

    def _abspath(self, path):
        if path.startswith("/"):
            return path
        if self.cwd.endswith("/"):
            return self.cwd + path
        if path == ".":
            return self.cwd
        return self.cwd.rstrip("/") + "/" + path

    def ls(self, args):
        long = "-l" in args
        path = "."
        parts = [p for p in args.split() if not p.startswith("-")]
        if parts:
            path = parts[0]

        ap = self._abspath(path)
        # directory listing
        if ap.endswith("/") and ap not in self.files:
            ap = ap.rstrip("/")
        if ap in self.files and self.files[ap]["type"] == "dir":
            # list children
            prefix = ap.rstrip("/")
            if prefix == "":
                prefix = "/"
            print()
            for p, meta in sorted(self.files.items()):
                if p == prefix:
                    continue
                if p.startswith(prefix.rstrip("/") + "/") and "/" not in p[len(prefix.rstrip("/"))+1:]:
                    name = p.split("/")[-1] or "/"
                    if long:
                        m = mode_to_string(meta["mode"], meta["type"], meta.get("acl", False))
                        owner = meta.get("owner", "root")
                        group = meta.get("group", "root")
                        print(f"{m} 1 {owner} {group} {name}")
                    else:
                        print(name, end="  ")
            if not long:
                print()
            print()
        elif ap in self.files:
            meta = self.files[ap]
            name = ap.split("/")[-1]
            if long:
                m = mode_to_string(meta["mode"], meta["type"], meta.get("acl", False))
                owner = meta.get("owner", "root")
                group = meta.get("group", "root")
                print(f"\n{m} 1 {owner} {group} {name}\n")
            else:
                print("\n" + name + "\n")
        else:
            print(f"ls: cannot access '{path}': No such file or directory\n")

    def cd(self, path):
        if not path:
            path = "/"
        ap = self._abspath(path)
        if ap in self.files and self.files[ap]["type"] == "dir":
            self.cwd = ap
        else:
            print(f"bash: cd: {path}: No such directory")

    def pwd(self):
        print(self.cwd)

# ============================================
#   MODULE BASE
# ============================================

def shell_loop(module_name, scenario):
    """
    scenario:
      - "intro": str
      - "files": {...} for VFS
      - "goal_check": fn(vfs)->bool
      - "apply_cmd": fn(cmd,vfs)->(bool handled, bool maybe_wrong_msg)
      - "hints": [str,...]
      - "extra_help": str
    """
    banner(module_name + " – " + scenario["name"])
    print(scenario["intro"], "\n")
    print("Commands you can use: ls, ls -l, cd, pwd, help, hint, exit")
    print("Module-specific commands are described in 'help'.\n")

    vfs = VFS(scenario["files"], scenario.get("cwd", "/"))
    hint_idx = 0

    while True:
        if scenario["goal_check"](vfs):
            correct("Objective completed for this scenario!")
            break

        cmd = ask(f"{module_name.split()[0].lower()}$ ")

        if cmd in ("exit", "quit"):
            print("Returning to main menu...\n")
            break
        if cmd.startswith("ls"):
            vfs.ls(cmd[2:].strip())
            continue
        if cmd.startswith("cd"):
            parts = cmd.split(maxsplit=1)
            vfs.cd(parts[1] if len(parts) > 1 else "/")
            continue
        if cmd == "pwd":
            vfs.pwd()
            continue
        if cmd == "help":
            print("\n" + scenario["extra_help"] + "\n")
            continue
        if cmd == "hint":
            hint_idx = ask_hint(scenario["hints"], hint_idx)
            continue
        if not cmd:
            continue

        handled, potentially_wrong = scenario["apply_cmd"](cmd, vfs)
        if not handled:
            if potentially_wrong:
                wrong("Command recognized but does not solve the scenario.")
            else:
                print("🔧 That command is not implemented in this training shell.\n")

# ============================================
#   PERMISSIONS MODULE
# ============================================

def make_permissions_scenarios():
    base_dir = {
        "/": {"mode": 0o755, "type": "dir", "owner": "root", "group": "root"},
    }

    def scen1_goal(vfs):
        f = vfs.files["/script.sh"]
        return f["mode"] == 0o700

    def scen1_apply(cmd, vfs):
        if cmd == "chmod 700 script.sh":
            vfs.files["/script.sh"]["mode"] = 0o700
            return True, False
        elif cmd.startswith("chmod"):
            return True, True
        return False, False

    scen1 = {
        "name": "Owner-only executable script",
        "intro": "Make /script.sh readable, writable, and executable *only* by the owner.",
        "files": {
            **base_dir,
            "/script.sh": {"mode": 0o664, "type": "file", "owner": "root", "group": "root"},
        },
        "goal_check": scen1_goal,
        "apply_cmd": scen1_apply,
        "hints": [
            "Use numeric mode: owner=7, group=0, others=0.",
            "Command should look like: chmod 700 script.sh",
        ],
        "extra_help": "You are practising basic chmod. Try: ls -l, then chmod 700 script.sh"
    }

    def scen2_goal(vfs):
        return vfs.files["/usr/bin/custom"]["mode"] == 0o4755

    def scen2_apply(cmd, vfs):
        if cmd == "chmod u+s /usr/bin/custom":
            vfs.files["/usr/bin/custom"]["mode"] |= 0o4000
            return True, False
        if cmd == "chmod 4755 /usr/bin/custom":
            vfs.files["/usr/bin/custom"]["mode"] = 0o4755
            return True, False
        if cmd.startswith("chmod"):
            return True, True
        return False, False

    scen2 = {
        "name": "Set SUID on a binary",
        "intro": "Set the SUID bit on /usr/bin/custom so that it runs with the file owner's privileges.",
        "files": {
            **base_dir,
            "/usr": {"mode": 0o755, "type": "dir", "owner": "root", "group": "root"},
            "/usr/bin": {"mode": 0o755, "type": "dir", "owner": "root", "group": "root"},
            "/usr/bin/custom": {"mode": 0o755, "type": "file", "owner": "root", "group": "root"},
        },
        "goal_check": scen2_goal,
        "apply_cmd": scen2_apply,
        "hints": [
            "SUID is the 4 in front of normal perms (e.g. 4755).",
            "You can also use symbolic: chmod u+s /usr/bin/custom.",
        ],
        "extra_help": "Practise SUID: SUID bit shows as 's' in user execute position (rwsr-xr-x)."
    }

    def scen3_goal(vfs):
        # SGID directory and 2775 perms
        d = vfs.files["/shared"]
        return (d["mode"] & 0o7777) == 0o2775

    def scen3_apply(cmd, vfs):
        if cmd == "chmod 2775 /shared":
            vfs.files["/shared"]["mode"] = 0o2775
            return True, False
        if cmd == "chmod g+s /shared":
            vfs.files["/shared"]["mode"] |= 0o2000
            return True, False
        if cmd.startswith("chmod"):
            return True, True
        return False, False

    scen3 = {
        "name": "Project directory with SGID",
        "intro": "Configure /shared so that all files created inside inherit group 'dev' (via SGID).",
        "files": {
            **base_dir,
            "/shared": {"mode": 0o0775, "type": "dir", "owner": "root", "group": "dev"},
        },
        "goal_check": scen3_goal,
        "apply_cmd": scen3_apply,
        "hints": [
            "SGID is the 2 in front: chmod 2775 /shared.",
            "Or use chmod g+s /shared.",
        ],
        "extra_help": "SGID on a directory (rwxrwsr-x) makes new files inherit its group."
    }

    def scen4_goal(vfs):
        d = vfs.files["/public"]
        return (d["mode"] & 0o7777) == 0o1777

    def scen4_apply(cmd, vfs):
        if cmd == "chmod 1777 /public":
            vfs.files["/public"]["mode"] = 0o1777
            return True, False
        if cmd == "chmod +t /public":
            vfs.files["/public"]["mode"] |= 0o1000
            return True, False
        if cmd.startswith("chmod"):
            return True, True
        return False, False

    scen4 = {
        "name": "Sticky bit on shared directory",
        "intro": "Configure /public like /tmp: anyone can create files, but only owners (or root) can delete theirs.",
        "files": {
            **base_dir,
            "/public": {"mode": 0o0777, "type": "dir", "owner": "root", "group": "root"},
        },
        "goal_check": scen4_goal,
        "apply_cmd": scen4_apply,
        "hints": [
            "Sticky bit is the 1 in front: chmod 1777 /public.",
            "Or use chmod +t /public.",
        ],
        "extra_help": "Sticky bit shows as 't' in others execute position: rwxrwxrwt."
    }

    return [scen1, scen2, scen3, scen4]

def permissions_module():
    for scen in make_permissions_scenarios():
        shell_loop("Permissions", scen)

# ============================================
#   ACL MODULE
# ============================================

def make_acl_scenarios():
    base = {
        "/": {"mode": 0o755, "type": "dir", "owner": "root", "group": "root"},
        "/project": {"mode": 0o770, "type": "dir", "owner": "root", "group": "dev", "acl": False},
        "/shared": {"mode": 0o770, "type": "dir", "owner": "root", "group": "dev", "acl": False},
        "/project/file.txt": {"mode": 0o660, "type": "file", "owner": "root", "group": "dev", "acl": False},
    }

    def scen1_goal(vfs):
        return vfs.files["/project/file.txt"].get("acl") == "alice:rwx"

    def scen1_apply(cmd, vfs):
        if cmd == "setfacl -m u:alice:rwx /project/file.txt":
            vfs.files["/project/file.txt"]["acl"] = "alice:rwx"
            vfs.files["/project/file.txt"]["mode"] = 0o660
            return True, False
        if cmd.startswith("setfacl"):
            return True, True
        if cmd.startswith("getfacl"):
            print("\n# file: /project/file.txt\n"
                  "user::rw-\n"
                  "user:alice:rwx\n"
                  "group::rw-\n"
                  "mask::rwx\n"
                  "other::---\n")
            return True, False
        return False, False

    scen1 = {
        "name": "Give alice rwx on a single file",
        "intro": "Grant user alice rwx on /project/file.txt without changing the group.",
        "files": {k: copy.deepcopy(v) for k, v in base.items()},
        "goal_check": scen1_goal,
        "apply_cmd": scen1_apply,
        "hints": [
            "Use setfacl -m to modify ACL entries.",
            "Syntax: setfacl -m u:alice:rwx /project/file.txt",
        ],
        "extra_help": "Commands: setfacl -m u:alice:rwx /project/file.txt, getfacl /project/file.txt"
    }

    def scen2_goal(vfs):
        return vfs.files["/shared"].get("def_acl") == "bob:rwx"

    def scen2_apply(cmd, vfs):
        if cmd == "setfacl -d -m u:bob:rwx /shared":
            vfs.files["/shared"]["def_acl"] = "bob:rwx"
            vfs.files["/shared"]["acl"] = True
            return True, False
        if cmd.startswith("setfacl"):
            return True, True
        if cmd.startswith("getfacl"):
            print("\n# file: /shared\n"
                  "user::rwx\n"
                  "group::rwx\n"
                  "mask::rwx\n"
                  "other::---\n"
                  "default:user::rwx\n"
                  "default:user:bob:rwx\n"
                  "default:group::rwx\n"
                  "default:mask::rwx\n"
                  "default:other::---\n")
            return True, False
        return False, False

    scen2 = {
        "name": "Default ACL for new files",
        "intro": "Ensure user bob automatically gets rwx on new files in /shared.",
        "files": {k: copy.deepcopy(v) for k, v in base.items()},
        "goal_check": scen2_goal,
        "apply_cmd": scen2_apply,
        "hints": [
            "Default ACLs apply to directories only.",
            "Use -d to set default ACL: setfacl -d -m u:bob:rwx /shared",
        ],
        "extra_help": "Default ACL syntax: setfacl -d -m u:USER:rwx DIR"
    }

    def scen3_goal(vfs):
        return vfs.files["/project/file.txt"].get("acl") is None

    def scen3_apply(cmd, vfs):
        if cmd == "setfacl -x u:alice /project/file.txt":
            vfs.files["/project/file.txt"]["acl"] = None
            return True, False
        if cmd.startswith("setfacl"):
            return True, True
        if cmd.startswith("getfacl"):
            print("\n# file: /project/file.txt\n"
                  "user::rw-\n"
                  "group::rw-\n"
                  "mask::rw-\n"
                  "other::---\n")
            return True, False
        return False, False

    scen3 = {
        "name": "Remove an ACL entry",
        "intro": "Remove alice's ACL entry from /project/file.txt.",
        "files": {**base,
                  "/project/file.txt": {"mode": 0o660, "type": "file",
                                        "owner": "root", "group": "dev",
                                        "acl": "alice:rwx"}},
        "goal_check": scen3_goal,
        "apply_cmd": scen3_apply,
        "hints": [
            "Use -x to delete an ACL entry.",
            "Command: setfacl -x u:alice /project/file.txt",
        ],
        "extra_help": "Use getfacl to inspect, setfacl -x to remove."
    }

    return [scen1, scen2, scen3]

def acl_module():
    for scen in make_acl_scenarios():
        shell_loop("ACL", scen)

# ============================================
#   SELINUX MODULE
# ============================================

def make_selinux_scenarios():
    base = {
        "/": {"mode": 0o755, "type": "dir", "owner": "root", "group": "root"},
        "/virtual": {"mode": 0o755, "type": "dir", "owner": "root", "group": "root", "ctx": "default_t"},
        "/virtual/index.html": {"mode": 0o644, "type": "file", "owner": "root", "group": "root", "ctx": "default_t"},
    }

    # We'll store fcontext rules separately in scenario state via vfs.files["_rules"]
    def scen1_goal(vfs):
        # We consider it solved if directory and file have httpd_sys_content_t
        d = vfs.files["/virtual"]["ctx"]
        f = vfs.files["/virtual/index.html"]["ctx"]
        rules = vfs.files.get("_rules", [])
        bool1 = any(r["type"] == "httpd_sys_content_t" and r["pattern"] == "/virtual(/.*)?" for r in rules)
        return d == "httpd_sys_content_t" and f == "httpd_sys_content_t" and bool1

    def scen1_apply(cmd, vfs):
        # semanage fcontext -a -t httpd_sys_content_t '/virtual(/.*)?'
        if cmd.startswith("semanage fcontext -a -t httpd_sys_content_t"):
            vfs.files.setdefault("_rules", []).append(
                {"pattern": "/virtual(/.*)?", "type": "httpd_sys_content_t"}
            )
            return True, False
        if cmd.startswith("restorecon -Rv /virtual"):
            # apply rule if present
            for r in vfs.files.get("_rules", []):
                if r["pattern"] == "/virtual(/.*)?":
                    vfs.files["/virtual"]["ctx"] = r["type"]
                    vfs.files["/virtual/index.html"]["ctx"] = r["type"]
            return True, False
        if cmd.startswith("chcon -t"):
            # temporary relabel
            parts = cmd.split()
            t = parts[2]
            path = parts[3]
            ap = path
            if ap in vfs.files:
                vfs.files[ap]["ctx"] = t
            return True, True  # accepted but not persistent
        if cmd == "ls -Z":
            print("\n/virtual " + base["/virtual"]["owner"] + ":" +
                  base["/virtual"]["group"] + " " +
                  vfs.files["/virtual"]["ctx"])
            print("/virtual/index.html " + vfs.files["/virtual/index.html"]["ctx"] + "\n")
            return True, False
        return False, False

    scen1 = {
        "name": "Serve /virtual with Apache (persistent)",
        "intro": ("Apache must serve files from /virtual.\n"
                  "Set a *persistent* SELinux context so that after relabel, /virtual "
                  "and its contents use httpd_sys_content_t."),
        "files": {k: copy.deepcopy(v) for k, v in base.items()},
        "goal_check": scen1_goal,
        "apply_cmd": scen1_apply,
        "hints": [
            "First, add a rule with semanage fcontext.",
            "Then apply it with restorecon -Rv /virtual.",
            "Pattern should be '/virtual(/.*)?'."
        ],
        "extra_help": ("Useful commands:\n"
                       "  semanage fcontext -a -t httpd_sys_content_t '/virtual(/.*)?'\n"
                       "  restorecon -Rv /virtual\n"
                       "Temporary label (NOT persistent): chcon -t httpd_sys_content_t /virtual")
    }

    def scen2_goal(vfs):
        return vfs.files["/tmp/data"]["ctx"] == "httpd_sys_rw_content_t"

    def scen2_apply(cmd, vfs):
        if cmd == "chcon -t httpd_sys_rw_content_t /tmp/data":
            vfs.files["/tmp/data"]["ctx"] = "httpd_sys_rw_content_t"
            return True, False
        if cmd.startswith("semanage") or cmd.startswith("restorecon"):
            return True, True
        return False, False

    scen2_files = {
        "/": {"mode": 0o755, "type": "dir", "owner": "root", "group": "root"},
        "/tmp": {"mode": 0o777, "type": "dir", "owner": "root", "group": "root"},
        "/tmp/data": {"mode": 0o666, "type": "file", "owner": "apache", "group": "apache", "ctx": "tmp_t"},
    }

    scen2 = {
        "name": "Temporary writable content for Apache",
        "intro": ("You just need a temporary fix so Apache can write to /tmp/data.\n"
                  "Do NOT worry about persistence – just relabel this one file."),
        "files": scen2_files,
        "goal_check": scen2_goal,
        "apply_cmd": scen2_apply,
        "hints": [
            "Use chcon, not semanage, for temporary labels.",
            "Target type: httpd_sys_rw_content_t",
        ],
        "extra_help": "Command to try: chcon -t httpd_sys_rw_content_t /tmp/data"
    }

    def scen3_goal(vfs):
        return vfs.files.get("_bools", {}).get("httpd_use_nfs") is True

    def scen3_apply(cmd, vfs):
        if cmd == "setsebool -P httpd_use_nfs on":
            vfs.files.setdefault("_bools", {})["httpd_use_nfs"] = True
            return True, False
        if cmd.startswith("setsebool"):
            return True, True
        if cmd.startswith("getsebool httpd_use_nfs"):
            val = vfs.files.get("_bools", {}).get("httpd_use_nfs", False)
            state = "on" if val else "off"
            print(f"httpd_use_nfs --> {state}")
            return True, False
        return False, False

    scen3 = {
        "name": "Enable SELinux boolean for NFS",
        "intro": "Allow Apache to read content from NFS shares by flipping the right SELinux boolean.",
        "files": {"/": {"mode": 0o755, "type": "dir", "owner": "root", "group": "root"}},
        "goal_check": scen3_goal,
        "apply_cmd": scen3_apply,
        "hints": [
            "Check the boolean with: getsebool httpd_use_nfs",
            "Persistently enable with: setsebool -P httpd_use_nfs on",
        ],
        "extra_help": "Booleans: getsebool NAME, setsebool -P NAME on|off"
    }

    return [scen1, scen2, scen3]

def selinux_module():
    for scen in make_selinux_scenarios():
        shell_loop("SELinux", scen)

# ============================================
#   RD.BREAK / RESCUE MODULE
# ============================================

def rescue_module():
    banner("BOOT RESCUE SIMULATOR – rd.break / chroot / passwd / /.autorelabel")

    steps = [
        ("You are at the GRUB menu. Edit the default entry.", ["e"]),
        ("Append rd.break to the Linux kernel line.", ["rd.break"]),
        ("Boot with the modified kernel line (Ctrl+x).", ["ctrl+x", "c-x"]),
        ("Remount sysroot read-write.", ["mount -o remount,rw /sysroot"]),
        ("Chroot into sysroot.", ["chroot /sysroot"]),
        ("Change the root password.", ["passwd root"]),
        ("Force SELinux relabel on next boot.", ["touch /.autorelabel"]),
        ("Exit chroot.", ["exit"]),
        ("Exit emergency shell to reboot.", ["exit"]),
    ]

    idx = 0
    hint_idx = 0
    hints = [
        "At GRUB, press 'e' to edit the selected entry.",
        "Add rd.break at the end of the linux line.",
        "Ctrl+x boots the edited entry.",
        "mount -o remount,rw /sysroot",
        "chroot /sysroot",
        "passwd root",
        "touch /.autorelabel is required if SELinux is enforcing.",
        "exit twice to reboot.",
    ]

    print("Simulate the *exact* sequence to reset the root password on a RHEL-like system.\n")
    print("Type 'hint' for help, 'skip' to finish early, or 'exit' to go back.\n")

    while idx < len(steps):
        task, answers = steps[idx]
        print(f"Step {idx+1}/{len(steps)}: {task}")
        cmd = ask("rescue$ ")

        if cmd in ("exit", "quit"):
            print("Returning to main menu.\n")
            return
        if cmd == "skip":
            break
        if cmd == "hint":
            hint_idx = ask_hint(hints, hint_idx)
            continue

        if cmd in answers:
            correct("Good.")
            idx += 1
        else:
            wrong("That's not the expected action at this step.")

    if idx == len(steps):
        correct("You completed the full rd.break password reset workflow!")
    else:
        print("Simulation ended early. Review the steps and try again later.\n")

# ============================================
#   MAIN MENU
# ============================================

def main():
    banner("🔥 RHCSA COMMAND-LINE TRAINER 🔥")
    print("Modules:")
    print("  1) Permissions (chmod, SUID, SGID, Sticky bit)")
    print("  2) ACLs (setfacl, getfacl, default ACLs)")
    print("  3) SELinux (contexts, restorecon, semanage, setsebool)")
    print("  4) Boot Rescue (rd.break, chroot, passwd, /.autorelabel)")
    print("  5) Quit\n")

    choice = ask("Select module: ")

    if choice == "1":
        permissions_module()
    elif choice == "2":
        acl_module()
    elif choice == "3":
        selinux_module()
    elif choice == "4":
        rescue_module()
    else:
        print("\nFinal score:", score)
        print("Good luck on RHCSA!")
        sys.exit(0)

    # loop back to menu
    main()

if __name__ == "__main__":
    main()

