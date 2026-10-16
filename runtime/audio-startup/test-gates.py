from pathlib import Path
import ast,importlib.util,tempfile
p=Path(__file__).resolve().parent
source=p/'axon-audio-startup-recover.py'
ast.parse(source.read_text())
spec=importlib.util.spec_from_file_location('recover',source);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
d='3200000.rxmacro\tplatform: supplier 3370000.codec not ready\n3220000.txmacro\tplatform: supplier 3370000.codec not ready\n'
k='[ 6.753976] qcom-q6afe aprsvc:service:4:4: AFE failed to vote (3)\n[ 6.760340] va_macro 3370000.codec: probe with driver va_macro failed with error -110\n'
assert m.known_failure(d,k)
assert not m.known_failure(d,k.replace("6.760340","8.760340"))
assert not m.known_failure(d,k.replace("qcom-q6afe ","other-driver "))
assert not m.known_failure(d.splitlines()[0],k)
assert not m.known_failure(d,k.replace('-110','-22'))
assert not m.known_failure(d,k+'[ 7.0] va_macro 3370000.codec: probe with driver va_macro failed with error -22\n')
assert not m.known_failure(d,k.replace('vote (3)','vote (4)'))
with tempfile.TemporaryDirectory() as td:
 root=Path(td);m.SYS=root;m.VA=root/'bus/platform/devices/3370000.codec';m.VA.mkdir(parents=True)
 node=root/'firmware/devicetree/base/soc@0/codec@3370000';node.mkdir(parents=True)
 (root/'firmware/devicetree/base/compatible').write_bytes(b'zte,axon10s-pro\0qcom,sm8250\0')
 (node/'compatible').write_bytes(b'qcom,sm8250-lpass-va-macro\0');(node/'reg').write_bytes(bytes.fromhex('00000000033700000000000000001000'))
 (m.VA/'of_node').symlink_to(node);drv=root/'bus/platform/drivers/va_macro';drv.mkdir(parents=True)
 assert m.identity() is None
 afe=root/'bus/aprbus/devices/test-afe';afe.mkdir(parents=True)
 afenode=root/'firmware/devicetree/base/afe';afenode.mkdir();(afenode/'compatible').write_bytes(b'qcom,q6afe\0')
 afedrv=root/'bus/aprbus/drivers/qcom-q6afe';afedrv.mkdir(parents=True)
 (afe/'driver').symlink_to(afedrv);(afe/'of_node').symlink_to(afenode)
 assert m.afe_ready()
 (m.VA/'driver').symlink_to(drv);assert m.identity()=='va_macro'
 # Already-bound main must never consult log or invoke a subprocess.
 m.subprocess.run=lambda *a,**k: (_ for _ in ()).throw(AssertionError('unexpected command'))
 assert m.main()==0
 (m.VA/'driver_override').write_text('other')
 try:m.identity()
 except RuntimeError:pass
 else:raise AssertionError('override not rejected')
import configparser
c=configparser.ConfigParser(interpolation=None);c.read(p/'axon-audio-startup-recover.service')
assert c['Unit']['ConditionPathExists']=='/sys/bus/platform/drivers/va_macro'
print('PASS: syntax, exact known-failure gates, later unrelated error rejection, fake DT/VA identity, already-bound no-op, driver_override rejection; no real sysfs writes')
