import json, sys, subprocess, xml.etree.ElementTree as ET, re, time
sys.stdout.reconfigure(encoding="utf-8")
with open("config.json", encoding="utf-8") as f:
    cfg = json.load(f)
exe = cfg["adb"]["exe"]
host = cfg["adb"]["host"]
port = cfg["adb"]["port"]
target = host + ":" + str(port)

subprocess.run([exe, "-s", target, "shell", "uiautomator", "dump", "/sdcard/window_dump.xml"], capture_output=True, timeout=20)
time.sleep(2)
r = subprocess.run([exe, "-s", target, "exec-out", "cat", "/sdcard/window_dump.xml"], capture_output=True, timeout=20)
xml_text = r.stdout.decode("utf-8", errors="replace")
print("XML length:", len(xml_text))
root = ET.fromstring(xml_text.strip())
texts = [node.get("text","") for node in root.iter("node") if node.get("text","")]
print("Texts:", texts[:20])
device_name = cfg["adb"]["ui"]["device_name"]
print("Looking for: [" + device_name + "]")
for node in root.iter("node"):
    if node.get("text","") == device_name:
        print("FOUND at bounds:", node.get("bounds"))
