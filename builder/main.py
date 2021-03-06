import sys
from platform import system
from os import makedirs
from os.path import basename, isdir, join

from SCons.Script import (ARGUMENTS, COMMAND_LINE_TARGETS, AlwaysBuild,
                          Builder, Default, DefaultEnvironment)


env = DefaultEnvironment()
platform = env.PioPlatform()
board = env.BoardConfig()

JN51PROG_DIR = platform.get_package_dir("tool-nxp-jn51prog")

env.Replace(
    # 'BA2' Architecture
    AR="ba-elf-ar",
    AS="ba-elf-as",
    CC="ba-elf-gcc",
    CXX="ba-elf-g++",
    GDB="ba-elf-gdb",
    OBJCOPY="ba-elf-objcopy",
    RANLIB="ba-elf-ranlib",
    SIZETOOL="ba-elf-size",
    UPLOADER=join(JN51PROG_DIR, "JN51xxProgrammer.exe"),

    UPLOADERFLAGS=[
        '--serial', '$UPLOAD_PORT',
        '--programbaud', '$UPLOAD_SPEED',
        #'--deviceconfig',
        #'--force'
        #'--eraseflash=full',
        #'--eraseeprom=full',
        '--verify',
        "--loadflash", "$SOURCE"
    ],

    # NOTE: jn51prog requires an interactive TTY, so must use 'start' to launch in a new window.
    UPLOADCMD='start $UPLOADER $UPLOADERFLAGS',

    #ARFLAGS=["rc"],

    CCFLAGS=[
        '-march=ba2',
        '-mcpu=jn51xx',
        '-mredzone-size=4',
        '-mbranch-cost=3',
        '-fomit-frame-pointer',
        '-Os',
        '-fshort-enums',
        '-Wall',
        '-Wpacked',
        '-Wcast-align',
        '-fdata-sections',
        '-ffunction-sections',
        #'-flto',
    ],
    LINKFLAGS=[
        '-march=ba2',
        '-mcpu=jn51xx',
        '-mredzone-size=4',
        '-mbranch-cost=3',
        '-fomit-frame-pointer',
        '-Os',
        '-fshort-enums',
        #'-flto',
    ],

    SIZEPROGREGEXP=r"^(?:\.text|\.data|\.rodata|\.version|\.bir|\.flashheader)\s+(\d+).*",
    SIZEDATAREGEXP=r"^(?:\.data|\.bss|\.noinit|\.heap|\.stack)\s+(\d+).*",
    SIZECHECKCMD="$SIZETOOL -A -d $SOURCES",
    SIZEPRINTCMD='$SIZETOOL -B -d $SOURCES',

    PROGSUFFIX=".elf"
)

# Allow user to override via pre:script
if env.get("PROGNAME", "program") == "program":
    env.Replace(PROGNAME="firmware")

def pdumgenf(target, source, env):
    return "Cannot generate PDUM"

env.Append(
    BUILDERS=dict(
        ElfToBin=Builder(
            action=env.VerboseAction(" ".join([
                "$OBJCOPY",
                #"-j .version -j .bir -j .flashheader -j .vsr_table -j .vsr_handlers  -j .rodata -j .text -j .data -j .bss -j .heap -j .stack",
                #"-S",
                "-O",
                "binary",
                "$SOURCES",
                "$TARGET"
            ]), "Building $TARGET"),
            suffix=".bin"
        ),
        PdumGen=Builder(
            action=env.VerboseAction(
                pdumgenf,
                "Generating PDUM..."
            )
        ),
    )
)

#if not env.get("PIOFRAMEWORK"):
#    env.SConscript("frameworks/_bare.py")

#
# Target: Build executable and linkable firmware
#

target_elf = None
if "nobuild" in COMMAND_LINE_TARGETS:
    target_elf = join("$BUILD_DIR", "${PROGNAME}.elf")
    target_firm = join("$BUILD_DIR", "${PROGNAME}.bin")
else:
    target_elf = env.BuildProgram()
    target_firm = env.ElfToBin(join("$BUILD_DIR", "${PROGNAME}"), target_elf)

AlwaysBuild(env.Alias("nobuild", target_firm))
target_buildprog = env.Alias("buildprog", target_firm, target_firm)

#
# Target: Print binary size
#

target_size = env.Alias(
    "size", target_elf,
    env.VerboseAction("$SIZEPRINTCMD", "Calculating size $SOURCE"))
AlwaysBuild(target_size)

#
# Target: Upload by default .bin file
#

target_upload = env.Alias(
    "upload", target_firm,
    [env.VerboseAction(env.AutodetectUploadPort, "Looking for upload port..."),
     env.VerboseAction("$UPLOADCMD", "Uploading $SOURCE")])
env.AlwaysBuild(target_upload)

#
# Default targets
#

Default([target_buildprog, target_size])
