import re
import os
import sys

def fix_ksun(ksun_folder):
    init_path = os.path.join(ksun_folder, 'kernel', 'core', 'init.c')
    if os.path.exists(init_path):
        with open(init_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        new_lines = []
        for line in lines:
            if any(bad in line for bad in ['hook/syscall_hook_manager.h', 'hook/lsm_hook.h', 'hook/syscall_hook.h', 'infra/symbol_resolver.h']):
                continue
            new_lines.append(line)
            if 'feature/sulog.h' in line:
                if not any('hook/setuid_hook.h' in l for l in lines):
                    new_lines.append('#include "hook/setuid_hook.h"\n')
                if not any('feature/sucompat.h' in l for l in lines):
                    new_lines.append('#include "feature/sucompat.h"\n')

        content = ''.join(new_lines)
        if '#include <linux/susfs.h>' not in content:
            content = content.replace('#include <linux/workqueue.h>\n', '#include <linux/workqueue.h>\n#include <linux/susfs.h>\n')
            content = content.replace('#include <linux/workqueue.h>\r\n', '#include <linux/workqueue.h>\r\n#include <linux/susfs.h>\r\n')

        content = re.sub(r'#ifdef MODULE\s*\r?\n\s*ksu_late_loaded\s*=\s*\(current->pid\s*!=\s*1\);\s*\r?\n#else\s*\r?\n\s*ksu_late_loaded\s*=\s*false;\s*\r?\n#endif\s*\r?\n', '', content)
        content = re.sub(r'bool\s+ksu_late_loaded\s*;\s*\r?\n', '', content)
        content = re.sub(r'bool\s+ksu_late_loaded\s*=\s*false;\s*\r?\n', '', content)

        if 'bool ksu_late_loaded' not in content:
            content = content.replace('struct cred *ksu_cred;\n', 'struct cred *ksu_cred;\nbool ksu_late_loaded = false;\n')
            content = content.replace('struct cred *ksu_cred;\r\n', 'struct cred *ksu_cred;\r\nbool ksu_late_loaded = false;\r\n')

        new_init = (
            "int __init kernelsu_init(void)\n"
            "{\n"
            "#ifdef CONFIG_KSU_DEBUG\n"
            '\tpr_alert("*************************************************************");\n'
            '\tpr_alert("**     NOTICE NOTICE NOTICE NOTICE NOTICE NOTICE NOTICE    **");\n'
            '\tpr_alert("**                                                         **");\n'
            '\tpr_alert("**         You are running KernelSU in DEBUG mode          **");\n'
            '\tpr_alert("**                                                         **");\n'
            '\tpr_alert("**     NOTICE NOTICE NOTICE NOTICE NOTICE NOTICE NOTICE    **");\n'
            '\tpr_alert("*************************************************************");\n'
            "#endif\n"
            "\tif (allow_shell) {\n"
            '\t\tpr_alert("shell is allowed at init!");\n'
            "\t}\n\n"
            "\tksu_cred = prepare_creds();\n"
            "\tif (!ksu_cred) {\n"
            '\t\tpr_err("prepare cred failed!\\\\' + 'n");\n'
            "\t\treturn -ENOSYS;\n"
            "\t}\n\n"
            "#ifdef CONFIG_KSU_SUSFS\n"
            "\tsusfs_init();\n"
            "#endif\n\n"
            "\tksu_feature_init();\n"
            "\tksu_supercalls_init();\n"
            "\tksu_sucompat_init();\n"
            "\tksu_setuid_hook_init();\n"
            "\tksu_sulog_init();\n"
            "\tksu_adb_root_init();\n"
            "\tksu_selinux_hide_init();\n"
            "\tksu_allowlist_init();\n"
            "\tksu_throne_tracker_init();\n"
            "\tksu_ksud_init();\n"
            "\tksu_file_wrapper_init();\n\n"
            "\treturn 0;\n"
            "}"
        )
        content = re.sub(r'int __init kernelsu_init\(void\)\s*\{.*?return 0;\s*\}', new_init, content, flags=re.DOTALL)

        new_exit = (
            "void __exit kernelsu_exit(void)\n"
            "{\n"
            "\tksu_supercalls_exit();\n"
            "\tksu_ksud_exit();\n"
            "\tsynchronize_rcu();\n"
            "\tksu_observer_exit();\n"
            "\tksu_throne_tracker_exit();\n"
            "\tksu_allowlist_exit();\n"
            "\tksu_selinux_hide_exit();\n"
            "\tksu_adb_root_exit();\n"
            "\tksu_sulog_exit();\n"
            "\tksu_feature_exit();\n"
            "\tput_cred(ksu_cred);\n"
            "}"
        )
        content = re.sub(r'void __exit kernelsu_exit\(void\)\s*\{.*?put_cred\(ksu_cred\);\s*\}', new_exit, content, flags=re.DOTALL)

        with open(init_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"Successfully fixed {init_path}")

    # Fix Kbuild line by line
    kbuild_path = os.path.join(ksun_folder, 'kernel', 'Kbuild')
    if os.path.exists(kbuild_path):
        with open(kbuild_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        new_lines = []
        skip = False
        for line in lines:
            stripped = line.strip()
            if any(bad in stripped for bad in [
                'hook/lsm_hook.o',
                'hook/syscall_event_bridge.o',
                'hook/syscall_hook_manager.o',
                'hook/tp_marker.o',
                'hook/arm64/patch_memory.o',
                'hook/arm64/syscall_hook.o',
                'hook/x86_64/patch_memory.o',
                'hook/x86_64/syscall_hook.o',
                'infra/symbol_resolver.o',
            ]):
                continue
            if stripped == 'ifeq ($(CONFIG_ARM64),y)':
                skip = True
                continue
            if skip:
                if stripped == 'endif':
                    skip = False
                continue
            new_lines.append(line)

        kb = ''.join(new_lines)
        if '## For susfs stuff ##' not in kb:
            susfs_banner = (
                "\n## For susfs stuff ##\n"
                "ifeq ($(shell test -e $(srctree)/fs/susfs.c; echo $$?),0)\n"
                "$(eval SUSFS_VERSION=$(shell cat $(srctree)/include/linux/susfs.h | grep -E '^#define SUSFS_VERSION' | cut -d' ' -f3 | sed 's/\"//g'))\n"
                "$(info )\n"
                "$(info -- SUSFS_VERSION: $(SUSFS_VERSION))\n"
                "else\n"
                "$(info -- You have not integrated susfs in your kernel yet.)\n"
                "$(info -- Read: https://gitlab.com/simonpunk/susfs4ksu)\n"
                "endif\n"
            )
            kb = kb.rstrip() + "\n" + susfs_banner

        with open(kbuild_path, 'w', encoding='utf-8') as f:
            f.write(kb)
        print(f"Successfully fixed {kbuild_path}")

    # Fix Makefile (remove duplicate susfs stuff if present)
    makefile_path = os.path.join(ksun_folder, 'kernel', 'Makefile')
    if os.path.exists(makefile_path):
        with open(makefile_path, 'r', encoding='utf-8') as f:
            mf = f.read()
        susfs_mf_pat = r'## For susfs stuff ##.*?endif\s*\r?\n'
        mf = re.sub(susfs_mf_pat, '', mf, flags=re.DOTALL)
        with open(makefile_path, 'w', encoding='utf-8') as f:
            f.write(mf)
        print(f"Successfully checked/fixed {makefile_path}")

if __name__ == '__main__':
    target = sys.argv[1] if len(sys.argv) > 1 else 'test_ksun_330'
    fix_ksun(target)
