"""Build a debug APK without rewriting project sources or creating repo outputs."""

import argparse
from pathlib import Path
import shutil
import subprocess
import zipfile

BASE = Path(__file__).resolve().parent


def run(command):
    subprocess.run([str(x) for x in command], check=True)


def build(a):
    work, output = Path(a.work_dir).resolve(), Path(a.output).resolve()
    repo = BASE.parent
    if work == repo or repo in work.parents or output == repo or repo in output.parents:
        raise ValueError("Build work/output must be outside the source repository")
    work.mkdir(parents=True, exist_ok=False)
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists():
        raise FileExistsError(output)
    java = Path(a.java_home) / "bin"
    android = Path(a.android_jar)
    tool = BASE / "tools"
    res, assets, gen, classes, dex = (work / n for n in ("res", "assets", "gen", "classes", "dex"))
    shutil.copytree(BASE / "res", res)
    shutil.copytree(
        repo / "pc-agent-vision" / "web_app", assets / "www", ignore=shutil.ignore_patterns("*.apk")
    )
    for folder in (gen, classes, dex):
        folder.mkdir()
    # Existing resources and manifest are the source of truth, never regenerated.
    flat, base = work / "resources.zip", work / "base.apk"
    run([tool / "aapt2.exe", "compile", "--dir", res, "-o", flat])
    run(
        [
            tool / "aapt2.exe",
            "link",
            "-o",
            base,
            "--manifest",
            BASE / "AndroidManifest.xml",
            "-I",
            android,
            "--java",
            gen,
            "--auto-add-overlay",
            "-A",
            assets,
            flat,
        ]
    )
    sources = list((BASE / "src").rglob("*.java")) + list(gen.rglob("*.java"))
    run(
        [
            java / "javac.exe",
            "-encoding",
            "UTF-8",
            "-source",
            "8",
            "-target",
            "8",
            "-classpath",
            android,
            "-d",
            classes,
            *sources,
        ]
    )
    run(
        [
            java / "java.exe",
            "-cp",
            tool / "r8.jar",
            "com.android.tools.r8.D8",
            "--lib",
            android,
            "--min-api",
            "24",
            "--output",
            dex,
            *classes.rglob("*.class"),
        ]
    )
    unaligned = work / "unaligned.apk"
    with zipfile.ZipFile(base) as source, zipfile.ZipFile(unaligned, "w") as archive:
        for item in source.infolist():
            archive.writestr(item, source.read(item.filename))
        for file in dex.glob("*.dex"):
            archive.write(file, file.name)
    key = work / "debug.keystore"
    run(
        [
            java / "keytool.exe",
            "-genkeypair",
            "-keystore",
            key,
            "-storepass",
            "android",
            "-keypass",
            "android",
            "-alias",
            "androiddebugkey",
            "-keyalg",
            "RSA",
            "-keysize",
            "2048",
            "-validity",
            "3650",
            "-dname",
            "CN=Android Debug,O=Android,C=US",
        ]
    )
    tools = Path(a.build_tools)
    aligned = work / "aligned.apk"
    run([tools / "zipalign.exe", "-p", "4", unaligned, aligned])
    run(
        [
            java / "java.exe",
            "-jar",
            tools / "lib/apksigner.jar",
            "sign",
            "--ks",
            key,
            "--ks-pass",
            "pass:android",
            "--key-pass",
            "pass:android",
            "--v2-signing-enabled",
            "true",
            "--v4-signing-enabled",
            "false",
            "--out",
            output,
            aligned,
        ]
    )
    run([java / "java.exe", "-jar", tools / "lib/apksigner.jar", "verify", "--verbose", output])
    print("Debug APK (not installed or device-tested):", output)


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--work-dir", required=True, help="New empty task-specific build path outside repo"
    )
    p.add_argument("--output", required=True, help="New APK path outside repo")
    p.add_argument("--java-home", default=r"E:\Android\openjdk\jdk-17.0.12")
    p.add_argument(
        "--android-jar", default=r"E:\Android\android-sdk\platforms\android-35\android.jar"
    )
    p.add_argument(
        "--build-tools",
        required=True,
        help="Android SDK Build Tools directory with zipalign and lib/apksigner.jar",
    )
    build(p.parse_args())
