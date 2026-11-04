"""Build/run production C++ contracts and pure-Java bridge policy. No devices.

Requires Visual Studio C++ on Windows (or CXX elsewhere), an ESP-IDF checkout
for its actual cJSON source, and JDK 17. All outputs go to --work-dir.
"""
import argparse
import json
import hashlib
import os
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def run(command, work, env=None):
    subprocess.run([str(x) for x in command], cwd=work, env=env, check=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--work-dir', required=True)
    parser.add_argument('--idf-path', default=os.environ.get('IDF_PATH'))
    parser.add_argument('--java-home', default=os.environ.get('JAVA_HOME'))
    parser.add_argument('--json-jar',help='Optional pinned org.json:json:20240303 JAR for real JVM UDP loopback test')
    parser.add_argument('--capture-dir',help='Optional actual C++ renderer output outside repository')
    parser.add_argument('--phase-c-observations',help='Exploratory comparison; mismatches reported, never certified')
    parser.add_argument('--phase-c-cases',help='Optional additional input-only replay JSON')
    args = parser.parse_args()
    work = Path(args.work_dir).resolve()
    if work == ROOT or ROOT in work.parents:
        raise ValueError('Use a task cache outside the repository')
    work.mkdir(parents=True, exist_ok=True)
    stubs = ROOT / 'tests/phase_a_stubs'
    arcade = ROOT / 'firmware-s3/main/display/arcade'
    protocol = ROOT / 'firmware-s3/main/protocol'
    display = arcade.parent
    cjson = Path(args.idf_path) / 'components/json/cJSON'
    sources = [ROOT/'tests/phase_a_core_test.cpp', arcade/'arcade_score_store.cpp',
               arcade/'arcade_manager.cpp', arcade/'arcade_result_screen.cpp', display/'mario_game.cpp']
    # Production registry is the source of truth, not all archived cartridges.
    registry = (arcade/'arcade_manager.cpp').read_text(encoding='utf-8')
    import re
    sources += [arcade/(name+'.cpp') for name in re.findall(r'#include "(game_[^"]+)\.h"', registry)]
    includes = [stubs, arcade, display, protocol, cjson]
    executable = work / ('phase-a-core.exe' if os.name == 'nt' else 'phase-a-core')
    if os.name == 'nt':
        vswhere = Path(os.environ.get('ProgramFiles(x86)', 'C:/Program Files (x86)'))/'Microsoft Visual Studio/Installer/vswhere.exe'
        installation = subprocess.check_output([str(vswhere),'-latest','-products','*','-requires','Microsoft.VisualStudio.Component.VC.Tools.x86.x64','-property','installationPath'], text=True).strip()
        vcvars = Path(installation)/'VC/Auxiliary/Build/vcvars64.bat'
        variables = subprocess.check_output(f'cmd.exe /d /s /c ""{vcvars}" >nul && set"',text=True)
        env = dict(os.environ)
        for line in variables.splitlines():
            if '=' in line:
                key,value=line.split('=',1)
                if key: env[key]=value
        compiler=shutil.which('cl.exe',path=env.get('Path',env.get('PATH','')))
        if not compiler: raise RuntimeError('Visual Studio C++ compiler not found')
        run([compiler,'/nologo','/TC','/c',cjson/'cJSON.c',f'/Fo{work}/cJSON.obj'],work,env)
        run([compiler,'/nologo','/std:c++17','/EHsc','/utf-8',*[f'/I{x}' for x in includes],
             *sources,work/'cJSON.obj',f'/Fe{executable}'],work,env)
    else:
        run([os.environ.get('CC','cc'),'-c',cjson/'cJSON.c','-o',work/'cJSON.o'],work)
        run([os.environ.get('CXX','c++'),'-std=c++17','-pthread',*[f'-I{x}' for x in includes],
             *sources,work/'cJSON.o','-o',executable],work)
    replay_env=dict(os.environ)
    render_env=dict(os.environ)
    if args.capture_dir:
        captures=Path(args.capture_dir).resolve()
        if captures==ROOT or ROOT in captures.parents:raise ValueError('Capture outside repository')
        render_env['PHASE_C_CAPTURE']=str(captures)
    if args.phase_c_observations:
        replay_env['PHASE_C_OBSERVATIONS']=str(Path(args.phase_c_observations).resolve())
        replay_env['PHASE_C_COMPARISON']=str(work/'phase-c-comparison.csv')
    if args.phase_c_cases:replay_env['PHASE_C_REPLAY']=str(Path(args.phase_c_cases).resolve())
    run([executable,work/'nvs-host.txt'],work,replay_env)
    run([executable,'reopen',work/'nvs-host.txt'],work)
    if args.capture_dir:run([executable,'capture',work/'visual-nvs-host.txt'],work,render_env)
    java = Path(args.java_home)/'bin'
    harness = work/'BridgePolicyTest.java'
    harness.write_text('''import org.fglab.kurisu.BridgePolicy;
public class BridgePolicyTest {
 public static void main(String[] args) {
  for(String value:new String[]{"192.168.4.1","10.0.0.2","172.16.2.2","172.31.0.1"})
   if(!BridgePolicy.privateIpv4(value))throw new AssertionError(value);
  for(String value:new String[]{"192.168.evil.com","192.168.1.999","127.0.0.1","8.8.8.8","172.32.1.1","192.168.1.255","192.168.01.1","localhost","10.0.0.0"})
   if(BridgePolicy.privateIpv4(value))throw new AssertionError(value);
  if(BridgePolicy.requestId("x');evil()//")||BridgePolicy.token("short"))throw new AssertionError();
  if(!BridgePolicy.token("a".repeat(64)))throw new AssertionError();
  System.out.println("JVM native bridge target/callback/token validation passed");
 }
}''',encoding='utf-8')
    run([java/'javac','-d',work,ROOT/'android-app/src/org/fglab/kurisu/BridgePolicy.java',harness],work)
    run([java/'java','-cp',work,'BridgePolicyTest'],work)
    udp_status='NOT_RUN (supply --json-jar)'
    if args.json_jar:
        jar=Path(args.json_jar).resolve()
        if hashlib.sha256(jar.read_bytes()).hexdigest() != '3cf6cd6892e32e2b4c1c39e0f52f5248a2f5b37646fdfbb79a66b46b618414ed':
            raise ValueError('Expected the pinned org.json:json:20240303 artifact')
        package=ROOT/'android-app/src/org/fglab/kurisu'
        run([java/'javac','-encoding','UTF-8','-cp',jar,'-d',work,package/'BridgePolicy.java',
             package/'DeviceUdpClient.java',ROOT/'tests/java/org/fglab/kurisu/DeviceUdpClientTest.java'],work)
        run([java/'java','-cp',str(work)+os.pathsep+str(jar),'org.fglab.kurisu.DeviceUdpClientTest'],work)
        udp_status='INTEGRATION_PASSED (JVM loopback, not Android hardware)'
    (work/'result.json').write_text(json.dumps({'cpp_production_contracts':'UNIT_TEST_PASSED',
        'jvm_bridge_policy':'UNIT_TEST_PASSED','jvm_udp':udp_status,'physical_nvs':'NOT_TESTED','android_device':'NOT_TESTED'}),encoding='utf-8')


if __name__ == '__main__':
    main()
